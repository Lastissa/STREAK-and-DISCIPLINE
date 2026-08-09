"""
THE ACTUAL "who is due for a reminder RIGHT NOW" DECISION LIVES HERE.

This is deliberately separate from utility/email_sending.py, utility/send_bulk_email.py,
and utility/push_sending.py — those three only know how to BUILD and DELIVER a message
once they're told who to message. This file is the one that decides WHO, by walking
every active commitment and asking, per commitment:

    1. Is reminder_active True and the commitment still is_active?
    2. Has the user already checked in for it today? (an Entries row with commit_at=today)
    3. Has user_selected_reminder_time already arrived, today? <- THE IMPORTANT PART.
       This is intentionally checkin_time's cousin, not checkin_time itself: checkin_time
       is "when you're expected to have shown up by" (used for streak-break logic
       elsewhere), user_selected_reminder_time is "when I personally want to be nagged" —
       and a nag should only ever fire based on the second one, never the first.
    4. Has THIS commitment already had a reminder sent today? (last_reminder_sent_at)
       — this is the per-commitment dedupe guard so a tick that runs twice, or overlaps
       with itself, can never double-notify the same commitment.

WHY "has already arrived" instead of "matches this exact minute":
Render's free tier has no Celery worker and no built-in cron job feature, so this can't
be invoked once a minute by anything running inside the app itself. The realistic option
on a free tier is an external pinger (cron-job.org, UptimeRobot, etc) hitting an HTTP
endpoint every ~30 minutes (see origin/views/cron_job_View.py). If this engine only
matched an exact minute, a 30-minutes-apart cron would miss almost every reminder
entirely, since the one minute a commitment is "due" almost never lines up with the one
minute the cron happens to fire. Matching "time has already arrived and hasn't been sent
yet" instead means: however often you get pinged, you'll never miss a commitment, you'll
just occasionally send it a little late (up to ~one ping interval late) — which is the
correct trade-off for a free-tier setup, and exactly what was asked for.

KNOWN LIMITATION (near-midnight reminder times): because "has already arrived" is
computed against the plain time-of-day (no date arithmetic across midnight), a reminder
time in the last ~30 minutes before midnight can, in the worst case, get skipped for
that day if no ping happens to land between "reminder time" and "midnight" - the very
next ping is on a new calendar day, where that time-of-day now looks like it's still in
the future relative to "today". Not caught, not a crash, just a missed notification for
that one occurrence. Cheap way to sidestep this entirely: don't offer reminder times in
the very last 30 minutes of the day, or accept it as a known edge case for a free-tier
setup - fixing it properly would mean tracking exact last-run timestamps across midnight,
which is more machinery than a solo/free-tier project needs right now.
"""

import logging
from collections import defaultdict

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


def _commitments_due_right_now(now_local):
    """Every active, reminder-enabled commitment whose OWN user_selected_reminder_time
    has already passed today, and that has no check-in entry yet today.

    WhatsApp commitments are excluded on purpose: mode_of_delivery == 'whatsapp' isn't
    wired to a provider yet (no WhatsApp Business API integration exists in this
    codebase), so including them would silently claim/mark them as reminded without
    ever actually notifying the user. Better to skip and log than to fake a send.
    """
    from origin.models import Commitment, Entries

    today = now_local.date()
    checked_in_today_ids = set(
        Entries.objects.filter(commit_at=today).values_list('commitment_key_id', flat=True)
    )

    qs = (
        Commitment.objects.filter(
            is_active=True,
            reminder_active=True,
            user_selected_reminder_time__isnull=False,
            user_selected_reminder_time__lte=now_local.time(),
        )
        .exclude(id__in=checked_in_today_ids)
        .exclude(mode_of_delivery='whatsapp')
    )
    return qs


def _claim_for_sending(due_qs, now_local):
    """Atomically stamp last_reminder_sent_at=now on every commitment that's due AND
    hasn't already been reminded today, then return just those (freshly claimed) rows.

    This two-step "figure out ids -> bulk UPDATE by id, excluding anything already
    stamped today -> re-fetch only what the UPDATE actually touched" is the dedupe
    guard: it's what stops the same commitment being emailed/pushed twice if the cron
    endpoint is ever pinged twice in quick succession (a flaky pinger retrying, someone
    manually hitting the URL while the real cron also fires, etc). The UPDATE itself is
    one single SQL statement, so it's as atomic as the database gives us for free
    without reaching for an extra lock/queue just for this.
    """
    from origin.models import Commitment

    today = now_local.date()
    candidate_ids = list(due_qs.values_list('id', flat=True))
    if not candidate_ids:
        return Commitment.objects.none()

    with transaction.atomic():
        not_yet_reminded_today = (
            Commitment.objects.filter(id__in=candidate_ids)
            .exclude(last_reminder_sent_at__date=today)
        )
        claim_ids = list(not_yet_reminded_today.values_list('id', flat=True))
        if not claim_ids:
            return Commitment.objects.none()
        Commitment.objects.filter(id__in=claim_ids).update(last_reminder_sent_at=now_local)

    return Commitment.objects.filter(id__in=claim_ids).select_related('user')


def _build_email_item(user, commitments, profile):
    return {
        'email': user.email,
        'username': user.username,
        'pending_names': [c.what for c in commitments],
        'pending_count': len(commitments),
        'best_streak': max((c.streak_count for c in commitments), default=0),
        'zeal_score': profile.zeal_score if profile else 0,
    }


def _push_title_and_body(user, commitments):
    names = [c.what for c in commitments]
    count = len(names)
    best_streak = max((c.streak_count for c in commitments), default=0)

    shown = ", ".join(names[:2])
    if count > 2:
        shown += f" +{count - 2} more"

    title = (
        f"{user.username}, your {best_streak}-day streak is waiting"
        if best_streak > 0 else
        f"{user.username}, today's check-in is still open"
    )
    plural = "commitment" if count == 1 else "commitments"
    body = f"You haven't checked in for {count} {plural}: {shown}"
    return title, body


def run_due_reminders() -> dict:
    """Entry point for both the cron-hit HTTP endpoint and the (optional, local-only)
    management command. One call = one tick = one pass over every commitment whose
    personal reminder time has already arrived today and hasn't been handled yet.

    Groups the due commitments per (user, delivery mode) so a user with three
    commitments all reminding via email gets ONE email listing all three once this tick
    catches them, not three separate emails — while a user with commitments on
    different delivery modes still gets each mode handled independently.

    Safe to call as often as you like (every 30 minutes, every 5, or by hand while
    testing) — the dedupe guard in _claim_for_sending means an extra call just finds
    nothing new to do rather than double-sending.

    Returns a small summary dict, mainly so the endpoint/command can report something
    useful and so tests can assert on it.
    """
    now_local = timezone.localtime()
    due_qs = _commitments_due_right_now(now_local)
    claimed = list(_claim_for_sending(due_qs, now_local))

    if not claimed:
        logger.info("Reminder tick %s: nothing due.", now_local.strftime('%Y-%m-%d %H:%M'))
        return {'checked_at': now_local.isoformat(), 'commitments_due': 0, 'emails_queued': 0, 'push_queued': 0}

    buckets = defaultdict(list)
    for c in claimed:
        buckets[(c.user_id, c.mode_of_delivery)].append(c)

    from origin.models import Profile
    user_ids = {uid for uid, _mode in buckets.keys()}
    profiles = {p.user_id: p for p in Profile.objects.filter(user_id__in=user_ids)}

    email_items = []
    push_count = 0
    push_skipped_no_subscription = 0

    for (user_id, mode), commitments in buckets.items():
        user = commitments[0].user
        profile = profiles.get(user_id)

        if mode == 'email':
            email_items.append(_build_email_item(user, commitments, profile))

        elif mode == 'push':
            from origin.models import PushSubscription
            from utility.push_sending import send_push_to_user

            if not PushSubscription.objects.filter(user_id=user.id).exists():
                # This commitment is about to be marked "reminded" for today with
                # nothing actually deliverable - the person picked Push but never
                # completed the browser permission flow (or revoked it since). Logged
                # loudly and counted separately in the summary rather than folded into
                # push_queued, since "queued" would wrongly imply something was sent.
                push_skipped_no_subscription += 1
                logger.warning(
                    "Commitment(s) %s set to push for user_id=%s, but they have zero active "
                    "push subscriptions - nothing will be delivered. They likely never "
                    "completed the browser permission prompt, or revoked it since.",
                    [c.id for c in commitments], user.id
                )
                continue

            title, body = _push_title_and_body(user, commitments)
            send_push_to_user(user_id=user.id, title=title, body=body)
            push_count += 1

        else:
            # Shouldn't happen (whatsapp already excluded upstream, model choices are
            # validated at write time) but log instead of silently dropping if it does.
            logger.warning("Skipping reminder for commitment(s) %s: unhandled mode_of_delivery=%s",
                            [c.id for c in commitments], mode)

    if email_items:
        from utility.send_bulk_email import send_due_checkin_reminder_batch
        send_due_checkin_reminder_batch(email_items)

    summary = {
        'checked_at': now_local.isoformat(),
        'commitments_due': len(claimed),
        'emails_queued': len(email_items),
        'push_queued': push_count,
        'push_skipped_no_subscription': push_skipped_no_subscription,
    }
    logger.info("Reminder tick %s: %s commitment(s) due -> %s email batch(es), %s push send(s), %s push skipped (no subscription).",
                now_local.strftime('%Y-%m-%d %H:%M'), summary['commitments_due'], summary['emails_queued'],
                summary['push_queued'], summary['push_skipped_no_subscription'])
    return summary
