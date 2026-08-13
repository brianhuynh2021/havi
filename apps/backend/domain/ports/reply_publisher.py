"""Port cho adapter trả lời tin nhắn/bình luận (Reply Publisher)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from core.enums import Platform


@dataclass
class ReplyRequest:
    workspace_id: UUID
    platform: Platform
    text: str
    recipient_id: str | None = None
    external_message_id: str | None = None


@dataclass
class ReplyResult:
    external_reply_id: str
    sent_at: datetime


class ReplyError(Exception):
    def __init__(self, platform: Platform, message: str) -> None:
        super().__init__(f"[{platform}] {message}")
        self.platform = platform
        self.message = message


class ReplyPublisherPort(ABC):
    """Port định nghĩa giao tiếp phát gửi reply tới các nền tảng."""

    @property
    @abstractmethod
    def platform(self) -> Platform: ...

    @abstractmethod
    async def send_reply(
        self, request: ReplyRequest, *, access_token: str | None = None
    ) -> ReplyResult: ...
