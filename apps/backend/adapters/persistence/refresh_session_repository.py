from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.models.user import RefreshSession


class RefreshSessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_active_by_token_hash(self, token_hash: str) -> RefreshSession | None:
        now = datetime.now(UTC)
        result = await self._session.execute(
            select(RefreshSession).where(
                RefreshSession.token_hash == token_hash,
                RefreshSession.revoked_at.is_(None),
                RefreshSession.expires_at > now,
            )
        )
        return result.scalar_one_or_none()

    async def create(
        self, *, user_id: UUID, token_hash: str, expires_at: datetime
    ) -> RefreshSession:
        session_row = RefreshSession(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
        self._session.add(session_row)
        await self._session.flush()
        return session_row

    async def revoke(self, refresh_session: RefreshSession) -> None:
        refresh_session.revoked_at = datetime.now(UTC)
        await self._session.flush()
