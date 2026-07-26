import logging
import httpx
from email.message import EmailMessage
import aiosmtplib

from app.core.config import settings

logger = logging.getLogger(__name__)

class EmailProvider:
    async def send_email(self, to_email: str, subject: str, content: str) -> None:
        raise NotImplementedError

class SMTPEmailProvider(EmailProvider):
    async def send_email(self, to_email: str, subject: str, content: str) -> None:
        if not settings.SMTP_HOST:
            raise ValueError("Unable to send verification email. Please try again later.")

        message = EmailMessage()
        message["From"] = settings.SMTP_FROM_EMAIL
        message["To"] = to_email
        message["Subject"] = subject
        message.set_content(content)

        try:
            response = await aiosmtplib.send(
                message,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USER,
                password=settings.SMTP_PASSWORD,
                use_tls=(settings.SMTP_PORT in (465,)),
                start_tls=(settings.SMTP_PORT == 587),
            )
            logger.info(f"[SMTP] Successfully sent email to {to_email}. Response: {response}")
        except Exception as e:
            logger.exception(f"[SMTP] Failed to send email to {to_email}.")
            raise ValueError(f"SMTP Error: {type(e).__name__} - {str(e)}")

class ResendEmailProvider(EmailProvider):
    async def send_email(self, to_email: str, subject: str, content: str) -> None:
        if not settings.RESEND_API_KEY:
            raise ValueError("Unable to send verification email. Please try again later.")
            
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    "https://api.resend.com/emails",
                    headers={
                        "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "from": settings.SMTP_FROM_EMAIL,
                        "to": [to_email],
                        "subject": subject,
                        "text": content
                    }
                )
                response.raise_for_status()
                logger.info(f"[Resend] Successfully sent email to {to_email}.")
            except Exception as e:
                logger.exception(f"[Resend] Failed to send email to {to_email}.")
                raise ValueError(f"Resend Error: {type(e).__name__} - {str(e)}")

class MailtrapEmailProvider(EmailProvider):
    async def send_email(self, to_email: str, subject: str, content: str) -> None:
        if not settings.MAILTRAP_API_KEY:
            raise ValueError("Unable to send verification email. Please try again later.")
            
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    "https://send.api.mailtrap.io/api/send",
                    headers={
                        "Authorization": f"Bearer {settings.MAILTRAP_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "from": {"email": settings.SMTP_FROM_EMAIL, "name": "Signal Clone"},
                        "to": [{"email": to_email}],
                        "subject": subject,
                        "text": content
                    }
                )
                response.raise_for_status()
                logger.info(f"[Mailtrap] Successfully sent email to {to_email}.")
            except Exception as e:
                logger.exception(f"[Mailtrap] Failed to send email to {to_email}.")
                raise ValueError(f"Mailtrap Error: {type(e).__name__} - {str(e)}")


class EmailService:
    def __init__(self):
        provider = settings.EMAIL_PROVIDER.lower()
        if provider == "resend":
            self.provider = ResendEmailProvider()
        elif provider == "mailtrap":
            self.provider = MailtrapEmailProvider()
        else:
            self.provider = SMTPEmailProvider()

    async def send_otp_email(self, to_email: str, otp: str) -> None:
        """
        Sends an email containing the 6-digit OTP using the configured provider.
        """
        subject = "Your Signal Clone Verification Code"
        content = (
            f"Hello,\n\n"
            f"Your verification code is: {otp}\n\n"
            f"This code will expire in 5 minutes.\n\n"
            f"If you did not request this code, please ignore this email."
        )
        
        await self.provider.send_email(to_email, subject, content)

email_service = EmailService()
