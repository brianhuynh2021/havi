"""Fake reply publisher — dùng cho test và local development."""

from datetime import UTC, datetime

from core.enums import Platform
from domain.ports.reply_publisher import ReplyPublisherPort, ReplyRequest, ReplyResult


class FakeReplyPublisher(ReplyPublisherPort):
    """Giả lập việc gửi phản hồi tin nhắn/bình luận cho local và test."""

    def __init__(self, platform: Platform = Platform.FACEBOOK) -> None:
        self._platform = platform
        self.calls: list[ReplyRequest] = []

    @property
    def platform(self) -> Platform:
        return self._platform

    async def send_reply(
        self, request: ReplyRequest, *, access_token: str | None = None
    ) -> ReplyResult:
        self.calls.append(request)
        return ReplyResult(
            external_reply_id=f"reply_{self._platform.value}_{len(self.calls)}",
            sent_at=datetime.now(UTC),
        )
