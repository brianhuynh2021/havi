"""Port OAuth — service nối kênh chỉ biết interface này, không biết Facebook.

Tách khỏi `PublisherPort` vì hai việc khác nhau và xảy ra ở hai thời điểm khác
nhau: nối kênh chạy một lần trong request của người dùng, đăng bài chạy nhiều
lần trong worker. Gộp lại thì `FakePublisher` (đang được 22 test dùng) phải cài
thêm cả OAuth chỉ để tồn tại.

Lỗi cũng chia hai loại, cùng lý do như publish:

- `OAuthTemporaryError` — Facebook 5xx/timeout. Bảo chị bấm lại là xong.
- `OAuthPermanentError` — code sai/hết hạn, thiếu quyền, không có Page nào.
  Bấm lại y nguyên vẫn hỏng; phải nói rõ cần sửa gì.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from core.enums import Platform


@dataclass(frozen=True)
class OAuthAccount:
    """Một tài khoản đăng bài được (Facebook Page, Zalo OA…).

    `access_token` ở đây là plaintext và chỉ sống trong bộ nhớ tới lúc
    `ConnectionRepository.upsert` mã hoá nó. Không log dataclass này nguyên
    khối — dùng `__repr__` bên dưới, nó đã che token sẵn.
    """

    external_account_id: str
    account_name: str
    access_token: str
    external_user_id: str | None = None
    expires_at: datetime | None = None
    refresh_token: str | None = None

    def __repr__(self) -> str:
        """Che token trong repr.

        Che ở đây thay vì dặn nhau đừng log: `logger.exception` in cả local
        variable của frame, và một traceback lọt token ra log là token coi như
        đã lộ. Repr an toàn thì không phụ thuộc vào việc ai đó nhớ quy tắc.
        """
        return (
            f"OAuthAccount(external_account_id={self.external_account_id!r}, "
            f"account_name={self.account_name!r}, external_user_id={self.external_user_id!r}, "
            "access_token='***', "
            f"expires_at={self.expires_at!r})"
        )


class OAuthError(Exception):
    def __init__(self, platform: Platform, message: str) -> None:
        super().__init__(f"[{platform}] {message}")
        self.platform = platform
        self.detail = message


class OAuthTemporaryError(OAuthError):
    """Nền tảng lỗi tạm — bấm nối lại là được."""


class OAuthPermanentError(OAuthError):
    """Code hỏng, thiếu quyền, không có Page. Bấm lại y nguyên vẫn hỏng."""


class OAuthClientPort(ABC):
    @property
    @abstractmethod
    def platform(self) -> Platform: ...

    @property
    @abstractmethod
    def is_configured(self) -> bool:
        """False khi thiếu client id/secret — router trả 503 thay vì đẩy chủ
        tiệm sang một trang lỗi của Facebook."""

    @abstractmethod
    def authorization_url(self, *, state: str) -> str:
        """URL màn hình cấp quyền. `state` đã ký sẵn (`core.oauth_state`)."""

    @abstractmethod
    async def exchange_code(self, code: str) -> OAuthAccount:
        """Đổi `code` từ callback lấy tài khoản đăng bài được."""
