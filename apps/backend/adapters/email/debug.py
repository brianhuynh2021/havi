"""Local-only email sender used in development and tests."""

from domain.ports.email import EmailSender


class DebugEmailSender(EmailSender):
    async def send_password_reset_code(
        self, *, email: str, code: str, expires_in_seconds: int
    ) -> None:
        return None
