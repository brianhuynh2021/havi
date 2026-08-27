"""Adapter gửi tin nhắn trả lời Facebook Page qua Graph API chính thức.

Chỉ dùng endpoint Graph API chính thức POST /{page_id}/messages.
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

from adapters.meta_graph import GRAPH_BASE
from adapters.persistence.connection_repository import ConnectionRepository
from core.enums import ConnectionStatus, InboxItemType, Platform
from domain.ports.reply_publisher import (
    ReplyError,
    ReplyPublisherPort,
    ReplyRequest,
    ReplyResult,
)

logger = logging.getLogger("havi.facebook_reply")


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
        if connection.status != ConnectionStatus.CONNECTED:
            raise ReplyError(
                self.platform,
                "Kết nối Facebook cần được nối lại trước khi gửi phản hồi.",
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

            try:
                body = response.json() if response.content else {}
            except ValueError as exc:
                raise ReplyError(
                    self.platform,
                    "Meta trả dữ liệu không đọc được; chưa thể xác nhận đã gửi.",
                ) from exc
            if response.status_code >= 400:
                err_data = body.get("error", {})
                code = err_data.get("code")
                # Không đưa provider message vào log hay event: Meta đôi lúc
                # vọng tham số request trong message và có thể làm lộ token.
                logger.error("Meta Graph API reply error code=%s", code)
                if code in {102, 190}:
                    detail = "Quyền Facebook đã hết hiệu lực — hãy nối lại Trang."
                    await self._connections.mark_unusable(
                        connection,
                        status=ConnectionStatus.EXPIRED,
                        reason=detail,
                    )
                elif code in {10, 200}:
                    detail = "Facebook từ chối quyền gửi phản hồi — hãy nối lại Trang."
                    await self._connections.mark_unusable(
                        connection,
                        status=ConnectionStatus.REVOKED,
                        reason=detail,
                    )
                else:
                    detail = f"Meta Graph API từ chối phản hồi (mã {code or 'không rõ'})."
                raise ReplyError(self.platform, detail)

            message_id = body.get("message_id") or body.get("id")
            if not message_id:
                # 2xx không ID không chứng minh được tin đã gửi. Báo thành công
                # ở đây sẽ khiến người vận hành bỏ qua một khách chưa được trả lời.
                raise ReplyError(
                    self.platform,
                    "Meta không trả mã phản hồi; chưa thể xác nhận đã gửi.",
                )
            return ReplyResult(
                external_reply_id=str(message_id),
                sent_at=datetime.now(UTC),
            )
