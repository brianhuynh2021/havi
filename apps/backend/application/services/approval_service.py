"""Use case cho sửa / duyệt / từ chối / đổi lịch một content item.

Đây là chỗ cưỡng chế nguyên tắc #1 của Havi (ROADMAP §1): không bài nào lên mạng
khi chủ chưa duyệt. State machine nằm ở `core/content_state.py` và được gọi ở
tầng này — không ở router, không ở UI — nên mọi đường vào API đều đi qua cùng một
luật. Frontend duyệt optimistic được, nhưng backend mới là nơi quyết định.

Tách khỏi `ContentService` (tạo job, đọc job) vì hai use case khác nhau về rủi
ro: tạo job chỉ tốn tiền LLM, còn duyệt là hành động không thu hồi được sau khi
đã đăng, nên cần row lock + audit event.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from adapters.persistence.content_repository import ContentRepository
from adapters.persistence.event_log_repository import EventLogRepository
from core.content_state import (
    RESCHEDULABLE_STATUSES,
    InvalidTransitionError,
    assert_transition,
)
from core.enums import ContentStatus
from core.events import EventLogEntry
from domain.models.content import ContentItem, ContentItemVersion
from domain.policies.scheduling import next_golden_hour


class ContentItemNotFound(Exception):
    pass


class NotReschedulable(Exception):
    """Đã đăng rồi thì không đổi được giờ đăng — kéo-thả trên Lịch đăng phải trả 409."""

    def __init__(self, status: ContentStatus) -> None:
        super().__init__(f"Không thể đổi giờ đăng khi bài đang ở trạng thái {status}")
        self.status = status


@dataclass
class BulkApproveOutcome:
    approved: list[UUID]
    #: (content_item_id, lý do) — một bài hỏng không được làm fail cả lô.
    failures: list[tuple[UUID, str]]


class ApprovalService:
    def __init__(
        self, *, content: ContentRepository, events: EventLogRepository
    ) -> None:
        self._content = content
        self._events = events

    async def update_item(
        self,
        *,
        workspace_id: UUID,
        item_id: UUID,
        user_id: UUID,
        text: str | None,
        media_note: str | None,
        scheduled_at: datetime | None,
    ) -> ContentItem:
        item = await self._require_item(workspace_id=workspace_id, item_id=item_id)
        if item.status in {ContentStatus.PUBLISHED, ContentStatus.PUBLISHING}:
            # Sửa text của bài đã/đang lên mạng thì bản trên Facebook và bản trong
            # DB lệch nhau — audit trail nói dối.
            raise NotReschedulable(item.status)
        return await self._content.update_item(
            item,
            text=text,
            media_note=media_note,
            scheduled_at=scheduled_at,
            edited_by=user_id,
        )

    async def list_versions(
        self, *, workspace_id: UUID, item_id: UUID
    ) -> list[ContentItemVersion]:
        await self._require_item(workspace_id=workspace_id, item_id=item_id)
        return await self._content.list_versions(item_id)

    async def approve(
        self,
        *,
        workspace_id: UUID,
        item_id: UUID,
        user_id: UUID,
        scheduled_at: datetime | None,
    ) -> ContentItem:
        """pending_approval → approved → scheduled trong cùng một transaction.

        Đi qua `approved` chứ không nhảy thẳng sang `scheduled` để state machine
        vẫn là nguồn sự thật duy nhất; `approved_by`/`approved_at` được ghi ở bước
        đầu nên dù có lỗi sau đó vẫn biết ai đã duyệt.
        """
        item = await self._require_item(
            workspace_id=workspace_id, item_id=item_id, for_update=True
        )
        assert_transition(item.status, ContentStatus.APPROVED)
        await self._content.set_item_status(
            item, status=ContentStatus.APPROVED, approved_by=user_id
        )
        assert_transition(item.status, ContentStatus.SCHEDULED)
        await self._content.set_item_status(
            item,
            status=ContentStatus.SCHEDULED,
            scheduled_at=scheduled_at or item.scheduled_at or next_golden_hour(),
        )
        await self._audit(
            workspace_id=workspace_id,
            item=item,
            action="content.approve",
            summary=f"user={user_id} scheduled_at={item.scheduled_at}",
        )
        return item

    async def reject(
        self, *, workspace_id: UUID, item_id: UUID, user_id: UUID
    ) -> ContentItem:
        """pending_approval → draft. Giữ lại bài để chủ sửa, không xoá."""
        item = await self._require_item(
            workspace_id=workspace_id, item_id=item_id, for_update=True
        )
        assert_transition(item.status, ContentStatus.DRAFT)
        await self._content.set_item_status(item, status=ContentStatus.DRAFT)
        await self._audit(
            workspace_id=workspace_id,
            item=item,
            action="content.reject",
            summary=f"user={user_id}",
        )
        return item

    async def approve_many(
        self, *, workspace_id: UUID, item_ids: list[UUID], user_id: UUID
    ) -> BulkApproveOutcome:
        """Nút "Duyệt & đăng hết".

        Bài nào không duyệt được thì báo lý do riêng cho bài đó — một item đã bị
        duyệt ở tab khác không được làm hỏng cả lô 5 bài.
        """
        approved: list[UUID] = []
        failures: list[tuple[UUID, str]] = []
        for item_id in item_ids:
            try:
                await self.approve(
                    workspace_id=workspace_id,
                    item_id=item_id,
                    user_id=user_id,
                    scheduled_at=None,
                )
            except ContentItemNotFound:
                failures.append((item_id, "Không tìm thấy bài trong workspace này"))
            except InvalidTransitionError as exc:
                failures.append((item_id, str(exc)))
            else:
                approved.append(item_id)
        return BulkApproveOutcome(approved=approved, failures=failures)

    async def reschedule(
        self,
        *,
        workspace_id: UUID,
        item_id: UUID,
        user_id: UUID,
        scheduled_at: datetime,
    ) -> ContentItem:
        item = await self._require_item(
            workspace_id=workspace_id, item_id=item_id, for_update=True
        )
        if item.status not in RESCHEDULABLE_STATUSES:
            raise NotReschedulable(item.status)
        await self._content.set_item_status(
            item, status=item.status, scheduled_at=scheduled_at
        )
        await self._audit(
            workspace_id=workspace_id,
            item=item,
            action="content.reschedule",
            summary=f"user={user_id} scheduled_at={scheduled_at}",
        )
        return item

    async def calendar(
        self, *, workspace_id: UUID, start: datetime, end: datetime
    ) -> list[ContentItem]:
        return await self._content.list_items_in_range(
            workspace_id=workspace_id, start=start, end=end
        )

    async def _require_item(
        self, *, workspace_id: UUID, item_id: UUID, for_update: bool = False
    ) -> ContentItem:
        if for_update:
            item = await self._content.get_item_for_update(
                workspace_id=workspace_id, item_id=item_id
            )
        else:
            item = await self._content.get_item(
                workspace_id=workspace_id, item_id=item_id
            )
        if item is None:
            raise ContentItemNotFound()
        return item

    async def _audit(
        self, *, workspace_id: UUID, item: ContentItem, action: str, summary: str
    ) -> None:
        """Mọi hành động duyệt đều để lại dấu vết — Definition of Done §7."""
        await self._events.record(
            EventLogEntry(
                workspace_id=workspace_id,
                job_id=item.job_id,
                job_kind=action,
                input_summary=f"content_item={item.id} {summary}",
                output_summary=f"status={item.status}",
                created_at=datetime.now(UTC),
            )
        )
