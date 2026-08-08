"""Fake publisher — test luồng publish không cần quyền nền tảng thật.

Facebook App Review duyệt `pages_manage_posts` có thể mất vài tuần (ROADMAP §10
xếp đây là rủi ro chặn pilot). Adapter này cho phép làm và kiểm hết phần khó —
idempotency, row lock, retry backoff, dead-letter, phân loại lỗi — trước khi có
quyền thật, rồi lúc có quyền chỉ đổi adapter.

Khác `FacebookPublisher` ở chỗ nó không gọi mạng. Giống ở chỗ nó ném đúng ba
loại `PublishError` mà worker phải xử — nên logic worker test ở đây chạy được
với adapter thật.
"""

from datetime import UTC, datetime

from core.enums import Channel
from domain.ports.publisher import (
    AuthPermissionError,
    PublisherPort,
    PublishRequest,
    PublishResult,
    TemporaryPublishError,
    ValidationPublishError,
)


class FakePublisher(PublisherPort):
    """Ghi lại lời gọi và trả kết quả đã dựng sẵn.

    `fail_times` mô phỏng lỗi thoáng qua: hỏng N lần đầu rồi thành công — đúng
    hình dạng của rate limit, và là thứ cần để kiểm tra retry backoff thật sự
    hoạt động chứ không phải bỏ cuộc ngay.
    """

    def __init__(
        self,
        *,
        channel: Channel = Channel.FACEBOOK_PAGE,
        error: Exception | None = None,
        fail_times: int = 0,
        post_id: str = "fb_post_123",
    ) -> None:
        self._channel = channel
        self._error = error
        self._fail_times = fail_times
        self._post_id = post_id
        self.calls: list[PublishRequest] = []
        self.tokens_seen: list[str] = []

    @property
    def channel(self) -> Channel:
        return self._channel

    async def publish(
        self, request: PublishRequest, *, access_token: str
    ) -> PublishResult:
        self.calls.append(request)
        self.tokens_seen.append(access_token)

        if self._fail_times > 0:
            self._fail_times -= 1
            raise TemporaryPublishError(self._channel, "Rate limit — thử lại sau")
        if self._error is not None:
            raise self._error

        # ID gắn số lần gọi: nếu logic chống trùng hỏng và adapter bị gọi hai
        # lần, hai ID khác nhau làm lộ ra ngay thay vì trùng nhau che mất lỗi.
        return PublishResult(
            external_post_id=f"{self._post_id}_{len(self.calls)}",
            published_at=datetime.now(UTC),
        )


def auth_error(channel: Channel = Channel.FACEBOOK_PAGE) -> AuthPermissionError:
    return AuthPermissionError(channel, "Token hết hạn hoặc mất quyền đăng bài")


def validation_error(channel: Channel = Channel.FACEBOOK_PAGE) -> ValidationPublishError:
    return ValidationPublishError(channel, "Nền tảng từ chối nội dung này")
