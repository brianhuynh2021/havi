"""Repository cho InboxItem — lưu trữ và truy vấn tin nhắn/bình luận khách hàng."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.enums import InboxItemStatus, Platform
from domain.models.inbox import InboxItem


class InboxRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, *, workspace_id: UUID, item_id: UUID) -> InboxItem | None:
        result = await self._session.execute(
            select(InboxItem).where(
                InboxItem.id == item_id,
                InboxItem.workspace_id == workspace_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        workspace_id: UUID,
        platform: Platform,
        content: str,
        author_name: str,
        type: str = "message",
        ai_suggested_reply: str | None = None,
        status: InboxItemStatus = InboxItemStatus.NEW,
    ) -> InboxItem:
        item = InboxItem(
            workspace_id=workspace_id,
            platform=platform,
            content=content,
            author_name=author_name,
            ai_suggested_reply=ai_suggested_reply,
            status=status,
        )
        self._session.add(item)
        await self._session.flush()
        return item

    async def list_items(
        self,
        *,
        workspace_id: UUID,
        status: InboxItemStatus | None = None,
        platform: Platform | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[InboxItem], int]:
        filters = [InboxItem.workspace_id == workspace_id]
        if status is not None:
            filters.append(InboxItem.status == status)
        if platform is not None:
            filters.append(InboxItem.platform == platform)

        total = await self._session.execute(select(func.count()).where(*filters))
        rows = await self._session.execute(
            select(InboxItem)
            .where(*filters)
            .order_by(InboxItem.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(rows.scalars().all()), total.scalar_one()

    async def update_status(
        self,
        item: InboxItem,
        *,
        status: InboxItemStatus,
        reply_text: str | None = None,
    ) -> InboxItem:
        item.status = status
        if reply_text is not None:
            item.ai_suggested_reply = reply_text
        await self._session.flush()
        return item
