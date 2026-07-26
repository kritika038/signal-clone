import logging
from email.message import EmailMessage
import aiosmtplib

from app.core.config import settings

logger = logging.getLogger(__name__)

class EmailService:
    async def send_otp_email(self, to_email: str, otp: str) -> None:
        """
        Sends an email containing the 6-digit OTP.
        If SMTP is not configured, logs the OTP to the console instead.
        """
        if not settings.SMTP_HOST:
            logger.warning(
                f"\n{'='*50}\n"
                f"SMTP_HOST is not configured. Email to {to_email} skipped.\n"
                f"MOCK EMAIL DELIVERY:\n"
                f"To: {to_email}\n"
                f"OTP Code: {otp}\n"
                f"{'='*50}"
            )
            return

        message = EmailMessage()
        message["From"] = settings.SMTP_FROM_EMAIL
        message["To"] = to_email
        message["Subject"] = "Your Signal Clone Verification Code"

        content = (
            f"Hello,\n\n"
            f"Your verification code is: {otp}\n\n"
            f"This code will expire in 5 minutes.\n\n"
            f"If you did not request this code, please ignore this email."
        )
        message.set_content(content)

        try:
            await aiosmtplib.send(
                message,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USER,
                password=settings.SMTP_PASSWORD,
                use_tls=(settings.SMTP_PORT in (465,)),
                start_tls=(settings.SMTP_PORT == 587),
            )
            logger.info(f"Successfully sent OTP email to {to_email}")
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            raise ValueError("Failed to send OTP email. Please try again.")

email_service = EmailService()
