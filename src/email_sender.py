import requests

from .config import BREVO_API_KEY, SENDER_EMAIL, SENDER_NAME


def send_email(subject: str, html: str, recipients: list[dict]) -> dict:
    if not BREVO_API_KEY:
        raise ValueError("BREVO_API_KEY is missing")

    if not SENDER_EMAIL:
        raise ValueError("SENDER_EMAIL is missing")

    if not recipients:
        raise ValueError("No recipients configured")

    payload = {
        "sender": {
            "email": SENDER_EMAIL,
            "name": SENDER_NAME,
        },
        "to": [
            {"email": r["email"], "name": r["name"]}
            for r in recipients
        ],
        "subject": subject,
        "htmlContent": html,
    }

    response = requests.post(
        "https://api.brevo.com/v3/smtp/email",
        headers={
            "accept": "application/json",
            "api-key": BREVO_API_KEY,
            "content-type": "application/json",
        },
        json=payload,
        timeout=30,
    )

    if response.status_code not in (200, 201, 202):
        raise RuntimeError(
            f"Brevo email send failed: {response.status_code} {response.text}"
        )

    return response.json()
