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
from core.events import EventLogEntry
from domain.models.inbox import InboxItem


class InboxItemNotFound(Exception):
    pass


def _normalize(text: str) -> str:
    """Chuẩn hoá để so khớp FAQ: bỏ khoảng trắng thừa, hạ chữ thường, bỏ dấu câu
    cuối câu. Chỉ vậy thôi — không stem, không đồng nghĩa."""
    return " ".join(text.strip().lower().split()).rstrip("?!.")


def _match_approved_faq(faqs: list[dict], content: str) -> str | None:
    """Trả câu trả lời FAQ khi câu hỏi khớp *tuyệt đối*, ngược lại `None`.

    Bản trước dùng `question in content`, tức là một FAQ ngắn như "giá" sẽ khớp
    mọi tin nhắn có chữ "giá" và tự gửi câu trả lời sẵn. Nguyên tắc #1 chỉ cho
    tự động với đúng câu chủ tiệm đã duyệt, nên so khớp phải là bằng nhau sau
    chuẩn hoá. Khớp hụt thì tệ nhất là chủ tiệm phải bấm duyệt — khớp thừa là
    gửi nhầm câu trả lời cho khách.
    """
    normalized_content = _normalize(content)
    for entry in faqs:
        question = _normalize(entry.get("question") or "")
        answer = entry.get("answer") or ""
        if not question or not answer:
            continue
        if not entry.get("approved", True):
            continue
        if question == normalized_content:
            return answer
    return None


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
        external_message_id: str | None = None,
    ) -> InboxItem:
        """Nhận inbox mới: kiểm tra FAQ hoặc sinh câu trả lời gợi ý.

        `external_message_id` là ID sự kiện của nền tảng. Nếu đã có item mang
        đúng ID đó thì trả lại item cũ — Meta gửi lại webhook khi không nhận
        được 200 kịp, và lần gửi lại không được sinh thêm một tin nhắn khách.
        """
        if external_message_id:
            existing = await self._inbox.get_by_external_id(
                workspace_id=workspace_id,
                platform=platform,
                external_message_id=external_message_id,
            )
            if existing is not None:
                return existing

        profile = await self._profiles.get(workspace_id)
        faqs = profile.faq if profile and profile.faq else []
        matched_answer = _match_approved_faq(faqs, content)

        if matched_answer:
            # FAQ khớp tuyệt đối -> đây là ngoại lệ duy nhất được tự động trả
            # lời khách (Nguyên tắc #1).
            item = await self._inbox.create(
                workspace_id=workspace_id,
                platform=platform,
                content=content,
                author_name=author_name,
                ai_suggested_reply=matched_answer,
                status=InboxItemStatus.SENT,
                external_message_id=external_message_id,
            )
            # Tự động gửi cho khách là hành vi nhạy cảm nhất trong hệ thống —
            # phải để lại dấu vết để về sau trả lời được "vì sao khách nhận câu
            # này mà chủ tiệm không bấm gì".
            await self._events.record(
                EventLogEntry(
                    workspace_id=workspace_id,
                    job_kind="inbox.faq_auto_reply",
                    input_summary=f"{platform.value}: tin nhắn khớp FAQ đã duyệt",
                    output_summary=matched_answer[:200],
                )
            )
            return item

        # Không khớp FAQ -> Tạo bản nháp gợi ý, chờ người thật duyệt
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
            external_message_id=external_message_id,
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

        await self._inbox.update_status(item, status=InboxItemStatus.DISMISSED)
