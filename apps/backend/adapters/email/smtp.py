"""SMTP email sender for password-reset messages."""

import asyncio
import smtplib
from email.message import EmailMessage

from core.config import Settings
from domain.ports.email import EmailSender


class SmtpEmailSender(EmailSender):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def send_password_reset_code(
        self, *, email: str, code: str, expires_in_seconds: int
    ) -> None:
        await asyncio.to_thread(
            self._send_password_reset_code,
            email,
            code,
            expires_in_seconds,
        )

    def _send_password_reset_code(self, email: str, code: str, expires_in_seconds: int) -> None:
        message = EmailMessage()
        message["From"] = self._settings.email_from
        message["To"] = email
        message["Subject"] = "Ma dat lai mat khau Havi"
        ttl_minutes = max(1, expires_in_seconds // 60)
        message.set_content(
            "\n".join(
                [
                    "Ma dat lai mat khau Havi cua ban la:",
                    "",
                    code,
                    "",
                    f"Ma nay het han sau {ttl_minutes} phut.",
                    "Neu ban khong yeu cau dat lai mat khau, hay bo qua email nay.",
                ]
            )
        )

        if self._settings.smtp_use_tls:
            with smtplib.SMTP_SSL(
                self._settings.smtp_host,
                self._settings.smtp_port,
                timeout=self._settings.smtp_timeout_seconds,
            ) as smtp:
                self._login_and_send(smtp, message)
            return

        with smtplib.SMTP(
            self._settings.smtp_host,
            self._settings.smtp_port,
            timeout=self._settings.smtp_timeout_seconds,
        ) as smtp:
            self._login_and_send(smtp, message)

    def _login_and_send(self, smtp: smtplib.SMTP, message: EmailMessage) -> None:
        if self._settings.smtp_username:
            smtp.login(self._settings.smtp_username, self._settings.smtp_password)
        smtp.send_message(message)
