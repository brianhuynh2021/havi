from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.enums import Industry, PublishMode
from domain.models.audit import EventLog
from domain.models.connection import PlatformConnection
from domain.models.content import ContentItem, ContentItemVersion, ContentJob
from domain.models.media import MediaAsset
from domain.models.publish import PublishJob
from domain.models.user import User
from domain.models.workspace import BrandProfile, Workspace, WorkspaceMember
from domain.policies.subscription import trial_end_for


class WorkspaceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, workspace_id: UUID) -> Workspace | None:
        result = await self._session.execute(select(Workspace).where(Workspace.id == workspace_id))
        return result.scalar_one_or_none()

    async def get(self, workspace_id: UUID) -> Workspace | None:
        return await self.get_by_id(workspace_id)

    async def list_all(self) -> list[Workspace]:
        result = await self._session.execute(select(Workspace).order_by(Workspace.created_at))
        return list(result.scalars().all())

    async def list_for_user(self, user_id: UUID) -> list[Workspace]:
        result = await self._session.execute(
            select(Workspace)
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .where(WorkspaceMember.user_id == user_id)
            .order_by(Workspace.created_at)
        )
        return list(result.scalars().all())

    async def create(self, *, name: str, industry: Industry, owner_user_id: UUID) -> Workspace:
        # Đồng hồ dùng thử chạy từ lúc tạo workspace, và mốc được ghi ngay ở đây.
        # Tính lười ("created_at + 14 ngày") thì mọi chỗ đọc phải nhớ cùng một
        # công thức, và đổi độ dài dùng thử sau này sẽ lặng lẽ gia hạn cho cả
        # những tiệm đã hết hạn từ lâu.
        now = datetime.now(UTC)
        workspace = Workspace(
            name=name,
            industry=industry,
            owner_user_id=owner_user_id,
            trial_ends_at=trial_end_for(now),
        )
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

    async def delete_workspace_cascade(self, workspace_id: UUID) -> None:
        """Cascade deletes all data associated with workspace_id and anonymizes audit logs."""
        await self._session.execute(
            delete(BrandProfile).where(BrandProfile.workspace_id == workspace_id)
        )
        content_item_ids_stmt = select(ContentItem.id).where(
            ContentItem.workspace_id == workspace_id
        )
        await self._session.execute(
            delete(ContentItemVersion).where(
                ContentItemVersion.content_item_id.in_(content_item_ids_stmt)
            )
        )
        await self._session.execute(
            delete(ContentItem).where(ContentItem.workspace_id == workspace_id)
        )
        await self._session.execute(
            delete(ContentJob).where(ContentJob.workspace_id == workspace_id)
        )
        await self._session.execute(
            delete(PublishJob).where(PublishJob.workspace_id == workspace_id)
        )
        await self._session.execute(
            delete(PlatformConnection).where(PlatformConnection.workspace_id == workspace_id)
        )
        await self._session.execute(
            delete(MediaAsset).where(MediaAsset.workspace_id == workspace_id)
        )
        await self._session.execute(
            delete(WorkspaceMember).where(WorkspaceMember.workspace_id == workspace_id)
        )
        await self._session.execute(
            update(EventLog)
            .where(EventLog.workspace_id == workspace_id)
            .values(
                workspace_id=None,
                input_summary="[redacted]",
                output_summary="[redacted]",
            )
        )
        await self._session.execute(
            update(User)
            .where(User.active_workspace_id == workspace_id)
            .values(active_workspace_id=None)
        )
        await self._session.execute(delete(Workspace).where(Workspace.id == workspace_id))
        await self._session.flush()
