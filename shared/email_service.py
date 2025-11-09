"""Email service for sending verification codes."""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional


class EmailService:
    """Service for sending emails."""

    def __init__(
        self,
        smtp_host: str = "localhost",
        smtp_port: int = 587,
        smtp_user: Optional[str] = None,
        smtp_password: Optional[str] = None,
        from_email: str = "noreply@company.com",
        use_tls: bool = True,
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.from_email = from_email
        self.use_tls = use_tls

    def send_verification_code(self, to_email: str, code: str) -> bool:
        """
        Send verification code email.

        Args:
            to_email: Recipient email address
            code: 6-digit verification code

        Returns:
            True if sent successfully, False otherwise
        """
        subject = "Your LLM API Verification Code"

        html_body = f"""
        <html>
          <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
              <h2 style="color: #2563eb;">LLM API - Verification Code</h2>
              <p>Your verification code is:</p>
              <div style="background-color: #f3f4f6; padding: 20px; border-radius: 8px; text-align: center; margin: 20px 0;">
                <h1 style="color: #2563eb; font-size: 36px; letter-spacing: 8px; margin: 0;">{code}</h1>
              </div>
              <p>This code will expire in <strong>5 minutes</strong>.</p>
              <p>If you didn't request this code, please ignore this email.</p>
              <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 30px 0;">
              <p style="font-size: 12px; color: #6b7280;">
                This is an automated message from the Internal LLM API Service.
              </p>
            </div>
          </body>
        </html>
        """

        text_body = f"""
LLM API - Verification Code

Your verification code is: {code}

This code will expire in 5 minutes.

If you didn't request this code, please ignore this email.

---
This is an automated message from the Internal LLM API Service.
        """

        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.from_email
            msg["To"] = to_email

            # Attach both plain text and HTML versions
            part1 = MIMEText(text_body, "plain")
            part2 = MIMEText(html_body, "html")
            msg.attach(part1)
            msg.attach(part2)

            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()

                if self.smtp_user and self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)

                server.send_message(msg)

            print(f"Verification code email sent to {to_email}")
            return True

        except Exception as e:
            print(f"Failed to send email to {to_email}: {str(e)}")
            return False


# For development/testing: print to console instead of sending email
class MockEmailService(EmailService):
    """Mock email service that prints to console instead of sending."""

    def send_verification_code(self, to_email: str, code: str) -> bool:
        """Print verification code to console."""
        print("=" * 60)
        print(f"📧 MOCK EMAIL TO: {to_email}")
        print(f"🔑 VERIFICATION CODE: {code}")
        print("⏰ Expires in 5 minutes")
        print("=" * 60)
        return True


# Get email service based on environment
def get_email_service() -> EmailService:
    """Get email service instance based on environment configuration."""

    # Check if SMTP is configured
    smtp_host = os.getenv("SMTP_HOST", "localhost")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    from_email = os.getenv("SMTP_FROM_EMAIL", "noreply@company.com")
    use_mock = os.getenv("USE_MOCK_EMAIL", "true").lower() == "true"

    if use_mock or not smtp_user:
        print("Using MockEmailService (emails will be printed to console)")
        return MockEmailService()

    return EmailService(
        smtp_host=smtp_host,
        smtp_port=smtp_port,
        smtp_user=smtp_user,
        smtp_password=smtp_password,
        from_email=from_email,
    )
