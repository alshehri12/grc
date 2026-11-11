"""
Notification delivery.

Notifications are created with status=pending by the application and the
automation jobs. This module pushes them out:

  * e-mail, when the recipient has an address, has not opted out
    (UserProfile.email_notifications) and GRC_AUTOMATION.EMAIL_ENABLED is on;
  * otherwise they are marked sent (in-app only).

EMAIL_BACKEND defaults to the console backend in development, so messages
are printed to the runserver / worker log instead of being sent.
"""
import logging

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

logger = logging.getLogger('grc.notifications')


def _wants_email(user):
    if not user.email:
        return False
    try:
        return bool(user.profile.email_notifications)
    except Exception:
        return True


def _email_enabled():
    return getattr(settings, 'GRC_AUTOMATION', {}).get('EMAIL_ENABLED', True)


def render_email(notification):
    subject = f"[GRC] {notification.subject}"
    body = notification.body.strip()
    base_url = getattr(settings, 'FRONTEND_URL', '')
    if base_url:
        body += f"\n\nOpen the GRC system: {base_url}"
    body += "\n\n-- \nThis is an automated message from the GRC System."
    return subject, body


def deliver_pending_notifications(limit=500):
    from .models import Notification

    pending = Notification.objects.filter(status='pending').exclude(channel='sms') \
        .select_related('recipient').order_by('created_at')[:limit]
    emailed = in_app = failed = 0
    now = timezone.now()
    for n in pending:
        if _email_enabled() and _wants_email(n.recipient):
            try:
                subject, body = render_email(n)
                send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [n.recipient.email], fail_silently=False)
                n.status, n.sent_at, n.error_message = 'sent', now, ''
                n.channel = 'email' if n.channel == 'in_app' else n.channel
                emailed += 1
            except Exception as exc:
                n.status, n.error_message = 'failed', str(exc)[:1000]
                failed += 1
                logger.warning('Email delivery failed for notification %s: %s', n.pk, exc)
        else:
            n.status, n.sent_at = 'sent', now
            in_app += 1
        n.save(update_fields=['status', 'sent_at', 'error_message', 'channel'])
    return {'emailed': emailed, 'in_app_only': in_app, 'failed': failed}
