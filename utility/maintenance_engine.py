"""
EVERYTHING IN HERE RUNS OFF THE SAME EXTERNAL CRON PING THAT DRIVES THE CHECK-IN
REMINDERS (see origin/views/cron_job_View.py + utility/reminder_engine.py). There is
only ONE http endpoint configured on cron-job.org/UptimeRobot, so every periodic
task the app needs lives on that single tick, not four different endpoints.

Four jobs live here, in the order they should run:

1. `complete_expired_commitments`  - a commitment whose goal_days is not 0 (0 = forever)
   and whose age has reached goal_days has hit 100%. Unlike a user Delete, this does
   NOT touch is_active - the commitment stays fully alive and visible. All this job
   does is stamp `completed_at` once, which the frontend uses to trigger the one-time
   "standing ovation" celebration on the dashboard/commitment page.

2. `purge_deleted_commitments`     - hard-deletes (DB row gone, Entries cascade with it)
   every commitment that the user themselves soft-deleted (is_active=False via the
   Delete button on the commitment page - see EachCommitmentArchive) MORE THAN 24
   HOURS AGO (deactivated_at). Inside that 24h window the commitment is only hidden
   from the active list and shows up as "recoverable" on the profile page - nothing
   is ever purged before the 24h recovery window has genuinely elapsed.

3. `reset_stale_streaks`          - the piece that was missing entirely: nothing used
   to proactively reset streak_count if a user just stopped checking in. Quick-checkin
   and the long entry form only ever reset a streak reactively (the next time THAT
   user shows up late). If they never come back, the streak just sat there wrong
   forever. This walks every still-active commitment with a last_check_in and, if more
   than 24 hours have passed since then, zeroes the streak - and leaves a
   `pending_notice` on the row so the user gets an honest django message about it next
   time they load a page that touches that commitment (see DashboardCommitmentView /
   EachCommitmentView, which flush + clear pending_notice via messages.warning()).

4. `downgrade_expired_trials`     - every new signup gets 7 days of premium for free
   (see origin/views/auth_view.py -> Signup.post). This is the other half of that: once
   PremiumTrial.expires_at has passed, flip the profile back down to free, exactly
   once, and record it as downgraded so we never touch that user's tier again here.

5. `send_inactivity_checkups`     - the "we miss you" nudge. Any active user whose
   last_login is 4+ days old gets both an email AND a push notification (push only
   actually reaches them if they have push enabled - see utility/push_sending.py,
   which silently no-ops for everyone else). To stop this firing on every single cron
   tick for the same user, last_checkup_notice_sent_at is stamped the moment it sends
   and only re-fires once another 4 days have passed with no login - so someone who
   stays away keeps getting nudged every 4 days, and it stops the moment they log back
   in (last_login updates, resetting the 4-day countdown).
"""

import logging
from datetime import datetime

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


def complete_expired_commitments() -> int:
    """Reaching 100% (goal_days != 0, i.e. not a "forever" commitment, and age >=
    goal_days) no longer deactivates or queues the commitment for deletion - product
    decision: a completed commitment stays fully alive (is_active stays True) so the
    user can keep visiting it, they just get the one-time "standing ovation" trigger.
    All this job does now is stamp `completed_at` exactly once (the
    `completed_at__isnull=True` filter is what stops it re-stamping/re-notifying on
    every subsequent tick) - the dashboard/commitment page reads `completed_at` to
    decide whether to replay the celebration."""
    from origin.models import Commitment

    today = timezone.now().date()
    candidates = Commitment.objects.filter(is_active=True, completed_at__isnull=True).exclude(goal_days=0)

    completed_ids = []
    for c in candidates:
        age_days = (today - c.created_at.date()).days
        if age_days >= c.goal_days:
            completed_ids.append(c.id)

    if not completed_ids:
        return 0

    now = timezone.now()
    Commitment.objects.filter(id__in=completed_ids).update(
        completed_at=now,
        pending_notice="You hit 100% on this commitment - amazing work! It's staying right where it is; open it any time to relive the celebration.",
    )
    logger.info("Marked %s commitment(s) as completed (100%% of goal_days) - left active.", len(completed_ids))
    return len(completed_ids)


def purge_deleted_commitments() -> int:
    """Hard-delete a commitment ONLY once it has been soft-deleted (is_active=False,
    via the user's own Delete button - see EachCommitmentArchive) for more than 24
    hours (deactivated_at). This is the 24-hour recovery window promised to the user
    on the profile page's "recently deleted" list - before that window closes, the
    row is only HIDDEN (is_active=False), never gone. Entries cascade-delete with it.

    Rows with is_active=False but deactivated_at=None are deliberately left alone -
    that combination should not exist going forward (every path that sets
    is_active=False also stamps deactivated_at now) but if old data has it, purging
    it without ever having shown the user a 24h countdown would be unfair, so it
    just sits there until someone deliberately backfills/reviews it."""
    from origin.models import Commitment

    purge_cutoff = timezone.now() - timezone.timedelta(hours=24)
    qs = Commitment.objects.filter(
        is_active=False,
        deactivated_at__isnull=False,
        deactivated_at__lte=purge_cutoff,
    )
    count = qs.count()
    if count:
        with transaction.atomic():
            qs.delete()
        logger.info("Purged %s soft-deleted commitment(s) whose 24h recovery window has passed (and their entries).", count)
    return count


def reset_stale_streaks() -> int:
    """Zero out streak_count, but ONLY once BOTH of these are true for a commitment:
      1. today's expected check-in time (Commitment.checkin_time) has already passed, and
      2. it has genuinely been more than 24 hours since last_check_in.
    Checking (1) as well as (2) matters because checkin_time is user-configurable per
    commitment (e.g. some people's "day" ends at 23:00, others at 06:00) - resetting
    purely on a rolling 24h timer without ever looking at checkin_time could zero a
    streak in the middle of a user's still-valid check-in window on an unlucky cron
    tick. Leaves an honest pending_notice for the user either way."""
    from origin.models import Commitment

    now = timezone.now()
    local_now = timezone.localtime(now)
    today = local_now.date()
    current_tz = timezone.get_current_timezone()

    #candidates: still active, have checked in at least once, and currently show a non-zero
    #streak (nothing to reset otherwise) - the checkin_time/24h math happens per-row below
    #since checkin_time differs commitment to commitment.
    candidates = Commitment.objects.filter(
        is_active=True,
        last_check_in__isnull=False,
    ).exclude(streak_count=0)

    reset_count = 0
    for c in candidates:
        expected_checkin_today = timezone.make_aware(datetime.combine(today, c.checkin_time), current_tz)
        if local_now < expected_checkin_today:
            #today's check-in window hasn't arrived yet for THIS commitment - never reset early
            continue

        if (now - c.last_check_in) <= timezone.timedelta(hours=24):
            #still inside the 24h grace period since their last check-in - leave it alone
            continue

        c.streak_count = 0
        c.pending_notice = (
            f"Your streak on \"{c.what}\" was reset - your check-in time "
            f"({c.checkin_time.strftime('%I:%M %p')}) has passed and it had been more than "
            f"24 hours since your last check-in."
        )
        c.save(update_fields=['streak_count', 'pending_notice'])
        reset_count += 1

    if reset_count:
        logger.info("Reset %s stale streak(s) (past today's check-in time AND 24h+ since last check-in).", reset_count)
    return reset_count


def downgrade_expired_trials() -> int:
    """Every signup starts on premium for 7 days (PremiumTrial, created at signup).
    Once expires_at has passed, drop them back to free exactly once."""
    from origin.models import PremiumTrial, Profile

    now = timezone.now()
    expired = PremiumTrial.objects.filter(downgraded=False, expires_at__lte=now).select_related('user')

    downgraded_count = 0
    for trial in expired:
        profile = Profile.objects.filter(user=trial.user).first()
        if profile is not None and profile.tier == 'premium':
            profile.tier = 'free'
            profile.save(update_fields=['tier'])
        trial.downgraded = True
        trial.downgraded_at = now
        trial.save(update_fields=['downgraded', 'downgraded_at'])
        downgraded_count += 1

    if downgraded_count:
        logger.info("Downgraded %s expired premium trial(s) back to free.", downgraded_count)
    return downgraded_count


def send_inactivity_checkups() -> int:
    """The 4-day "we miss you" nudge - both email and push, to every active user whose
    last_login is 4+ days old and who hasn't already been nudged within the last 4 days.
    Push silently reaches nobody who has it off (see utility/push_sending.py); email
    always attempts to send, on the same "known production email issue" basis as
    everything else in this app - a failed email here never blocks the push half, and
    a failure for one user never stops the rest of the batch."""
    from origin.models import CustomeUser
    from utility.email_sending import send_checkup_email
    from utility.push_sending import send_push_to_user

    now = timezone.now()
    cutoff = now - timezone.timedelta(days=4)

    candidates = CustomeUser.objects.filter(is_active=True, last_login__lte=cutoff).exclude(last_login__isnull=True)
    #only re-nudge once another 4 days have passed since the last nudge - otherwise every
    #tick between day 4 and whenever they eventually return would re-send this
    due = [
        u for u in candidates
        if u.last_checkup_notice_sent_at is None or u.last_checkup_notice_sent_at <= cutoff
    ]

    sent_count = 0
    for u in due:
        email_ok = True
        try:
            send_checkup_email(to_email=u.email, username=u.username)
        except Exception as e:
            email_ok = False
            logger.error("Inactivity check-up email failed for user_id=%s: %s", u.id, e)

        try:
            send_push_to_user(
                user_id=u.id,
                title="We miss you!",
                body="It's been 4 days - your streaks are waiting. Come check in.",
                url="/v1/dashboard/",
            )
        except Exception as e:
            logger.error("Inactivity check-up push failed for user_id=%s: %s", u.id, e)

        u.last_checkup_notice_sent_at = now
        u.save(update_fields=['last_checkup_notice_sent_at'])
        sent_count += 1
        if not email_ok:
            logger.info("user_id=%s: push attempted, email failed - still counted as nudged so we don't spam-retry every tick.", u.id)

    if sent_count:
        logger.info("Sent %s inactivity check-up notice(s) (email + push).", sent_count)
    return sent_count


def run_maintenance_tick() -> dict:
    """Entry point called by the cron endpoint alongside run_due_reminders()."""
    now_local = timezone.localtime()
    completed = complete_expired_commitments()
    purged = purge_deleted_commitments()
    streaks_reset = reset_stale_streaks()
    trials_downgraded = downgrade_expired_trials()
    checkups_sent = send_inactivity_checkups()

    summary = {
        'checked_at': now_local.isoformat(),
        'commitments_completed': completed,
        'commitments_purged': purged,
        'streaks_reset': streaks_reset,
        'trials_downgraded': trials_downgraded,
        'inactivity_checkups_sent': checkups_sent,
    }
    logger.info(
        "Maintenance tick %s: %s completed, %s purged, %s streaks reset, %s trials downgraded, %s check-ups sent.",
        now_local.strftime('%Y-%m-%d %H:%M'), completed, purged, streaks_reset, trials_downgraded, checkups_sent,
    )
    return summary