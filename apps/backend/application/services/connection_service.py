"""Connection service — nối kênh, nối lại, ngắt kênh.

Chỗ này cưỡng chế ba việc mà router không được tự làm:

1. **Callback phải chứng minh được nó thuộc về ai.** `/callback` là endpoint
   public (Facebook điều hướng trình duyệt tới, không kèm JWT). Danh tính đến
   từ `state` đã ký ở bước `/start` — xem `core.oauth_state`.
2. **Người ở state phải còn là thành viên workspace.** State sống 10 phút; một
   người bị gỡ khỏi workspace ngay sau khi bấm "Nối kênh" không được nối token
   của mình vào tiệm cũ.
3. **Token không bao giờ ra khỏi tầng này.** Service trả `PlatformConnection`
   schema (không có field token) chứ không trả model.
"""

import logging
from uuid import UUID

from adapters.oauth.base import OAuthClientPort, OAuthError
from adapters.persistence.connection_repository import ConnectionRepository
from adapters.persistence.workspace_member_repository import WorkspaceMemberRepository
from core.config import Settings
from core.enums import Platform
from core.oauth_state import (
    DEFAULT_RETURN_KEY,
    RETURN_PATHS,
    InvalidOAuthState,
    create_oauth_state,
    verify_oauth_state,
)
from core.schemas import PlatformConnection as PlatformConnectionSchema
from core.token_crypto import TokenEncryptionUnavailable
from domain.models.connection import PlatformConnection

logger = logging.getLogger(__name__)


class PlatformNotSupported(Exception):
    """Nền tảng chưa có adapter OAuth (Zalo/Google ở pilot)."""

    def __init__(self, platform: Platform) -> None:
        super().__init__(f"Chưa hỗ trợ nối {platform.value}")
        self.platform = platform


class PlatformNotConfigured(Exception):
    """Thiếu client id/secret trong config — lỗi vận hành, không phải lỗi user."""

    def __init__(self, platform: Platform) -> None:
        super().__init__(f"Chưa cấu hình OAuth cho {platform.value}")
        self.platform = platform


class ConnectionNotFound(Exception):
    pass


class NotWorkspaceMember(Exception):
    """State hợp lệ nhưng người đó không còn quyền trên workspace."""


class ConnectionService:
    def __init__(
        self,
        *,
        connections: ConnectionRepository,
        members: WorkspaceMemberRepository,
        oauth_clients: dict[Platform, OAuthClientPort],
        settings: Settings,
    ) -> None:
        self._connections = connections
        self._members = members
        self._oauth_clients = oauth_clients
        self._settings = settings

    # --- Đọc -----------------------------------------------------------------

    async def list_connections(self, workspace_id: UUID) -> list[PlatformConnectionSchema]:
        rows = await self._connections.list_for_workspace(workspace_id)
        return [to_schema(row) for row in rows]

    # --- Nối kênh ------------------------------------------------------------

    def start(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID,
        platform: Platform,
        return_key: str = DEFAULT_RETURN_KEY,
    ) -> tuple[str, str]:
        """Trả `(authorization_url, state)`.

        Không ghi gì vào DB: state đã ký nên không cần bảng lưu phiên, và bấm
        "Nối kênh" rồi bỏ giữa chừng không để lại rác.

        `return_key` đi *trong state đã ký* chứ không qua query param của
        callback: query param do client kiểm soát, nên dùng nó để chọn nơi
        redirect là mở đường cho open redirect.
        """
        client = self._client_for(platform)
        state = create_oauth_state(
            workspace_id=workspace_id,
            user_id=user_id,
            platform=platform,
            settings=self._settings,
            return_key=return_key,
        )
        return client.authorization_url(state=state), state

    def return_path_for(self, state: str, *, platform: Platform) -> str:
        """Nơi đưa người dùng về, đọc từ state đã ký.

        Tách riêng khỏi `complete` vì router cần biết đường về **cả khi
        `complete` ném lỗi** — báo lỗi xong vẫn phải đưa chủ tiệm về đúng trang
        họ bấm từ đó. State hỏng thì về mặc định, không ném thêm lỗi ở đây.
        """
        try:
            payload = verify_oauth_state(
                state, platform=platform, settings=self._settings
            )
        except InvalidOAuthState:
            return RETURN_PATHS[DEFAULT_RETURN_KEY]
        return payload.return_path

    async def complete(
        self, *, platform: Platform, code: str, state: str
    ) -> PlatformConnectionSchema:
        """Xử lý callback: kiểm state, đổi code, lưu token đã mã hoá.

        Ném `InvalidOAuthState` khi state hỏng/hết hạn/lệch platform, và
        `NotWorkspaceMember` khi người ký state không còn quyền.
        """
        client = self._client_for(platform)
        payload = verify_oauth_state(state, platform=platform, settings=self._settings)

        if not await self._members.is_member(
            workspace_id=payload.workspace_id, user_id=payload.user_id
        ):
            raise NotWorkspaceMember(
                "Tài khoản này không còn quyền trên workspace — đăng nhập lại rồi nối kênh"
            )

        account = await client.exchange_code(code)

        connection = await self._connections.upsert(
            workspace_id=payload.workspace_id,
            platform=platform,
            access_token=account.access_token,
            refresh_token=account.refresh_token,
            expires_at=account.expires_at,
            account_name=account.account_name,
            external_account_id=account.external_account_id,
            connected_by=payload.user_id,
        )
        logger.info(
            "workspace %s nối %s vào trang %s",
            payload.workspace_id,
            platform.value,
            account.external_account_id,
        )
        return to_schema(connection)

    # --- Ngắt kênh -----------------------------------------------------------

    async def disconnect(self, *, workspace_id: UUID, platform: Platform) -> None:
        """Xoá hẳn bản ghi kèm token đã mã hoá.

        Khác `mark_unusable` (giữ bản ghi để hiện nút "Nối lại"): đây là chủ
        tiệm chủ động ngắt, giữ token lại không còn lý do gì.
        """
        connection = await self._connections.get(
            workspace_id=workspace_id, platform=platform
        )
        if connection is None:
            raise ConnectionNotFound()
        await self._connections.delete(connection)

    # --- Nội bộ --------------------------------------------------------------

    def _client_for(self, platform: Platform) -> OAuthClientPort:
        client = self._oauth_clients.get(platform)
        if client is None:
            raise PlatformNotSupported(platform)
        if not client.is_configured:
            raise PlatformNotConfigured(platform)
        return client


def to_schema(connection: PlatformConnection) -> PlatformConnectionSchema:
    """Model → schema. Đây là chỗ token bị bỏ lại.

    Không dùng `model_validate(connection)`: nó sẽ đọc theo tên field của
    schema nên hôm nay vẫn an toàn, nhưng chỉ cần ai đó thêm một field tên
    trùng vào schema là token đi ra response. Liệt kê tay thì thêm field mới
    phải sửa ở đây, có chủ đích.
    """
    return PlatformConnectionSchema(
        workspace_id=connection.workspace_id,
        platform=connection.platform,
        status=connection.status,
        account_name=connection.account_name,
        expires_at=connection.expires_at,
        connected_by=connection.connected_by,
    )


__all__ = [
    "ConnectionNotFound",
    "ConnectionService",
    "NotWorkspaceMember",
    "PlatformNotConfigured",
    "PlatformNotSupported",
    "InvalidOAuthState",
    "OAuthError",
    "TokenEncryptionUnavailable",
    "to_schema",
]
