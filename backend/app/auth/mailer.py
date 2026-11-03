import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


def send_otp_email(to_email: str, name: str, otp: str) -> None:
    if not settings.resend_api_key:
        if settings.environment == "production":
            raise RuntimeError("RESEND_API_KEY is not configured")
        logger.warning("DEV MODE: verification code for %s is %s", to_email, otp)
        return

    res = httpx.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {settings.resend_api_key}"},
        json={
            "from": settings.mail_from,
            "to": [to_email],
            "subject": f"{otp} is your Wayfind verification code",
            "html": (
                f"<p>Hi {name},</p>"
                "<p>Your Wayfind verification code is:</p>"
                f"<p style='font-size:28px;letter-spacing:6px'><b>{otp}</b></p>"
                f"<p>It expires in {settings.otp_expire_minutes} minutes. "
                "If you didn't request it, you can ignore this email.</p>"
            ),
        },
        timeout=15,
    )
    if res.status_code >= 400:
        # Resend explains the problem in the body (bad key, unverified domain, ...).
        logger.error("Resend error %s: %s", res.status_code, res.text)
    res.raise_for_status()
