from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.enums import Industry, PublishMode
from domain.models.workspace import Workspace, WorkspaceMember


class WorkspaceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, workspace_id: UUID) -> Workspace | None:
        result = await self._session.execute(
            select(Workspace).where(Workspace.id == workspace_id)
        )
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: UUID) -> list[Workspace]:
        result = await self._session.execute(
            select(Workspace)
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .where(WorkspaceMember.user_id == user_id)
            .order_by(Workspace.created_at)
        )
        return list(result.scalars().all())

    async def create(self, *, name: str, industry: Industry, owner_user_id: UUID) -> Workspace:
        workspace = Workspace(name=name, industry=industry, owner_user_id=owner_user_id)
        self._session.add(workspace)
        await self._session.flush()
        return workspace

    async def update(
        self,
        workspace: Workspace,
        *,
        name: str | None = None,
        industry: Industry | None = None,
        publish_mode: PublishMode | None = None,
    ) -> Workspace:
        if name is not None:
            workspace.name = name
        if industry is not None:
            workspace.industry = industry
        if publish_mode is not None:
            workspace.publish_mode = publish_mode
        await self._session.flush()
        return workspace
