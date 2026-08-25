"""Inbox service — xử lý tin nhắn/bình luận từ khách hàng.

NGUYÊN TẮC #2 & #7:
1. Không bao giờ tự động gửi tin nhắn cho khách (full_auto = False).
2. Ngoại lệ duy nhất là FAQ chủ đã duyệt sẵn từng câu trong Brand Profile.
"""

import logging
from uuid import UUID

from adapters.persistence.brand_profile_repository import BrandProfileRepository
from adapters.persistence.event_log_repository import EventLogRepository
from adapters.persistence.inbox_repository import InboxRepository
from core.enums import InboxItemStatus, InboxItemType, Platform
from core.events import EventLogEntry
from domain.models.inbox import InboxItem
from domain.ports.reply_publisher import ReplyError, ReplyPublisherPort, ReplyRequest

logger = logging.getLogger(__name__)

class InboxItemNotFound(Exception):
    pass


def _normalize(text: str) -> str:
    """Chuẩn hoá để so khớp FAQ: bỏ khoảng trắng thừa, hạ chữ thường, bỏ dấu câu
    cuối câu. Chỉ vậy thôi — không stem, không đồng nghĩa."""
    return " ".join(text.strip().lower().split()).rstrip("?!.")


def _match_approved_faq(faqs: list[dict], content: str) -> str | None:
    """Trả câu trả lời FAQ khi câu hỏi khớp *tuyệt đối*, ngược lại `None`.

    **Fail-closed ở cờ `approved`.** Bản trước dùng `entry.get("approved", True)`
    — thiếu trường thì coi như đã duyệt. Nghĩa là một hàng FAQ đến từ import,
    từ migration, hay từ một client cũ không khai `approved` sẽ được gửi thẳng
    tới khách thật mà không ai từng đọc nó.

    Câu trả lời tự động là thứ duy nhất trong Havi đi tới người ngoài mà không
    qua mắt chủ tiệm. Nói sai giờ mở cửa hay một cam kết dịch vụ không rút lại
    được, nên mặc định phải là "chưa duyệt", không phải "đã duyệt".
    """
    normalized_content = _normalize(content)
    for entry in faqs:
        question = _normalize(entry.get("question") or "")
        answer = entry.get("answer") or ""
        if not question or not answer:
            continue
        if entry.get("approved") is not True:
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
        reply_publishers: dict[Platform, ReplyPublisherPort] | None = None,
    ) -> None:
        self._inbox = inbox
        self._profiles = profiles
        self._events = events
        # Publisher giả phải được lắp ghép rõ ràng ở composition root cho local.
        # Service không được tự rơi về fake vì điều đó biến cấu hình thiếu ở
        # production thành một lần gửi "thành công" không hề xảy ra ngoài đời.
        self._reply_publishers = reply_publishers if reply_publishers is not None else {}

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
        item_type: InboxItemType = InboxItemType.MESSAGE,
        external_message_id: str | None = None,
        recipient_id: str | None = None,
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
            # FAQ khớp tuyệt đối -> gửi qua reply publisher port (Nguyên tắc #1)
            reply_res = None
            auto_status = InboxItemStatus.SENT
            try:
                publisher = self._reply_publishers.get(platform)
                if publisher is None:
                    raise ReplyError(platform, "Chưa cấu hình kênh gửi phản hồi")
                reply_res = await publisher.send_reply(
                    ReplyRequest(
                        workspace_id=workspace_id,
                        platform=platform,
                        text=matched_answer,
                        item_type=item_type,
                        recipient_id=recipient_id,
                        external_message_id=external_message_id,
                    )
                )
            except ReplyError as exc:
                logger.warning("Không thể tự động gửi trả lời: %s", exc)
                auto_status = InboxItemStatus.FAILED

            item = await self._inbox.create(
                workspace_id=workspace_id,
                platform=platform,
                content=content,
                author_name=author_name,
                type=item_type,
                ai_suggested_reply=matched_answer,
                status=auto_status,
                external_message_id=external_message_id,
                recipient_id=recipient_id,
            )
            # Tự động gửi cho khách là hành vi nhạy cảm nhất trong hệ thống —
            # phải để lại dấu vết để về sau trả lời được "vì sao khách nhận câu
            # này mà chủ tiệm không bấm gì".
            await self._events.record(
                EventLogEntry(
                    workspace_id=workspace_id,
                    job_kind="inbox.faq_auto_reply",
                    input_summary=f"{platform.value}: tin nhắn khớp FAQ đã duyệt",
                    output_summary=(
                        f"status:{auto_status.value} reply_id:{reply_res.external_reply_id if reply_res else 'none'} | {matched_answer[:200]}"
                    ),
                )
            )
            return item

        # Không khớp FAQ -> Tạo bản nháp gợi ý, chờ người thật duyệt
        suggested_reply = f"Chào {author_name}, cảm ơn bạn đã nhắn tin. Tiệm sẽ phản hồi bạn sớm ạ."
        return await self._inbox.create(
            workspace_id=workspace_id,
            platform=platform,
            content=content,
            author_name=author_name,
            type=item_type,
            ai_suggested_reply=suggested_reply,
            status=InboxItemStatus.DRAFTED,
            external_message_id=external_message_id,
            recipient_id=recipient_id,
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

        try:
            publisher = self._reply_publishers.get(item.platform)
            if publisher is None:
                raise ReplyError(item.platform, "Chưa cấu hình kênh gửi phản hồi")
            reply_res = await publisher.send_reply(
                ReplyRequest(
                    workspace_id=workspace_id,
                    platform=item.platform,
                    text=text,
                    item_type=item.type,
                    recipient_id=item.recipient_id,
                    external_message_id=item.external_message_id,
                )
            )
        except ReplyError as exc:
            logger.warning("Không thể gửi tin nhắn thật qua API nền tảng: %s", exc)
            await self._inbox.update_status(
                item,
                status=InboxItemStatus.FAILED,
                reply_text=text,
            )
            await self._events.record(
                EventLogEntry(
                    workspace_id=workspace_id,
                    job_kind="inbox.reply_failed",
                    input_summary=f"{item.platform.value}: lỗi gửi phản hồi cho {item.author_name}",
                    output_summary=f"error:{str(exc)[:200]}",
                )
            )
            raise

        updated = await self._inbox.update_status(
            item,
            status=InboxItemStatus.SENT,
            reply_text=text,
        )

        await self._events.record(
            EventLogEntry(
                workspace_id=workspace_id,
                job_kind="inbox.reply_sent",
                input_summary=f"{item.platform.value}: gửi phản hồi cho {item.author_name}",
                output_summary=f"reply_id:{reply_res.external_reply_id if reply_res else 'none'} | {text[:200]}",
            )
        )
        return updated

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
