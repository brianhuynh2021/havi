"""Adapter gửi tin nhắn trả lời Facebook Page qua Graph API chính thức.

Chỉ dùng endpoint Graph API chính thức POST /v21.0/me/messages (hoặc /{page_id}/messages).
Payload:
{
  "recipient": {"id": recipient_id},
  "message": {"text": text},
  "messaging_type": "RESPONSE"
}
"""

import logging
from datetime import UTC, datetime
from typing import Any

import httpx

from adapters.persistence.connection_repository import ConnectionRepository
from core.enums import InboxItemType, Platform
from domain.ports.reply_publisher import (
    ReplyError,
    ReplyPublisherPort,
    ReplyRequest,
    ReplyResult,
)

logger = logging.getLogger("havi.facebook_reply")

GRAPH_VERSION = "v21.0"
GRAPH_BASE = f"https://graph.facebook.com/{GRAPH_VERSION}"


class FacebookReplyAdapter(ReplyPublisherPort):
    def __init__(
        self,
        connections: ConnectionRepository,
        *,
        timeout_seconds: float = 15.0,
    ) -> None:
        self._connections = connections
        self._timeout = timeout_seconds

    @property
    def platform(self) -> Platform:
        return Platform.FACEBOOK

    async def send_reply(self, request: ReplyRequest) -> ReplyResult:
        connection = await self._connections.get(
            workspace_id=request.workspace_id,
            platform=Platform.FACEBOOK,
        )
        if connection is None:
            raise ReplyError(
                self.platform,
                "Chưa kết nối Fanpage Facebook — vui lòng kết nối Fanpage trong mục Cài đặt.",
            )

        access_token = self._connections.read_access_token(connection)
        page_id = connection.external_account_id or "me"

        # Loại inbox item là nguồn sự thật. Comment cũng có `from.id`, nhưng đó
        # không có nghĩa Havi được phép đổi thành tin nhắn riêng tư Messenger.
        if request.item_type == InboxItemType.MESSAGE and request.recipient_id:
            url = f"{GRAPH_BASE}/{page_id}/messages"
            payload: dict[str, Any] = {
                "recipient": {"id": request.recipient_id},
                "message": {"text": request.text},
                "messaging_type": "RESPONSE",
            }
        elif request.item_type == InboxItemType.COMMENT and request.external_message_id:
            # Bình luận bài viết Facebook feed: trả lời trực tiếp dưới comment
            url = f"{GRAPH_BASE}/{request.external_message_id}/comments"
            payload = {
                "message": request.text,
            }
        else:
            raise ReplyError(
                self.platform,
                "Thiếu định danh hợp lệ để phản hồi đúng loại tin nhắn/bình luận.",
            )

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                response = await client.post(
                    url,
                    json=payload,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
            except httpx.RequestError as exc:
                logger.error("Lỗi mạng khi gọi Facebook Graph API: %s", exc)
                raise ReplyError(
                    self.platform,
                    f"Lỗi mạng khi kết nối Meta Graph API: {exc}",
                ) from exc

            body = response.json() if response.content else {}
            if response.status_code >= 400:
                err_data = body.get("error", {})
                code = err_data.get("code")
                msg = err_data.get("message", "Lỗi gửi tin nhắn Facebook")
                logger.error("Meta Graph API error code %s: %s", code, msg)
                raise ReplyError(self.platform, f"Meta Graph API error ({code}): {msg}")

            message_id = body.get("message_id") or body.get("id") or "fb_msg_ok"
            return ReplyResult(
                external_reply_id=str(message_id),
                sent_at=datetime.now(UTC),
            )
