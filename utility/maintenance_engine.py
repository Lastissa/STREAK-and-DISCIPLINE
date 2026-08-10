"""
EVERYTHING IN HERE RUNS OFF THE SAME EXTERNAL CRON PING THAT DRIVES THE CHECK-IN
REMINDERS (see origin/views/cron_job_View.py + utility/reminder_engine.py). There is
only ONE http endpoint configured on cron-job.org/UptimeRobot, so every periodic
task the app needs lives on that single tick, not four different endpoints.

Four jobs live here, in the order they should run:

1. `complete_expired_commitments`  - a commitment whose goal_days is not 0 (0 = forever)
   and whose age has reached goal_days is "end of life". There is intentionally NO
   archive state in this product - end of life behaves exactly like the user pressing
   Delete: is_active flips to False immediately (so it vanishes from the user's own
   commitment list the moment this tick runs) and it is queued up for real removal by
   job #2 on the NEXT tick.

2. `purge_deleted_commitments`     - hard-deletes (DB row gone, Entries cascade with it)
   every commitment that is currently is_active=False, regardless of whether it got
   there via the user's own Delete button (see EachCommitmentArchive) or via job #1
   above. Deliberately one tick behind completion/deletion (never in the same pass) so
   a freshly-deleted commitment is never mid-air between "hidden" and "gone" during the
   same request - it is simply hidden the moment it happens, and permanently gone the
   next time this job runs.

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
"""

import logging

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


def complete_expired_commitments() -> int:
    """Auto end-of-life: goal_days != 0 (0 means forever/never auto-ends) and the
    commitment has been running >= goal_days. Marked exactly like a user delete -
    is_active=False, hidden immediately - and left for purge_deleted_commitments to
    actually remove next tick."""
    from origin.models import Commitment

    today = timezone.now().date()
    candidates = Commitment.objects.filter(is_active=True).exclude(goal_days=0)

    completed_ids = []
    for c in candidates:
        age_days = (today - c.created_at.date()).days
        if age_days >= c.goal_days:
            completed_ids.append(c.id)

    if not completed_ids:
        return 0

    now = timezone.now()
    Commitment.objects.filter(id__in=completed_ids).update(
        is_active=False,
        completed_at=now,
        pending_notice="You hit your goal on this commitment and it's been marked complete - nice work. It's now been removed from your active list.",
    )
    logger.info("Completed %s commitment(s) that reached their goal_days.", len(completed_ids))
    return len(completed_ids)


def purge_deleted_commitments() -> int:
    """Hard-delete every commitment currently sitting at is_active=False (whether from
    a user Delete or from complete_expired_commitments above). Entries cascade-delete
    with it. This is the "next cron job" the delete button queues work up for."""
    from origin.models import Commitment

    qs = Commitment.objects.filter(is_active=False)
    count = qs.count()
    if count:
        with transaction.atomic():
            qs.delete()
        logger.info("Purged %s soft-deleted commitment(s) (and their entries).", count)
    return count


def reset_stale_streaks() -> int:
    """Zero out streak_count for any still-active commitment where more than 24 hours
    have passed since last_check_in, and leave an honest pending_notice for the user."""
    from origin.models import Commitment

    cutoff = timezone.now() - timezone.timedelta(hours=24)
    stale = Commitment.objects.filter(
        is_active=True,
        last_check_in__isnull=False,
        last_check_in__lt=cutoff,
    ).exclude(streak_count=0)

    reset_count = 0
    for c in stale:
        c.streak_count = 0
        c.pending_notice = f"Your streak on \"{c.what}\" was reset - it had been more than 24 hours since your last check-in."
        c.save(update_fields=['streak_count', 'pending_notice'])
        reset_count += 1

    if reset_count:
        logger.info("Reset %s stale streak(s) (no check-in for 24h+).", reset_count)
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


def run_maintenance_tick() -> dict:
    """Entry point called by the cron endpoint alongside run_due_reminders()."""
    now_local = timezone.localtime()
    completed = complete_expired_commitments()
    purged = purge_deleted_commitments()
    streaks_reset = reset_stale_streaks()
    trials_downgraded = downgrade_expired_trials()

    summary = {
        'checked_at': now_local.isoformat(),
        'commitments_completed': completed,
        'commitments_purged': purged,
        'streaks_reset': streaks_reset,
        'trials_downgraded': trials_downgraded,
    }
    logger.info(
        "Maintenance tick %s: %s completed, %s purged, %s streaks reset, %s trials downgraded.",
        now_local.strftime('%Y-%m-%d %H:%M'), completed, purged, streaks_reset, trials_downgraded,
    )
    return summary
