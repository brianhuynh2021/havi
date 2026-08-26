"""Repository cho InboxItem — lưu trữ và truy vấn tin nhắn/bình luận khách hàng."""

from datetime import UTC, datetime, timedelta
from math import ceil
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.enums import InboxItemStatus, InboxItemType, Platform
from domain.models.inbox import InboxItem
from domain.models.user import User
from domain.policies import inbox_triage


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

    async def count_in_range(self, *, workspace_id: UUID, start: datetime, end: datetime) -> int:
        """Số tin nhắn, bình luận và đánh giá đi vào hộp thư trong kỳ."""
        result = await self._session.execute(
            select(func.count(InboxItem.id)).where(
                InboxItem.workspace_id == workspace_id,
                InboxItem.created_at >= start,
                InboxItem.created_at < end,
            )
        )
        return result.scalar_one()

    async def count_by_status_in_range(
        self,
        *,
        workspace_id: UUID,
        status: InboxItemStatus,
        start: datetime,
        end: datetime,
    ) -> int:
        """Đếm item theo trạng thái để báo cáo việc đội ngũ đã xử lý."""
        result = await self._session.execute(
            select(func.count(InboxItem.id)).where(
                InboxItem.workspace_id == workspace_id,
                InboxItem.status == status,
                InboxItem.created_at >= start,
                InboxItem.created_at < end,
            )
        )
        return result.scalar_one()

    async def count_by_statuses(
        self,
        *,
        workspace_id: UUID,
        statuses: list[InboxItemStatus],
    ) -> int:
        result = await self._session.execute(
            select(func.count(InboxItem.id)).where(
                InboxItem.workspace_id == workspace_id,
                InboxItem.status.in_(statuses),
            )
        )
        return result.scalar_one()

    async def get_by_external_id(
        self, *, workspace_id: UUID, platform: Platform, external_message_id: str
    ) -> InboxItem | None:
        """Item đã tạo từ đúng sự kiện này chưa — dùng cho webhook gửi lại."""
        result = await self._session.execute(
            select(InboxItem).where(
                InboxItem.workspace_id == workspace_id,
                InboxItem.platform == platform,
                InboxItem.external_message_id == external_message_id,
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
        type: InboxItemType = InboxItemType.MESSAGE,
        ai_suggested_reply: str | None = None,
        status: InboxItemStatus = InboxItemStatus.NEW,
        external_message_id: str | None = None,
        recipient_id: str | None = None,
    ) -> InboxItem:
        item = InboxItem(
            workspace_id=workspace_id,
            platform=platform,
            content=content,
            author_name=author_name,
            type=type,
            ai_suggested_reply=ai_suggested_reply,
            status=status,
            external_message_id=external_message_id,
            recipient_id=recipient_id,
            # Phân loại ngay lúc nhận, ở repository chứ không ở service: webhook,
            # simulator và seed đều đi qua đây, nên đặt ở service là có đường vào
            # tạo ra tin không có category rồi tin đó chìm dưới hàng đợi.
            category=inbox_triage.classify(content).value,
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

    #: Trạng thái nghĩa là "còn việc phải làm với tin này".
    OPEN_STATUSES = (InboxItemStatus.NEW, InboxItemStatus.DRAFTED, InboxItemStatus.FAILED)

    async def list_open(
        self, *, workspace_id: UUID, limit: int = 200
    ) -> list[tuple[InboxItem, str | None]]:
        """Tin còn phải xử lý, kèm tên người đang nhận việc.

        Join sang `users` ngay trong truy vấn thay vì để router đi hỏi tên từng
        người: hàng đợi có bao nhiêu người nhận việc thì bấy nhiêu lượt hỏi, và
        đây là truy vấn chạy mỗi lần mở màn làm việc.

        `outerjoin` vì phần lớn tin **chưa có ai nhận** — inner join sẽ lặng lẽ
        làm biến mất đúng những việc cần người làm nhất.
        """
        rows = await self._session.execute(
            select(InboxItem, User.name)
            .outerjoin(User, User.id == InboxItem.assigned_to_user_id)
            .where(
                InboxItem.workspace_id == workspace_id,
                InboxItem.status.in_(self.OPEN_STATUSES),
            )
            .order_by(InboxItem.created_at.asc())
            .limit(limit)
        )
        return [(item, name) for item, name in rows.all()]

    async def response_metrics(
        self, *, workspace_id: UUID, start: datetime, end: datetime, now: datetime
    ) -> dict:
        """Chỉ số **tổn thất tránh được**, không phải đếm hoạt động.

        Bốn con số dưới đây là thứ chứng minh giá trị sản phẩm cho người trả tiền
        — "tuần trước bạn sót 12 tin hỏi giá" kiểm chứng được, còn "doanh thu sẽ
        tăng" thì không.

        `waiting_over_*` tính theo **`now`**, không theo cửa sổ báo cáo: "đang có
        3 tin chờ quá 4 giờ" là một sự thật của hiện tại. Một tin chờ từ tháng
        trước và vẫn chưa ai trả lời thì nó vẫn đang là việc chưa làm, dù nó rơi
        ngoài kỳ báo cáo.
        """
        replied = await self._session.execute(
            select(InboxItem.created_at, InboxItem.replied_at).where(
                InboxItem.workspace_id == workspace_id,
                InboxItem.replied_at.is_not(None),
                InboxItem.replied_at >= start,
                InboxItem.replied_at < end,
            )
        )
        waits = sorted(
            (replied_at - created_at).total_seconds()
            for created_at, replied_at in replied.all()
        )

        open_rows = await self._session.execute(
            select(InboxItem.created_at, InboxItem.category).where(
                InboxItem.workspace_id == workspace_id,
                InboxItem.status.in_(self.OPEN_STATUSES),
            )
        )
        open_items = open_rows.all()

        # Bỏ sót = thuộc nhóm tốn tiền, và **chưa bao giờ** được trả lời sau hơn
        # một ngày. Không tính tin mới đến sáng nay: chậm chưa phải là sót.
        missed_cutoff = now - timedelta(days=1)
        missed_costly = sum(
            1
            for created_at, category in open_items
            if created_at < missed_cutoff and inbox_triage.is_costly(category)
        )

        return {
            "replied_count": len(waits),
            "avg_response_seconds": round(sum(waits) / len(waits)) if waits else 0,
            "p95_response_seconds": (
                round(waits[ceil(len(waits) * 0.95) - 1]) if waits else 0
            ),
            "waiting_over_1h": sum(
                1 for created_at, _ in open_items if created_at < now - timedelta(hours=1)
            ),
            "waiting_over_4h": sum(
                1 for created_at, _ in open_items if created_at < now - timedelta(hours=4)
            ),
            "missed_costly": missed_costly,
        }

    async def update_status(
        self,
        item: InboxItem,
        *,
        status: InboxItemStatus,
        reply_text: str | None = None,
        now: datetime | None = None,
    ) -> InboxItem:
        item.status = status
        if reply_text is not None:
            item.ai_suggested_reply = reply_text

        # `replied_at` ghi **một lần**, ở lần gửi thành công đầu tiên. Gửi lại
        # hay sửa câu trả lời sau đó không được dịch mốc này: thời gian phản hồi
        # là "khách chờ bao lâu mới có người trả lời", và nó không giảm đi vì
        # nhân viên quay lại sửa câu chữ.
        if status is InboxItemStatus.SENT and item.replied_at is None:
            item.replied_at = now or datetime.now(UTC)

        await self._session.flush()
        return item

    async def assign(
        self,
        item: InboxItem,
        *,
        user_id: UUID | None,
        now: datetime | None = None,
    ) -> InboxItem:
        """Nhận việc, hoặc trả việc lại hàng đợi khi `user_id` là None.

        Vuông góc với `status`: nhận việc không đổi trạng thái phản hồi. Một việc
        có người nhận vẫn đang chờ được trả lời.
        """
        item.assigned_to_user_id = user_id
        item.assigned_at = (now or datetime.now(UTC)) if user_id is not None else None
        await self._session.flush()
        return item
