from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.models.user import OtpChallenge


class OtpRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_latest_for_phone(self, phone: str) -> OtpChallenge | None:
        result = await self._session.execute(
            select(OtpChallenge)
            .where(OtpChallenge.phone == phone)
            .order_by(OtpChallenge.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_active_for_phone(self, phone: str) -> OtpChallenge | None:
        """Challenge còn hạn, chưa dùng — dùng để verify."""
        now = datetime.now(UTC)
        result = await self._session.execute(
            select(OtpChallenge)
            .where(
                OtpChallenge.phone == phone,
                OtpChallenge.consumed_at.is_(None),
                OtpChallenge.expires_at > now,
            )
            .order_by(OtpChallenge.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def create(self, *, phone: str, code_hash: str, expires_at: datetime) -> OtpChallenge:
        challenge = OtpChallenge(phone=phone, code_hash=code_hash, expires_at=expires_at)
        self._session.add(challenge)
        await self._session.flush()
        return challenge

    async def increment_attempt(self, challenge: OtpChallenge) -> None:
        challenge.attempt_count += 1
        await self._session.flush()

    async def consume(self, challenge: OtpChallenge) -> None:
        challenge.consumed_at = datetime.now(UTC)
        await self._session.flush()
