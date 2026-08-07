"""
ALL BULK / BROADCAST EMAIL LIVES HERE.

Difference from utility/email_sending.py:
- email_sending.py  -> one-to-one transactional mail (password reset, partner requests...)
- send_bulk_email.py (this file) -> one-to-many broadcast mail sent to a *list* of users
  at once: product updates, news posts, and anything else (category 'other').

Every send goes through Django's send_mail(), using whatever EMAIL_BACKEND is configured
in settings.py. No third-party mail API (Resend, etc.) is used here.
"""

import logging
import threading

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.utils import timezone

from utility.config import Static
from utility.email_sending import _button, _shell  # reuse the exact same visual shell as transactional mail

logger = logging.getLogger(__name__)


def _dispatch(fn, *args, **kwargs):
    """Run a bulk send on a background daemon thread so the caller (a view/admin action/
    management command) doesn't block while hundreds of emails go out.
    """
    def _inner():
        try:
            fn(*args, **kwargs)
        except Exception as e:  # last line of defense in a background thread
            logger.error("Bulk email send failed (%s): %s", getattr(fn, "__name__", fn), e)

    thread = threading.Thread(target=_inner, daemon=True)
    thread.start()


def _default_recipients() -> list:
    """Everyone who opted in to newsletter/update style email and is not deactivated.

    Import of Profile is deliberately done inside the function (not at module load time)
    to avoid circular-import issues between utility/ and the origin app.
    """
    from origin.models import Profile

    return list(
        Profile.objects.filter(receive_newsletter=True, user__is_active=True)
        .select_related('user')
        .values_list('user__email', flat=True)          #RETURN JUSTA LIST
    )


def _send_bulk(subject: str, html_body: str, recipient_emails: list, plain_fallback: str = "") -> None:
    """Send the same email to many people.

    Each recipient gets their OWN message (one connection, reused across sends) so nobody
    ever sees another recipient's email address, unlike a single message with everyone in `to`.
    """
    recipient_emails = [e for e in dict.fromkeys(recipient_emails) if e]  # de-dupe, drop empties
    if not recipient_emails:
        logger.warning("Bulk email '%s' skipped: no recipients matched.", subject)
        return

    connection = get_connection()
    connection.open()
    sent, failed = 0, 0
    try:
        for email in recipient_emails:
            try:
                message = EmailMultiAlternatives(
                    subject=subject,
                    body=plain_fallback or "This email is best viewed in an HTML capable mail client.",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[email],
                    connection=connection,
                )
                message.attach_alternative(html_body, "text/html")
                message.send()
                sent += 1
            except Exception as e:  # noqa: BLE001 - one bad address shouldn't kill the whole batch
                failed += 1
                logger.error("Bulk email '%s' failed for %s: %s", subject, email, e)
    finally:
        connection.close()

    logger.info("Bulk email '%s' finished: %s sent, %s failed.", subject, sent, failed)


def _standard_body(heading: str, message_html: str, cta_label: str = None, cta_link: str = None) -> str:
    body = f"""
        <h1 style="margin:0 0 14px;font-size:19px;color:#0f172a;font-weight:700">{heading}</h1>
        <p style="margin:0 0 18px;font-size:14px;color:#334155;line-height:1.6">{message_html}</p>
    """
    if cta_label and cta_link:
        body += _button(cta_label, cta_link)
    return body


# ---------------------------------------------------------------------------
# 1. Product / feature updates (ASYNC, bulk)
# ---------------------------------------------------------------------------

def send_update_email(heading: str, message_html: str, cta_label: str = None, cta_link: str = None,
                       subject: str = None, recipient_emails: list = None) -> None:
    """Broadcast a product-update email (new feature, change, fix) to opted-in users.

    heading         -- short headline, e.g. "Custom check-in reminders are live"
    message_html    -- the body copy (can contain simple inline HTML like <strong>)
    cta_label/link  -- optional button, e.g. ("See what's new", ".../v1/dashboard/")
    subject         -- optional override; defaults to "STREAK & DISCIPLINE update: {heading}"
    recipient_emails -- optional explicit list; defaults to everyone with receive_newsletter=True
    """
    recipients = recipient_emails if recipient_emails is not None else _default_recipients()
    subject = subject or f"STREAK & DISCIPLINE update: {heading}"

    html = _shell(
        preheader=heading,
        eyebrow="Product Update",
        body_html=_standard_body(heading, message_html, cta_label, cta_link),
    )
    _dispatch(_send_bulk, subject=subject, html_body=html, recipient_emails=recipients, plain_fallback=heading)


# ---------------------------------------------------------------------------
# 2. News posts (ASYNC, bulk) - mirrors the origin.models.News model
# ---------------------------------------------------------------------------

def send_news_email(news_instance=None, *, title: str = None, excerpt: str = None,
                     banner: str = None, read_time: int = None, recipient_emails: list = None) -> None:
    """Broadcast a News item to opted-in users.

    Pass an origin.models.News instance directly, e.g.:
        send_news_email(news_instance=my_news_obj)
    OR pass the fields yourself if you don't have a saved instance yet:
        send_news_email(title="...", excerpt="...", banner="...", read_time=3)
    """
    title = title or getattr(news_instance, 'title', None)
    excerpt = excerpt or getattr(news_instance, 'excerpt', '')
    banner = banner or getattr(news_instance, 'banner', None)
    read_time = read_time if read_time is not None else getattr(news_instance, 'read_time', None)

    if not title:
        raise ValueError("send_news_email needs a title - pass news_instance or title=...")

    read_note = f'<p style="margin:0 0 10px;font-size:12px;color:#94a3b8">{read_time} min read</p>' if read_time else ""
    banner_html = f'<img src="{banner}" alt="" style="width:100%;border-radius:10px;margin-bottom:16px">' if banner else ""
    news_link = Static.custom_base_url() + "/v1/news/"

    body = f"""
        {banner_html}
        <h1 style="margin:0 0 8px;font-size:19px;color:#0f172a;font-weight:700">{title}</h1>
        {read_note}
        <p style="margin:0 0 18px;font-size:14px;color:#334155;line-height:1.6">{excerpt}</p>
        {_button('Read the full story', news_link)}
    """

    recipients = recipient_emails if recipient_emails is not None else _default_recipients()
    html = _shell(preheader=(excerpt or title)[:120], eyebrow="News", body_html=body)
    _dispatch(
        _send_bulk,
        subject=f"STREAK & DISCIPLINE news: {title}",
        html_body=html,
        recipient_emails=recipients,
        plain_fallback=excerpt or title,
    )


# ---------------------------------------------------------------------------
# 3. Other / general-purpose broadcast (ASYNC, bulk)
# ---------------------------------------------------------------------------

def send_other_email(subject: str, heading: str, message_html: str, cta_label: str = None,
                      cta_link: str = None, recipient_emails: list = None) -> None:
    """Catch-all broadcast for anything that isn't a product update or a news post,
    e.g. announcements, surveys, policy or downtime notices, seasonal messages.
    """
    recipients = recipient_emails if recipient_emails is not None else _default_recipients()
    html = _shell(
        preheader=heading,
        eyebrow="Announcement",
        body_html=_standard_body(heading, message_html, cta_label, cta_link),
    )
    _dispatch(_send_bulk, subject=subject, html_body=html, recipient_emails=recipients, plain_fallback=heading)


# ---------------------------------------------------------------------------
# 4. Daily check-in reminder (ASYNC, bulk job — PERSONALIZED per recipient)
# ---------------------------------------------------------------------------
#
# This is still a "bulk" send in every mechanical sense — one job, one query, one reused
# SMTP connection, fired at everyone who's overdue for the day in a single pass — but unlike
# send_update_email/send_news_email/send_other_email above, every recipient gets their OWN
# subject + body built from their OWN name, streak, and pending commitments. Nobody sees the
# same sentence as anybody else. Meant to be triggered by a scheduler/cron/management command
# a little before the day rolls over (see Commitment.checkin_time / user_selected_reminder_time).

def _send_checkin_reminders_batch(items: list) -> None:
    """items: list of dicts, each already carrying everything needed to build ONE
    person's personalized email (see _build_checkin_reminder_email). Sent one-by-one over a
    single reused connection — same low-overhead pattern as _send_bulk, just personalized.
    """
    items = [i for i in items if i.get('email')]
    if not items:
        logger.info("Check-in reminder batch: nobody was overdue, nothing sent.")
        return

    connection = get_connection()
    connection.open()
    sent, failed = 0, 0
    try:
        for item in items:
            try:
                subject, html_body, plain_fallback = _build_checkin_reminder_email(item)
                message = EmailMultiAlternatives(
                    subject=subject,
                    body=plain_fallback,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[item['email']],
                    connection=connection,
                )
                message.attach_alternative(html_body, "text/html")
                message.send()
                sent += 1
            except Exception as e:  # noqa: BLE001 - one bad address/record shouldn't kill the batch
                failed += 1
                logger.error("Check-in reminder failed for %s: %s", item.get('email'), e)
    finally:
        connection.close()

    logger.info("Check-in reminder batch finished: %s sent, %s failed.", sent, failed)


def _build_checkin_reminder_email(item: dict) -> tuple:
    """Build ONE person's subject/html/plain-text from their own data. Nothing here is shared
    boilerplate copy — every line reads differently depending on who it's for.

    item keys: email, username, pending_names (list[str]), pending_count (int),
               best_streak (int), zeal_score (int)
    """
    username = item.get('username') or 'there'
    pending_names = item.get('pending_names') or []
    pending_count = item.get('pending_count', len(pending_names))
    best_streak = item.get('best_streak', 0)
    zeal_score = item.get('zeal_score', 0)
    dashboard_link = Static.custom_base_url() + "/v1/dashboard/"

    shown = pending_names[:3]
    names_html = ", ".join(f"<strong>{n}</strong>" for n in shown)
    if pending_count > len(shown):
        names_html += f" and {pending_count - len(shown)} more"

    plural = "commitment" if pending_count == 1 else "commitments"

    streak_line = (
        f"Your best active streak right now is <strong>{best_streak} day{'s' if best_streak != 1 else ''}</strong> — "
        f"that's the one with the most to lose if today slips."
        if best_streak > 0 else
        "You're at the very start — today is a chance to put the first real day on the board."
    )

    body = f"""
        <h1 style="margin:0 0 14px;font-size:19px;color:#0f172a;font-weight:700">Don't lose today, {username}</h1>
        <p style="margin:0 0 14px;font-size:14px;color:#334155;line-height:1.6">
            You haven't checked in yet today for {pending_count} {plural}: {names_html}.
        </p>
        <p style="margin:0 0 18px;font-size:14px;color:#334155;line-height:1.6">
            {streak_line}
        </p>
        <table cellpadding="0" cellspacing="0" role="presentation" style="width:100%;margin-bottom:6px">
            <tr>
                <td style="background:#fff7ed;border:1px solid #fed7aa;border-radius:8px;padding:12px 14px">
                    <p style="margin:0;font-size:13px;color:#9a3412;line-height:1.7">
                        Momentum is easy to lose and slow to rebuild. A short, honest check-in
                        (even a minimum-effort one) keeps the streak alive.
                    </p>
                </td>
            </tr>
        </table>
        {_button('Check in now', dashboard_link)}
        <p style="margin:16px 0 0;font-size:12px;color:#94a3b8;line-height:1.6">
            Zeal Score right now: {zeal_score}. This reminder only goes out on days you're actually behind.
        </p>
    """

    subject = (
        f"{username}, your {best_streak}-day streak is waiting on you"
        if best_streak > 0 else
        f"{username}, today's check-in is still open"
    )
    plain = (
        f"Hi {username}, you haven't checked in today for {pending_count} {plural}. "
        f"Check in now: {dashboard_link}"
    )

    html = _shell(
        preheader=f"{pending_count} {plural} still waiting on today's check-in.",
        eyebrow="Check-in Reminder",
        body_html=body,
        footer_note="You're getting this because you have reminders turned on for at least one active commitment. "
                    "You can turn reminders off any time from that commitment's settings.",
    )
    return subject, html, plain


def _run_checkin_reminder_job(recipient_emails: list = None) -> None:
    """Find every active, reminder-enabled commitment with no entry yet today, group it by
    owner, and hand each owner's own data off to be turned into their own personalized email.

    recipient_emails -- optional explicit allowlist (e.g. only users whose personal
    checkin_time has already passed); defaults to everyone who qualifies.
    """
    from origin.models import Commitment, Entries, Profile

    today = timezone.localdate()
    checked_in_today_ids = set(
        Entries.objects.filter(commit_at=today).values_list('commitment_key_id', flat=True)
    )

    qs = (
        Commitment.objects.filter(is_active=True, reminder_active=True)
        .exclude(id__in=checked_in_today_ids)
        .select_related('user')
    )
    if recipient_emails is not None:
        qs = qs.filter(user__email__in=recipient_emails)

    per_user = {}
    for c in qs:
        bucket = per_user.setdefault(c.user_id, {'user': c.user, 'commitments': []})
        bucket['commitments'].append(c)

    if not per_user:
        logger.info("Check-in reminder job: nobody is overdue right now.")
        return

    profiles = {
        p.user_id: p for p in Profile.objects.filter(user_id__in=per_user.keys())
    }

    items = []
    for uid, bucket in per_user.items():
        user = bucket['user']
        commitments = bucket['commitments']
        profile = profiles.get(uid)
        items.append({
            'email': user.email,
            'username': user.username,
            'pending_names': [c.what for c in commitments],
            'pending_count': len(commitments),
            'best_streak': max((c.streak_count for c in commitments), default=0),
            'zeal_score': profile.zeal_score if profile else 0,
        })

    _send_checkin_reminders_batch(items)


def send_checkin_reminder_emails(recipient_emails: list = None) -> None:
    """Async entry point — call this from a scheduler/cron/management command a little
    before the day ends. Bulk in mechanics (one job, one connection, everyone overdue in
    one pass), personalized in substance (own name, own streak, own pending commitments
    per recipient).

    recipient_emails -- optional explicit allowlist of emails to restrict the run to
                         (e.g. only users whose own reminder time just passed).
    """
    _dispatch(_run_checkin_reminder_job, recipient_emails=recipient_emails)