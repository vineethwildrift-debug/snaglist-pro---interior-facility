import smtplib
import logging
from email.message import EmailMessage
from typing import Optional

from snaglist_pro.config import settings


def send_email(
    subject: str,
    body: str,
    to_email: Optional[str] = None,
    from_email: Optional[str] = None,
) -> bool:
    if not settings.smtp_host or not settings.smtp_user:
        logging.warning("SMTP not configured — notification skipped")
        return False

    to = to_email or settings.notify_email
    if not to:
        logging.warning("No recipient email configured — notification skipped")
        return False

    try:
        msg = EmailMessage()
        msg.set_content(body)
        msg["Subject"] = subject
        msg["From"] = from_email or settings.smtp_user
        msg["To"] = to

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.starttls()
            server.login(settings.smtp_user, settings.smtp_pass)
            server.send_message(msg)

        logging.info("Email sent to %s: %s", to, subject)
        return True
    except Exception as e:
        logging.error("Failed to send email: %s", e)
        return False


def notify_high_priority_snag(snag: dict, project_name: str) -> bool:
    subject = f"[HIGH PRIORITY] Snag #{snag.get('index', '?')} - {project_name}"
    body = (
        f"Project: {project_name}\n"
        f"Description: {snag.get('description', 'N/A')}\n"
        f"Category: {snag.get('category', 'N/A')}\n"
        f"Area: {snag.get('area', 'N/A')}\n"
        f"Vendor: {snag.get('vendor', 'N/A')}\n"
        f"Reported by: {snag.get('sender', 'N/A')}\n"
        f"Date: {snag.get('date_reported', 'N/A')}\n"
    )
    return send_email(subject, body)


def notify_status_change(snag: dict, from_status: str, to_status: str, changed_by: str) -> bool:
    subject = f"Snag #{snag.get('index', '?')} status: {from_status} → {to_status}"
    body = (
        f"Snag: {snag.get('description', 'N/A')[:100]}\n"
        f"Status changed from {from_status} to {to_status}\n"
        f"Changed by: {changed_by}\n"
    )
    return send_email(subject, body)
