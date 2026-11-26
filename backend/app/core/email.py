"""
AURA AI Email Service — SMTP email sending for verification codes.

Sends verification codes to new users on signup. Configure SMTP_*
environment variables in production (Render). Falls back to logging
the code to console when SMTP credentials are not set (local dev).
"""

import logging
import random
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


def generate_verification_code(length: int = 6) -> str:
    """Generate a numeric verification code."""
    return "".join(random.choice("0123456789") for _ in range(length))


def send_verification_email(
    to_email: str,
    code: str,
    code_type: str = "email_verification",
) -> bool:
    """
    Send a verification code to the user's email.

    Returns True if sent successfully (or logged in dev mode without SMTP).
    Returns False if SMTP is configured but sending fails.
    """
    smtp_user = settings.SMTP_USER
    smtp_password = settings.SMTP_PASSWORD

    if not smtp_user or not smtp_password:
        # Development mode: log the code instead of sending
        logger.info(
            "============================================================\n"
            f"  EMAIL VERIFICATION CODE for {to_email}\n"
            f"  Type: {code_type}\n"
            f"  Code: {code}\n"
            "  (SMTP not configured — code shown in logs only)\n"
            "============================================================"
        )
        return True

    subject_map = {
        "email_verification": "Your AURA AI verification code",
        "password_reset": "Your AURA AI password reset code",
    }
    subject = subject_map.get(code_type, "Your AURA AI verification code")
    current_year = datetime.now().year

    html_body = f"""\
<!DOCTYPE html>
<html>
<body style="font-family: system-ui, -apple-system, sans-serif; background:#0b0b14; color:#f1f5f9; padding:24px;">
  <div style="max-width:600px; margin:0 auto; background:#111827; border-radius:16px; padding:32px; border:1px solid #1f2937;">
    <h2 style="color:#34d399; margin-top:0;">AURA AI</h2>
    <p style="font-size:16px; color:#cbd5e1;">Your verification code is:</p>
    <div style="font-size:32px; font-weight:bold; letter-spacing:8px; color:#ffffff; background:#064e3b; display:inline-block; padding:12px 24px; border-radius:8px; margin:16px 0;">
      {code}
    </div>
    <p style="font-size:14px; color:#9ca3af;">This code expires in 10 minutes.</p>
    <p style="font-size:14px; color:#9ca3af;">If you didn't request this, you can safely ignore this email.</p>
    <hr style="border:none; border-top:1px solid #1f2937; margin:24px 0;">
    <p style="font-size:12px; color:#6b7280;">© {current_year} AURA AI — auraainet.xyz</p>
  </div>
</body>
</html>
"""

    text_body = f"""\
AURA AI Verification Code

Your verification code is: {code}

This code expires in 10 minutes.
If you didn't request this, you can safely ignore this email.

© {current_year} AURA AI — auraainet.xyz
"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
    msg["To"] = to_email

    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=30) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
        logger.info(f"Verification email sent to {to_email} (type={code_type})")
        return True
    except Exception as e:
        logger.error(f"Failed to send verification email to {to_email}: {e}")
        return False
