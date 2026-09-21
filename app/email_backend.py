import logging
import smtplib
from email.mime.text import MIMEText

from .config import get_settings

log = logging.getLogger("cas.email")


def send_email(to: str, subject: str, body: str) -> None:
    settings = get_settings()
    if settings.email_backend == "smtp":
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = settings.email_from
        msg["To"] = to
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
            server.starttls()
            if settings.smtp_user:
                server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
        return
    log.info("EMAIL to=%s subject=%s body=%s", to, subject, body)
