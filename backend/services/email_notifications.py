import smtplib
from email.message import EmailMessage

from config import settings


class EmailNotificationService:
    def is_configured(self) -> bool:
        return bool(settings.GMAIL_SMTP_USER and settings.GMAIL_SMTP_APP_PASSWORD)

    def send_text_email(self, to_email: str, subject: str, body: str) -> None:
        if not self.is_configured():
            raise RuntimeError("Email service not configured (GMAIL_SMTP_USER / GMAIL_SMTP_APP_PASSWORD).")

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = f"{settings.GMAIL_SMTP_FROM_NAME} <{settings.GMAIL_SMTP_USER}>"
        msg["To"] = to_email
        msg.set_content(body)

        with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(settings.GMAIL_SMTP_USER, settings.GMAIL_SMTP_APP_PASSWORD)
            smtp.send_message(msg)

    def send_text_email_safe(self, to_email: str, subject: str, body: str) -> None:
        try:
            self.send_text_email(to_email=to_email, subject=subject, body=body)
            print(f"✓ Email sent to={to_email} subject={subject!r}")
        except Exception as e:
            print(f"✗ Email failed to={to_email} subject={subject!r}: {e}")


email_notifications = EmailNotificationService()
