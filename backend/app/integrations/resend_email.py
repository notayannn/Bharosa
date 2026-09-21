"""
Resend integration for real email delivery. Uses their plain HTTP API
directly (no SDK dependency needed) since it's a single simple call.
"""
import requests

from app.core.config import settings


def send_email(to: str, subject: str, html_body: str) -> dict:
    response = requests.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {settings.EMAIL_API_KEY}"},
        json={
            "from": settings.EMAIL_FROM_ADDRESS,
            "to": [to],
            "subject": subject,
            "html": html_body,
        },
        timeout=15,
    )
    response.raise_for_status()
    return response.json()