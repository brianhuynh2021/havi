"""Email delivery boundary for auth and notifications."""

from typing import Protocol


class EmailSender(Protocol):
    async def send_password_reset_code(
        self, *, email: str, code: str, expires_in_seconds: int
    ) -> None:
        """Send a password reset code without returning or logging the code."""
