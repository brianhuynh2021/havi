from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.enums import WorkspaceRole
from domain.models.user import User
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

    async def get(self, *, workspace_id: UUID, user_id: UUID) -> WorkspaceMember | None:
        result = await self._session.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def add(
        self, *, workspace_id: UUID, user_id: UUID, role: WorkspaceRole
    ) -> WorkspaceMember:
        member = WorkspaceMember(workspace_id=workspace_id, user_id=user_id, role=role)
        self._session.add(member)
        await self._session.flush()
        return member

    async def remove(self, member: WorkspaceMember) -> None:
        await self._session.delete(member)
        await self._session.flush()

    async def update(
        self, member: WorkspaceMember, *, role: WorkspaceRole
    ) -> WorkspaceMember:
        member.role = role
        await self._session.flush()
        return member

    async def count_owners(self, workspace_id: UUID) -> int:
        result = await self._session.execute(
            select(func.count()).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.role == WorkspaceRole.OWNER,
            )
        )
        return result.scalar_one()

    async def count_members(self, workspace_id: UUID) -> int:
        result = await self._session.execute(
            select(func.count()).where(WorkspaceMember.workspace_id == workspace_id)
        )
        return result.scalar_one()

    async def list_for_user(self, user_id: UUID) -> list[WorkspaceMember]:
        result = await self._session.execute(
            select(WorkspaceMember).where(WorkspaceMember.user_id == user_id)
        )
        return list(result.scalars().all())

    async def remove_all_for_user(self, user_id: UUID) -> None:
        await self._session.execute(
            delete(WorkspaceMember).where(WorkspaceMember.user_id == user_id)
        )
        await self._session.flush()

    async def list_with_user_for_workspace(
        self, workspace_id: UUID
    ) -> list[tuple[WorkspaceMember, User]]:
        result = await self._session.execute(
            select(WorkspaceMember, User)
            .join(User, User.id == WorkspaceMember.user_id)
            .where(WorkspaceMember.workspace_id == workspace_id)
        )
        return [(member, user) for member, user in result.all()]
