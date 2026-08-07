from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.models.workspace import WorkspaceMember


class WorkspaceMemberRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def is_member(self, *, workspace_id: UUID, user_id: UUID) -> bool:
        result = await self._session.execute(
            select(WorkspaceMember.workspace_id).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id,
            )
        )
        return result.scalar_one_or_none() is not None
