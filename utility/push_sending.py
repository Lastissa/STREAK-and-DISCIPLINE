"""
ALL WEB PUSH (browser notification) SENDING LIVES HERE.

Mirrors utility/email_sending.py in spirit: build the payload, dispatch it on a
background daemon thread so the caller never blocks on it. Uses the Web Push protocol
(VAPID) via pywebpush - no third-party push provider, no Firebase - so it works for
any browser (Chrome, Firefox, Edge...) that has granted notification permission on the
site, the same way the "Add to Home Screen" / PWA pattern normally works.

Requires:
    pip install pywebpush
    VAPID_PUBLIC_KEY / VAPID_PRIVATE_KEY / VAPID_ADMIN_EMAIL set in settings/.env
    (see utility/config.py -> Static.vapid_public_key() etc, and the README section
    on generating a VAPID keypair)
"""

import json
import logging
import threading

from django.conf import settings

from utility.config import Static

logger = logging.getLogger(__name__)


def _dispatch(fn, *args, **kwargs):
    """Run a push send on a background daemon thread - same fire-and-forget pattern
    used everywhere else in utility/ so a slow/unreachable push service never blocks
    the request or the scheduler tick that triggered it.
    """
    def _inner():
        try:
            fn(*args, **kwargs)
        except Exception as e:
            logger.error("Background push send failed (%s): %s", getattr(fn, "__name__", fn), e)

    thread = threading.Thread(target=_inner, daemon=True)
    thread.start()


def _send_one_push(subscription, payload: dict) -> bool:
    """Send ONE push message to ONE browser subscription.

    subscription -- an origin.models.PushSubscription instance (or any object with
                    .endpoint, .p256dh, .auth attributes).
    payload      -- dict that becomes the JSON body the service worker receives in
                    its 'push' event, e.g. {"title": "...", "body": "...", "url": "/v1/dashboard/"}.

    Returns True if the send succeeded. If the push service reports the subscription
    is gone (410 Gone / 404 Not Found - meaning the user uninstalled, cleared site data,
    or revoked permission), the dead PushSubscription row is deleted so we stop wasting
    calls on it. Any other failure is logged and swallowed - one bad device should never
    take down the rest of the batch.
    """
    try:
        from pywebpush import webpush, WebPushException
    except ImportError:
        logger.error("pywebpush is not installed - run `pip install pywebpush` to enable push reminders.")
        return False

    try:
        webpush(
            subscription_info={
                "endpoint": subscription.endpoint,
                "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
            },
            data=json.dumps(payload),
            vapid_private_key=Static.vapid_private_key(),
            vapid_claims={"sub": f"mailto:{Static.vapid_admin_email()}"},
        )
        return True
    except WebPushException as e:
        status = getattr(e.response, "status_code", None)
        if status in (404, 410):
            # Subscription is dead on the browser's end - clean it up so future jobs
            # don't keep trying it.
            from origin.models import PushSubscription
            PushSubscription.objects.filter(endpoint=subscription.endpoint).delete()
            logger.info("Removed dead push subscription (%s) for endpoint ending in ...%s", status, subscription.endpoint[-12:])
        else:
            logger.error("Push send failed (%s): %s", status, e)
        return False


def _send_push_to_user(user_id: int, payload: dict) -> None:
    """Send the same payload to EVERY device the user has subscribed on (they might
    have push enabled on both their phone and laptop - both should light up).
    """
    from origin.models import PushSubscription

    subs = list(PushSubscription.objects.filter(user_id=user_id))
    if not subs:
        logger.info("Push reminder skipped for user_id=%s: no active push subscriptions.", user_id)
        return

    sent, failed = 0, 0
    for sub in subs:
        if _send_one_push(sub, payload):
            sent += 1
        else:
            failed += 1

    logger.info("Push reminder for user_id=%s finished: %s sent, %s failed.", user_id, sent, failed)


def send_push_to_user(user_id: int, title: str, body: str, url: str = None) -> None:
    """Async entry point: push ONE notification to every device belonging to `user_id`.

    title -- short headline shown in the OS notification (e.g. "Don't lose today, Ope")
    body  -- one or two lines of detail
    url   -- where tapping the notification should take them (defaults to the dashboard)
    """
    payload = {
        "title": title,
        "body": body,
        "url": url or (Static.custom_base_url() + "/v1/dashboard/"),
        "icon": Static.logo_url(),
    }
    _dispatch(_send_push_to_user, user_id=user_id, payload=payload)
