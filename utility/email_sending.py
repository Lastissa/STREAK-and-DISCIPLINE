"""
ALL EMAIL CONFIGURATION TO INDIVIDUALs LIVES HERE
"""

import os, random
from django.core.mail import send_mail
from django.conf import settings
import threading
import logging
from utility.config import Static

logger = logging.getLogger(__name__)


def _dispatch(fn, *args, **kwargs):
    """Run an email sending function on a daemon background thread (simple and fast async send).
    """
    def _innerDef():
        try:
            fn(*args, **kwargs)
        except Exception as e: 
            logger.error("Background email send failed (%s): %s", getattr(fn, "__name__", fn), e)

    thread = threading.Thread(target=_innerDef, daemon=True)
    thread.start()




def _button(label: str, href: str) -> str:
    """"""
    return f"""
    <table cellpadding="0" cellspacing="0" role="presentation" style="margin:28px 0 8px">
        <tr>
            <td align="center" style="background:#2563eb;border-radius:10px">
                <a href="{href}" style="display:inline-block;padding:13px 30px;color:#ffffff;text-decoration:none;
                   font-weight:600;font-size:14px;font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif">
                    {label}
                </a>
            </td>
        </tr>
    </table>
    """


def _shell(preheader: str, eyebrow: str, body_html: str, footer_note: str = "dstrict") -> str:
    """Wrap inner content in the shared STREAK & DISCIPLINE email shell.

    preheader   -- hidden preview text shown next to the subject line in most inboxes.
    eyebrow     -- small label under the logo (e.g. "Password Reset", "Welcome").
    body_html   -- the actual message: heading, paragraphs, button, all pre-built.
    footer_note -- optional extra line under the standard footer (e.g. a security notice).
    """
    logo = Static.logo_url()
    base = Static.custom_base_url()

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta name="color-scheme" content="light dark">
    </head>
    <body style="margin:0;padding:0;background:#f1f5f9;font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif">
        <div style="display:none;max-height:0;overflow:hidden;opacity:0">{preheader}&nbsp;&#8203;</div>
        <table width="100%" cellpadding="0" cellspacing="0" role="presentation" style="background:#f1f5f9;padding:32px 16px">
            <tr>
                <td align="center">
                    <table width="480" cellpadding="0" cellspacing="0" role="presentation"
                           style="width:100%;max-width:480px;background:#ffffff;border-radius:14px;overflow:hidden;border:1px solid #e2e8f0">

                        <!-- Header -->
                        <tr>
                            <td style="padding:22px 26px;background:#0a0e17">
                                <table cellpadding="0" cellspacing="0" role="presentation">
                                    <tr>
                                        <td style="padding-right:12px">
                                            <img src="{logo}" alt="STREAK & DISCIPLINE" width="36" height="36"
                                                 style="border-radius:8px;display:block">
                                        </td>
                                        <td>
                                            <p style="margin:0;font-weight:700;font-size:14px;letter-spacing:.02em;color:#ffffff">STREAK &amp; DISCIPLINE</p>
                                            <p style="margin:3px 0 0;font-size:12px;color:#93c5fd">{eyebrow}</p>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>

                        <!-- Body -->
                        <tr>
                            <td style="padding:28px 26px 8px">
                                {body_html}
                            </td>
                        </tr>

                        <!-- Footer -->
                        <tr>
                            <td style="padding:18px 26px 24px">
                                <hr style="border:none;border-top:1px solid #e2e8f0;margin:0 0 16px">
                                {f'<p style="margin:0 0 12px;font-size:12px;color:#64748b;line-height:1.6">{footer_note}</p>' if footer_note else ''}
                                <p style="margin:0;font-size:12px;color:#94a3b8;line-height:1.6">
                                    Questions? Write to
                                    <a href="{Static.official_email()}" style="color:#2563eb;text-decoration:none">{Static.official_email()}</a>
                                    or message us on
                                    <a href="https://wa.me/2347013687825" style="color:#2563eb;text-decoration:none">WhatsApp</a>.
                                </p>
                                <p style="margin:10px 0 0;font-size:11px;color:#cbd5e1">
                                    STREAK &amp; DISCIPLINE &middot; {base}
                                </p>
                            </td>
                        </tr>

                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """


# ---------------------------------------------------------------------------
# 1. Password reset — the link to start a reset (SYNCHRONOUS: The result is needed wether it failed or not so i cant use threading here
# ---------------------------------------------------------------------------

def send_password_reset_email(to_email: str, endpoint: str, expiry: int, username: str) -> None:
    """Send the "reset your password" link. Expires in `expiry` seconds."""

    minutes = max(1, int(expiry / 60))
    link = Static.custom_base_url() + endpoint
    # unique per-send tag purely so mail clients don't thread/dedupe repeat requests
    dedupe_tag = "".join(random.sample("abcdefghijklmnopqrstuvwxyz0123456789", 8))

    body = f"""
        <h1 style="margin:0 0 14px;font-size:19px;color:#0f172a;font-weight:700">Reset your password</h1>
        <p style="margin:0 0 18px;font-size:14px;color:#334155;line-height:1.6">
            Hi {username}, we got a request to reset the password on your account.
            Click the button below to choose a new one. The link is valid for
            <strong>{minutes} minute{'s' if minutes != 1 else ''}</strong> and can only be used once.
        </p>
        {_button('Reset my password', link)}
        <p style="margin:18px 0 0;font-size:12px;color:#94a3b8;line-height:1.6">
            Didn't ask for this? You can safely ignore this email. Your password stays the same
            and no one can reset it without access to this link.
        </p>
        <p style="margin:14px 0 0;font-size:11px;color:#cbd5e1">Ref: {dedupe_tag}</p>
    """
    #if this fail i can see the output instantly
    send_mail(
        subject= "Reset your STREAK & DISCIPLINE password",
        message= f"Hi {username}, reset your password here: {link} (expires in {minutes} minute{'s' if minutes != 1 else ''}).",
        from_email= settings.DEFAULT_FROM_EMAIL,
        recipient_list= [to_email],
        html_message= _shell(
            preheader=f"This link expires in {minutes} minutes.",
            eyebrow="Password Reset",
            body_html=body,
            footer_note="For your safety: STREAK & DISCIPLINE staff will never call, text, or email you asking for this link or your password.",
        )
    )


# ---------------------------------------------------------------------------
# 2. Password reset confirmation — sent right after the new password is saved (ASYNC)
# ---------------------------------------------------------------------------

def inner_send_password_reset_successful_email(to_email: str, username: str) -> None:
    """All this will be put inside the threadding custom def. """
    login_link = Static.custom_base_url() + "/v1/login/"
    reset_link = Static.custom_base_url() + "/v1/password-reset/"

    body = f"""
        <h1 style="margin:0 0 14px;font-size:19px;color:#0f172a;font-weight:700">Your password has been changed</h1>
        <p style="margin:0 0 18px;font-size:14px;color:#334155;line-height:1.6">
            Hi {username}, this confirms the password on your account was just updated.
            If that was you, there's nothing else to do, you're set.
        </p>
        {_button('Sign in', login_link)}
        <table cellpadding="0" cellspacing="0" role="presentation" style="margin-top:20px;width:100%">
            <tr>
                <td style="background:#fef2f2;border-left:3px solid #ef4444;border-radius:8px;padding:12px 14px">
                    <p style="margin:0;font-size:12px;color:#991b1b;line-height:1.6">
                        <strong>Wasn't you?</strong> Someone else may have access to your account.
                        <a href="{reset_link}" style="color:#991b1b;text-decoration:underline">Reset your password again</a>
                        right away, then contact support so we can help you lock things down.
                    </p>
                </td>
            </tr>
        </table>
    """

    send_mail(
        subject= "Your password was changed",
        message= f"Hi {username}, this confirms the password on your account was just changed. If this wasn't you, reset your password again right away at {reset_link}.",
        from_email= settings.DEFAULT_FROM_EMAIL,
        recipient_list= [to_email],
        html_message= _shell(
            preheader="Confirming your password was just updated.",
            eyebrow="Security Notice",
            body_html=body,
        ),
    )


def send_password_reset_successful_email(to_email: str, username: str) -> None:
    """Async: notify the user their password reset went through."""
    _dispatch(inner_send_password_reset_successful_email, to_email=to_email, username=username)


# ---------------------------------------------------------------------------
# 3. Friend / partner request received (ASYNC)
# ---------------------------------------------------------------------------

def _send_partner_request_notification(to_email: str, from_username: str, from_userid: str) -> None:
    dashboard_link = Static.custom_base_url() + "/v1/dashboard/relationship/"

    body = f"""
        <h1 style="margin:0 0 14px;font-size:19px;color:#0f172a;font-weight:700">{from_username} wants to be your accountability partner</h1>
        <p style="margin:0 0 14px;font-size:14px;color:#334155;line-height:1.6">
            <strong>@{from_userid}</strong> sent you a partner request. If you accept, you'll be able to see their:
        </p>
        <table cellpadding="0" cellspacing="0" role="presentation" style="width:100%;margin-bottom:16px">
            <tr>
                <td style="background:#f0f9ff;border:1px solid #bae6fd;border-radius:8px;padding:12px 14px">
                    <p style="margin:0;font-size:13px;color:#0c4a6e;line-height:1.7">
                        Combined streak count &middot; Zeal Score &middot;.
                    </p>
                </td>
            </tr>
        </table>
        <p style="margin:0 0 4px;font-size:13px;color:#64748b;line-height:1.6">
            This is one-way: {from_username} sees nothing of yours unless you send them a request back.
        </p>
        {_button('Review the request', dashboard_link)}
        <p style="margin:16px 0 0;font-size:12px;color:#94a3b8;line-height:1.6">
            You can accept or decline from Dashboard -> Relationships -> Received.
        </p>
    """

    send_mail(
        subject= f"{from_username} wants to be your accountability partner",
        message= f"@{from_userid} sent you a partner request. Review it at {dashboard_link}.",
        from_email= settings.DEFAULT_FROM_EMAIL,
        recipient_list= [to_email],
        html_message= _shell(
            preheader=f"@{from_userid} sent you a partner request.",
            eyebrow="Partner Request",
            body_html=body,
        ),
    )


def send_partner_request_notification(to_email: str, from_username: str, from_userid: str) -> None:
    """Async: sent the moment a partner/friend request is created to the reciver attaching the sender"""
    _dispatch(_send_partner_request_notification, to_email=to_email, from_username=from_username, from_userid=from_userid)


# ---------------------------------------------------------------------------
# 4. Partner request accepted (ASYNC)
# ---------------------------------------------------------------------------

def _send_partner_request_accepted_email(to_email: str, sender_username: str, accepter_userid: str) -> None:
    dashboard_link = Static.custom_base_url() + "/v1/dashboard/relationship/"

    body = f"""
        <h1 style="margin:0 0 14px;font-size:19px;color:#0f172a;font-weight:700">{accepter_userid} accepted your partner request</h1>
        <p style="margin:0 0 16px;font-size:14px;color:#334155;line-height:1.6">
            Hi {sender_username}, <strong>@{accepter_userid}</strong> just accepted. They can now see your
            combined streak and Zeal Score from their partner widget on the dashboard.
        </p>
        {_button('View your partners', dashboard_link)}
        <p style="margin:16px 0 0;font-size:12px;color:#94a3b8;line-height:1.6">
            Showing up together tends to work better than showing up alone. Check in on each other.
        </p>
    """

    send_mail(
        subject= f"{accepter_userid} accepted your partner request",
        message= f"@{accepter_userid} accepted your partner request. View your partners at {dashboard_link}.",
        from_email= settings.DEFAULT_FROM_EMAIL,
        recipient_list= [to_email],
        html_message= _shell(
            preheader=f"@{accepter_userid} is now your accountability partner.",
            eyebrow="Partner Request Accepted",
            body_html=body,
        ),
    )


def send_partner_request_accepted_email(to_email: str, sender_username: str, accepter_username: str, accepter_userid: str) -> None:
    """Async: sent to the original requester when the other person accepts."""
    _dispatch(
        _send_partner_request_accepted_email,
        to_email=to_email,
        sender_username=sender_username,
        accepter_username=accepter_username,
        accepter_userid=accepter_userid,
    )


# ---------------------------------------------------------------------------
# 5. Partner request rejected (ASYNC)
# ---------------------------------------------------------------------------

def _send_partner_request_rejected_email(to_email: str, sender_username: str) -> None:
    search_link = Static.custom_base_url() + "/v1/dashboard/relationship/"

    body = f"""
        <h1 style="margin:0 0 14px;font-size:19px;color:#0f172a;font-weight:700">Your partner request wasn't accepted</h1>
        <p style="margin:0 0 16px;font-size:14px;color:#334155;line-height:1.6">
            Hi {sender_username}, the accountability partner request you sent was declined.
            No details are shared beyond that, it happens, and it's not a reflection on your streak.
        </p>
        {_button('Find another partner', search_link)}
        <p style="margin:16px 0 0;font-size:12px;color:#94a3b8;line-height:1.6">
            You're welcome to send a new request to anyone else in partner mode whenever you're ready.
        </p>
    """

    send_mail(
        subject= "Your partner request was declined",
        message= f"Hi {sender_username}, the accountability partner request you sent was declined. You can send a new request any time at {search_link}.",
        from_email= settings.DEFAULT_FROM_EMAIL,
        recipient_list= [to_email],
        html_message= _shell(
            preheader="Your accountability partner request was declined.",
            eyebrow="Partner Request Declined",
            body_html=body,
        ),
    )


def send_partner_request_rejected_email(to_email: str, sender_username: str) -> None:
    """Async: sent to the original requester when the other person declines."""
    _dispatch(_send_partner_request_rejected_email, to_email=to_email, sender_username=sender_username)


# ---------------------------------------------------------------------------
# 6. Partner request received AGAIN, after the receiver previously rejected
#    this same sender (ASYNC)
# ---------------------------------------------------------------------------

def _send_partner_request_notification_previously_rejected(to_email: str, from_username: str, from_userid: str) -> None:
    """Same moment as _send_partner_request_notification (a request just landed in the
    receiver's inbox) but this time OUR records show the receiver rejected a request from
    this exact sender before. We say so plainly so accepting is an informed, deliberate
    choice, not something that slips through because the receiver forgot.
    """
    dashboard_link = Static.custom_base_url() + "/v1/dashboard/relationship/"

    body = f"""
        <h1 style="margin:0 0 14px;font-size:19px;color:#0f172a;font-weight:700">{from_username} sent you another partner request</h1>
        <table cellpadding="0" cellspacing="0" role="presentation" style="width:100%;margin-bottom:16px">
            <tr>
                <td style="background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:12px 14px">
                    <p style="margin:0;font-size:13px;color:#92400e;line-height:1.7">
                        <strong>Heads up:</strong> you previously declined a request from <strong>@{from_userid}</strong>.
                        They've sent a new one. There's no obligation, accept only if you actually want to.
                    </p>
                </td>
            </tr>
        </table>
        <p style="margin:0 0 14px;font-size:14px;color:#334155;line-height:1.6">
            <strong>@{from_userid}</strong> wants another shot at being your accountability partner. If you accept this time,
            they'll be able to see your:
        </p>
        <table cellpadding="0" cellspacing="0" role="presentation" style="width:100%;margin-bottom:16px">
            <tr>
                <td style="background:#f0f9ff;border:1px solid #bae6fd;border-radius:8px;padding:12px 14px">
                    <p style="margin:0;font-size:13px;color:#0c4a6e;line-height:1.7">
                        Combined streak count &middot; Zeal Score &middot;.
                    </p>
                </td>
            </tr>
        </table>
        <p style="margin:0 0 4px;font-size:13px;color:#64748b;line-height:1.6">
            This is one-way: {from_username} sees nothing of yours unless you send them a request back.
        </p>
        {_button('Review the request', dashboard_link)}
        <p style="margin:16px 0 0;font-size:12px;color:#94a3b8;line-height:1.6">
            You can accept or decline again from Dashboard -> Relationships -> Received. Declining again costs nothing.
        </p>
    """

    send_mail(
        subject= f"{from_username} sent you another partner request",
        message= f"@{from_userid} sent you another partner request after you previously declined one from them. Review it at {dashboard_link}.",
        from_email= settings.DEFAULT_FROM_EMAIL,
        recipient_list= [to_email],
        html_message= _shell(
            preheader=f"You declined @{from_userid} before — they tried again.",
            eyebrow="Partner Request (Again)",
            body_html=body,
        ),
    )


def send_partner_request_notification_previously_rejected(to_email: str, from_username: str, from_userid: str) -> None:
    """Async: use this INSTEAD of send_partner_request_notification whenever the receiver
    had a prior 'rejected' Friendship row with this exact sender, i.e. they're being asked
    again by someone they've already turned down once."""
    _dispatch(
        _send_partner_request_notification_previously_rejected,
        to_email=to_email,
        from_username=from_username,
        from_userid=from_userid,
    )


# ---------------------------------------------------------------------------
# 7. Staff access code — sent to the OFFICIAL inbox whenever someone requests
#    a staff signup token. This is deliberately SYNCHRONOUS: the staff-signup
#    view needs to know immediately whether the send succeeded before it tells
#    the requester "check with an admin", so I can't fire-and-forget this one
#    on a background thread like the others.
# ---------------------------------------------------------------------------

def send_checkup_email(to_email: str, username: str) -> None:
    """The 4-day "we miss you" re-engagement email - see
    utility/maintenance_engine.send_inactivity_checkups() for who gets this and when.
    Sent synchronously (no _dispatch/thread) since the cron job that calls this already
    loops over a whole batch of inactive users in one request; one slow/failed send here
    is caught by the caller and never stops the rest of the batch."""
    link = Static.custom_base_url() + "/v1/dashboard/"

    body = f"""
        <h1 style="margin:0 0 14px;font-size:19px;color:#0f172a;font-weight:700">Haven't seen you in a few days</h1>
        <p style="margin:0 0 18px;font-size:14px;color:#334155;line-height:1.6">
            Hi {username}, it's been 4 days since you last checked in on STREAK &amp; DISCIPLINE.
            Your commitments and streaks are still sitting there waiting for you - a quick
            check-in today keeps things moving.
        </p>
        {_button('Go to my dashboard', link)}
        <p style="margin:18px 0 0;font-size:12px;color:#94a3b8;line-height:1.6">
            You'll only get this if you've been away for a while - we send it again every
            4 days you're inactive, not more often than that.
        </p>
    """
    send_mail(
        subject="We miss you at STREAK & DISCIPLINE",
        message=f"Hi {username}, it's been 4 days since your last check-in. Come back: {link}",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[to_email],
        html_message=_shell(
            preheader="Your streaks are waiting for you.",
            eyebrow="Just Checking In",
            body_html=body,
            footer_note="Manage your reminder preferences anytime from Profile settings.",
        ),
    )


def send_staff_access_code_email(*, to_email: str = Static.official_email(), token: str, requester_email: str = "") -> None:
    """Email the staff/admin access `token` to `to_email` (defaults to the official
    STREAK & DISCIPLINE inbox). Nothing is ever sent straight to the person requesting
    access — an admin reads this email and passes the code to them personally, so this
    doubles as the manual vetting step before an account with is_staff=True can be made.

    to_email        -- where the code lands. Defaults to Static.official_email(); only
                        override this if you deliberately want it sent somewhere else.
    token           -- the raw access code (e.g. 'st-xxxxxxxx') to display.
    requester_email -- optional: the email the requester typed on the signup page, shown
                        in the email so the admin knows exactly who to hand the code to.
    """
    minutes = max(1, int(Static.token_expiry_time() / 60))

    body = f"""
        <h1 style="margin:0 0 14px;font-size:19px;color:#0f172a;font-weight:700">Staff access code requested</h1>
        <p style="margin:0 0 18px;font-size:14px;color:#334155;line-height:1.6">
            {f'<strong>{requester_email}</strong> just requested' if requester_email else 'Someone just requested'}
            a staff signup code on STREAK &amp; DISCIPLINE. Do not forward this code to anyone
            you haven't personally verified &mdash; read it out or share it with them directly.
        </p>
        <table cellpadding="0" cellspacing="0" role="presentation" style="width:100%;margin:0 0 18px">
            <tr>
                <td align="center" style="background:#0f172a;border-radius:10px;padding:18px">
                    <p style="margin:0 0 6px;font-size:11px;letter-spacing:.08em;color:#93c5fd;text-transform:uppercase">Access code</p>
                    <p style="margin:0;font-size:28px;font-weight:700;letter-spacing:.06em;color:#ffffff;font-family:'Courier New',monospace">{token}</p>
                </td>
            </tr>
        </table>
        <p style="margin:0;font-size:13px;color:#64748b;line-height:1.6">
            This code expires in <strong>{minutes} minute{'s' if minutes != 1 else ''}</strong> and can only be used once.
            If nobody at STREAK &amp; DISCIPLINE requested staff access, you can safely ignore this email.
        </p>
    """

    send_mail(
        subject="STREAK & DISCIPLINE staff access code" + (f" — {requester_email}" if requester_email else ""),
        message=(
            f"{requester_email or 'Someone'} requested a staff signup code.\n"
            f"Access code: {token}\n"
            f"Expires in {minutes} minute{'s' if minutes != 1 else ''}. Only share it after you've verified the requester."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[to_email],
        html_message=_shell(
            preheader=f"Access code expires in {minutes} minutes.",
            eyebrow="Staff Access Code",
            body_html=body,
            footer_note="This code grants staff-level access. Only share it with someone whose identity you've personally confirmed.",
        ),
    )