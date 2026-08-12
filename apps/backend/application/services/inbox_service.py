"""Inbox service — xử lý tin nhắn/bình luận từ khách hàng.

NGUYÊN TẮC #2 & #7:
1. Không bao giờ tự động gửi tin nhắn cho khách (full_auto = False).
2. Ngoại lệ duy nhất là FAQ chủ đã duyệt sẵn từng câu trong Brand Profile.
"""

from uuid import UUID

from adapters.persistence.brand_profile_repository import BrandProfileRepository
from adapters.persistence.event_log_repository import EventLogRepository
from adapters.persistence.inbox_repository import InboxRepository
from core.enums import InboxItemStatus, Platform
from domain.models.inbox import InboxItem


class InboxItemNotFound(Exception):
    pass


class InboxService:
    def __init__(
        self,
        *,
        inbox: InboxRepository,
        profiles: BrandProfileRepository,
        events: EventLogRepository,
    ) -> None:
        self._inbox = inbox
        self._profiles = profiles
        self._events = events

    async def list_items(
        self,
        *,
        workspace_id: UUID,
        status: InboxItemStatus | None = None,
        platform: Platform | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[InboxItem], int]:
        return await self._inbox.list_items(
            workspace_id=workspace_id,
            status=status,
            platform=platform,
            limit=limit,
            offset=offset,
        )

    async def process_inquiry(
        self,
        *,
        workspace_id: UUID,
        platform: Platform,
        author_name: str,
        content: str,
    ) -> InboxItem:
        """Nhận inbox mới: kiểm tra FAQ hoặc sinh câu trả lời gợi ý."""
        profile = await self._profiles.get_by_workspace(workspace_id)
        faqs = profile.faq if profile and profile.faq else []

        # 1. Kiểm tra FAQ đã duyệt sẵn
        matched_answer: str | None = None
        for faq_entry in faqs:
            q = (faq_entry.get("question") or "").strip().lower()
            a = faq_entry.get("answer") or ""
            is_approved = faq_entry.get("approved", True)
            if q and q in content.lower() and is_approved and a:
                matched_answer = a
                break

        if matched_answer:
            # FAQ khớp -> Gửi tự động
            return await self._inbox.create(
                workspace_id=workspace_id,
                platform=platform,
                content=content,
                author_name=author_name,
                ai_suggested_reply=matched_answer,
                status=InboxItemStatus.SENT,
            )

        # 2. Không khớp FAQ -> Tạo bản nháp gợi ý, chờ người thật duyệt
        suggested_reply = (
            f"Chào {author_name}, Havi đã nhận thông tin! Tiệm sẽ phản hồi bạn ngay ạ."
        )
        return await self._inbox.create(
            workspace_id=workspace_id,
            platform=platform,
            content=content,
            author_name=author_name,
            ai_suggested_reply=suggested_reply,
            status=InboxItemStatus.DRAFTED,
        )

    async def send_reply(
        self,
        *,
        workspace_id: UUID,
        item_id: UUID,
        text: str,
    ) -> InboxItem:
        item = await self._inbox.get(workspace_id=workspace_id, item_id=item_id)
        if item is None:
            raise InboxItemNotFound()

        return await self._inbox.update_status(
            item,
            status=InboxItemStatus.SENT,
            reply_text=text,
        )

    async def dismiss_item(
        self,
        *,
        workspace_id: UUID,
        item_id: UUID,
    ) -> None:
        item = await self._inbox.get(workspace_id=workspace_id, item_id=item_id)
        if item is None:
            raise InboxItemNotFound()

        await self._inbox.update_status(item, status=InboxItemStatus.SENT)
