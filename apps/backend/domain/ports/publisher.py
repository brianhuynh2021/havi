"""Port cho adapter đăng bài — domain chỉ biết interface này, không biết Facebook.

Thiết kế theo SYSTEM_ARCHITECTURE.md §5.2: mỗi kênh một adapter, lõi không biết
kênh. Thêm Zalo/Google sau chỉ là thêm một lớp cài đặt port này.

Điểm quan trọng nhất của port này là **phân loại lỗi**. Adapter không quyết định
retry hay không — nó chỉ nói lỗi thuộc loại nào, và worker dựa vào đó để xử:

- `TEMPORARY` (429, 5xx trước khi nền tảng chấp nhận) → thử lại với backoff
- `AMBIGUOUS_OUTCOME` (timeout sau khi gửi request) → dừng để đối soát, không retry
- `AUTH_PERMISSION` (token hết hạn, mất quyền) → KHÔNG retry, bắt chủ tiệm nối
  lại kênh. Retry ở đây chỉ đập vào API và vẫn hỏng.
- `VALIDATION_PERMANENT` (nội dung bị từ chối, ảnh sai định dạng) → KHÔNG retry,
  cùng payload sẽ hỏng y hệt.

Gộp ba loại này thành "lỗi" chung là cách chắc chắn nhất để hoặc retry vô tận
một thứ không bao giờ chạy, hoặc bỏ cuộc trên một lỗi mạng thoáng qua.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime

from core.enums import Channel, PublishFailureKind


@dataclass
class PublishRequest:
    """Mọi thứ adapter cần để đăng một bài."""

    text: str
    #: URL ảnh đã ký sẵn, adapter tải về hoặc chuyển tiếp cho nền tảng.
    media_urls: list[str] = field(default_factory=list)
    #: ID trang/tài khoản trên nền tảng (Facebook Page ID, Zalo OA ID…).
    external_account_id: str | None = None
    #: Khoá idempotency của publish job. Nền tảng nào hỗ trợ thì chuyển xuống để
    #: chính nền tảng cũng chặn trùng — lớp phòng thủ thứ hai sau unique
    #: constraint của Havi.
    idempotency_key: str | None = None
    #: Kênh xuất bản cụ thể (Facebook Post, Facebook Reels...)
    channel: Channel | None = None


@dataclass
class PublishResult:
    """Đăng thành công."""

    #: ID bài trên nền tảng. Bắt buộc — không có nó thì không đối soát được khi
    #: worker chết giữa chừng, và đó là lúc dễ đăng trùng nhất.
    external_post_id: str
    published_at: datetime


class PublishError(Exception):
    """Base cho mọi lỗi publish. `kind` quyết định worker có retry không."""

    kind: PublishFailureKind

    def __init__(self, channel: Channel, message: str) -> None:
        super().__init__(f"[{channel}] {message}")
        self.channel = channel
        self.detail = message


class TemporaryPublishError(PublishError):
    """Lỗi thoáng qua đã biết là an toàn để thử lại."""

    kind = PublishFailureKind.TEMPORARY


class AmbiguousPublishError(PublishError):
    """Không biết nền tảng đã tạo bài hay chưa; phải đối soát trước khi retry."""

    kind = PublishFailureKind.AMBIGUOUS_OUTCOME


class AuthPermissionError(PublishError):
    """Token hết hạn hoặc mất quyền. Không retry — cần chủ tiệm nối lại kênh."""

    kind = PublishFailureKind.AUTH_PERMISSION


class ValidationPublishError(PublishError):
    """Nền tảng từ chối nội dung. Không retry — cùng payload sẽ hỏng y hệt."""

    kind = PublishFailureKind.VALIDATION_PERMANENT


@dataclass(frozen=True)
class ReelStatus:
    """Trạng thái thật của một Reel đọc lại từ nền tảng.

    Tồn tại vì "gửi xong" không phải "đã đăng": Reels xử lý bất đồng bộ, và một
    video được nhận vẫn có thể hỏng sau đó. Đây cũng là thứ dùng để đối soát khi
    worker chết giữa chừng — không có nó thì lối duy nhất còn lại là đăng lại,
    và đăng lại là cách tạo ra bài trùng.
    """

    video_id: str
    #: `published` | `in_progress` | `error` | `not_found` | `unknown`
    phase: str
    permalink_url: str | None = None
    error_message: str | None = None

    @property
    def is_published(self) -> bool:
        return self.phase == "published"

    @property
    def is_failed(self) -> bool:
        return self.phase in ("error", "not_found")

    @property
    def is_pending(self) -> bool:
        return not self.is_published and not self.is_failed


@dataclass(frozen=True)
class ReconciliationOutcome:
    """Kết quả đối soát một publish job bị mơ hồ / chờ xác nhận."""

    status: str  # "published" | "failed" | "in_progress"
    external_post_id: str | None = None
    permalink_url: str | None = None
    error_message: str | None = None

    @property
    def is_published(self) -> bool:
        return self.status == "published"

    @property
    def is_failed(self) -> bool:
        return self.status == "failed"

    @property
    def is_in_progress(self) -> bool:
        return self.status == "in_progress"


class PublisherPort(ABC):
    """Một adapter cho một kênh."""

    @property
    @abstractmethod
    def channel(self) -> Channel: ...

    @abstractmethod
    async def publish(self, request: PublishRequest, *, access_token: str) -> PublishResult:
        """Đăng bài. Ném một trong ba `PublishError` ở trên khi hỏng.

        `access_token` truyền vào đã giải mã sẵn — adapter không tự đọc DB và
        không tự giải mã, để chỗ nào chạm token là đếm được.
        """

    async def reconcile(
        self,
        *,
        external_post_id: str | None = None,
        access_token: str,
        **kwargs,
    ) -> ReconciliationOutcome:
        """Đối soát lại trạng thái bài đăng trên kênh đối tác."""
        raise NotImplementedError
