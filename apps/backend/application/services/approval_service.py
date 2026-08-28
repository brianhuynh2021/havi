"""Use case cho sửa / duyệt / từ chối / đổi lịch một content item.

Đây là chỗ cưỡng chế nguyên tắc #1 của Havi (ROADMAP §1): không bài nào lên mạng
khi chủ chưa duyệt. State machine nằm ở `core/content_state.py` và được gọi ở
tầng này — không ở router, không ở UI — nên mọi đường vào API đều đi qua cùng một
luật. Frontend duyệt optimistic được, nhưng backend mới là nơi quyết định.

Tách khỏi `ContentService` (tạo job, đọc job) vì hai use case khác nhau về rủi
ro: tạo job chỉ tốn tiền LLM, còn duyệt là hành động không thu hồi được sau khi
đã đăng, nên cần row lock + audit event.
"""

import json
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
from domain.policies.scheduling import next_golden_hour, spread_over_golden_hours


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
    def __init__(self, *, content: ContentRepository, events: EventLogRepository) -> None:
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
        media_url: str | None = None,
        scheduled_at: datetime | None,
    ) -> ContentItem:
        item = await self._require_item(workspace_id=workspace_id, item_id=item_id)
        if item.status in {ContentStatus.PUBLISHED, ContentStatus.PUBLISHING}:
            # Sửa text của bài đã/đang lên mạng thì bản trên Facebook và bản trong
            # DB lệch nhau — audit trail nói dối.
            raise NotReschedulable(item.status)
        old_text = item.text
        updated = await self._content.update_item(
            item,
            text=text,
            media_note=media_note,
            media_url=media_url,
            scheduled_at=scheduled_at,
            edited_by=user_id,
        )
        if text is not None and text != old_text:
            diff_len = len(text) - len(old_text)
            diff_sign = f"+{diff_len}" if diff_len >= 0 else str(diff_len)
            await self._audit(
                workspace_id=workspace_id,
                item=updated,
                action="content.edit",
                summary=f"user={user_id} v{updated.version_no} diff_chars={diff_sign}",
            )
        return updated

    async def get_item(self, *, workspace_id: UUID, item_id: UUID) -> ContentItem:
        return await self._require_item(workspace_id=workspace_id, item_id=item_id)

    async def list_versions(self, *, workspace_id: UUID, item_id: UUID) -> list[ContentItemVersion]:
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
        item = await self._require_item(workspace_id=workspace_id, item_id=item_id, for_update=True)
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
        self,
        *,
        workspace_id: UUID,
        item_id: UUID,
        user_id: UUID,
        reason: str | None = None,
    ) -> ContentItem:
        """pending_approval/scheduled → draft. Giữ lại bài để chủ sửa, gỡ khỏi lịch đăng."""
        item = await self._require_item(workspace_id=workspace_id, item_id=item_id, for_update=True)
        assert_transition(item.status, ContentStatus.DRAFT)
        await self._content.set_item_status(
            item,
            status=ContentStatus.DRAFT,
            scheduled_at=None,
            rejection_reason=reason,
        )
        summary = f"user={user_id}"
        if reason:
            # Giới hạn độ dài trong audit summary (120 ký tự) để bảo vệ kích thước log
            # và đóng gói an toàn bằng json.dumps, tránh làm vỡ định dạng log nếu reason
            # chứa ký tự khoảng trắng hoặc dấu '=' (ví dụ text chứa 'user=').
            # Toàn bộ nội dung reason đầy đủ vẫn được lưu toàn vẹn ở content_items.rejection_reason.
            cleaned_reason = reason.strip()
            truncated_reason = json.dumps(cleaned_reason[:120], ensure_ascii=False)
            summary += f" reason={truncated_reason}"
        await self._audit(
            workspace_id=workspace_id,
            item=item,
            action="content.reject",
            summary=summary,
        )
        return item

    async def dismiss(self, *, workspace_id: UUID, item_id: UUID, user_id: UUID) -> ContentItem:
        """pending_approval/draft/scheduled → dismissed. Xoá bỏ vĩnh viễn khỏi hàng chờ."""
        item = await self._require_item(workspace_id=workspace_id, item_id=item_id, for_update=True)
        assert_transition(item.status, ContentStatus.DISMISSED)
        await self._content.set_item_status(item, status=ContentStatus.DISMISSED, scheduled_at=None)
        await self._audit(
            workspace_id=workspace_id,
            item=item,
            action="content.dismiss",
            summary=f"user={user_id}",
        )
        return item

    async def dismiss_many(
        self, *, workspace_id: UUID, item_ids: list[UUID], user_id: UUID
    ) -> list[UUID]:
        """Xoá hàng loạt bản nháp."""
        dismissed: list[UUID] = []
        for item_id in item_ids:
            try:
                await self.dismiss(
                    workspace_id=workspace_id,
                    item_id=item_id,
                    user_id=user_id,
                )
                dismissed.append(item_id)
            except Exception:
                continue
        return dismissed

    async def approve_many(
        self,
        *,
        workspace_id: UUID,
        item_ids: list[UUID],
        user_id: UUID,
        publish_now: bool = False,
        posts_per_day: int = 1,
    ) -> BulkApproveOutcome:
        """Duyệt cả loạt. `publish_now=False` thì **rải ra nhiều ngày**.

        Đây là lý do hàm này không gọi thẳng `approve()` với `scheduled_at=None`:
        `next_golden_hour()` trả cùng một mốc cho mọi lời gọi trong cùng một
        giây, nên duyệt sáu bài sẽ ra sáu bài đăng cùng một phút rồi im lặng sáu
        ngày. Chủ tiệm ngồi một buổi viết cả tuần nội dung chính là để tránh
        điều đó.

        Thứ tự bài giữ nguyên như caller truyền vào — bài đầu danh sách lên
        trước, nên "sắp xếp câu chuyện theo ý mình" là việc của UI, không phải
        của tầng này.

        Bài nào không duyệt được thì báo lý do riêng cho bài đó, và **không**
        tiêu mất một khung giờ: khung được cấp theo thứ tự thành công.
        """
        approved: list[UUID] = []
        failures: list[tuple[UUID, str]] = []

        if publish_now:
            slots: list[datetime] = []
            immediate: datetime | None = datetime.now(UTC)
        else:
            slots = spread_over_golden_hours(len(item_ids), per_day=posts_per_day)
            immediate = None

        for item_id in item_ids:
            # Cấp khung theo số bài đã duyệt thành công, không theo chỉ số vòng
            # lặp: một bài hỏng ở giữa mà vẫn ăn mất một khung thì lịch thủng
            # một ngày.
            target = immediate if publish_now else slots[len(approved)]
            try:
                await self.approve(
                    workspace_id=workspace_id,
                    item_id=item_id,
                    user_id=user_id,
                    scheduled_at=target,
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
        item = await self._require_item(workspace_id=workspace_id, item_id=item_id, for_update=True)
        if item.status not in RESCHEDULABLE_STATUSES:
            raise NotReschedulable(item.status)
        await self._content.set_item_status(item, status=item.status, scheduled_at=scheduled_at)
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
            item = await self._content.get_item(workspace_id=workspace_id, item_id=item_id)
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
                content_item_id=item.id,
                job_kind=action,
                input_summary=f"content_item={item.id} {summary}",
                output_summary=f"status={item.status}",
                created_at=datetime.now(UTC),
            )
        )
