"""Email delivery via Resend (Phase 41).

Guarded: without ``RESEND_API_KEY`` this is a no-op that logs what *would* have been
sent. That means the digest job is safe to run in CI and locally — no accidental mail.
"""

from __future__ import annotations

import logging

from src.config.settings import Settings, get_settings

logger = logging.getLogger(__name__)

_RESEND_URL = "https://api.resend.com/emails"


def is_configured(settings: Settings | None = None) -> bool:
    return bool((settings or get_settings()).resend_api_key)


def send_email(
    to: str,
    subject: str,
    html: str,
    settings: Settings | None = None,
) -> bool:
    """Send one email. Returns True if it was actually delivered."""
    settings = settings or get_settings()
    if not settings.resend_api_key:
        logger.info("email (no-op, RESEND_API_KEY unset) -> to=%s subject=%r", to, subject)
        return False

    import requests

    try:
        resp = requests.post(
            _RESEND_URL,
            headers={
                "Authorization": f"Bearer {settings.resend_api_key}",
                "Content-Type": "application/json",
            },
            json={"from": settings.email_from, "to": [to], "subject": subject, "html": html},
            timeout=15,
        )
        if resp.status_code >= 300:
            logger.warning("resend -> HTTP %s: %s", resp.status_code, resp.text[:200])
            return False
        logger.info("email sent to %s: %r", to, subject)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("resend send failed: %s", exc)
        return False
