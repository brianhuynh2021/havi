from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.enums import Channel, ConnectionStatus, Platform
from core.token_crypto import decrypt_token, encrypt_token
from domain.models.connection import PlatformConnection

PLATFORM_TO_CHANNELS: dict[Platform, list[Channel]] = {
    Platform.FACEBOOK: [Channel.FACEBOOK_PAGE, Channel.REELS],
    Platform.ZALO_OA: [Channel.ZALO_OA],
    Platform.GOOGLE_BUSINESS: [Channel.GOOGLE_BUSINESS],
    Platform.TIKTOK: [Channel.TIKTOK],
    Platform.YOUTUBE: [Channel.YOUTUBE],
}


class ConnectionRepository:
    """Kết nối OAuth nền tảng. Token vào/ra qua đây đều đi kèm mã hoá/giải mã.

    Cố ý gói mã hoá vào repository thay vì để service tự làm: chỗ nào chạm
    plaintext token là đếm được, và không ai lỡ tay lưu token trần.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, *, workspace_id: UUID, platform: Platform) -> PlatformConnection | None:
        result = await self._session.execute(
            select(PlatformConnection).where(
                PlatformConnection.workspace_id == workspace_id,
                PlatformConnection.platform == platform,
            )
        )
        return result.scalar_one_or_none()

    async def find_by_external_account(
        self, *, platform: Platform, external_account_id: str
    ) -> PlatformConnection | None:
        """Tra ngược từ ID trang của nền tảng về workspace.

        Webhook đến không kèm JWT và không biết workspace nào — thứ duy nhất nó
        mang theo là ID trang. Đây là chỗ duy nhất trong hệ thống truy vấn
        connection mà không lọc theo `workspace_id`, nên nó phải nằm gọn ở đây và
        chỉ dùng cho đường webhook; caller lấy `workspace_id` từ kết quả rồi mọi
        truy vấn sau đó quay lại lọc theo workspace như bình thường.

        Chỉ nhận kết nối đang `CONNECTED`: trang đã ngắt kết nối thì tin nhắn của
        nó không còn là dữ liệu Havi được phép nhận.
        """
        result = await self._session.execute(
            select(PlatformConnection).where(
                PlatformConnection.platform == platform,
                PlatformConnection.external_account_id == external_account_id,
                PlatformConnection.status == ConnectionStatus.CONNECTED,
            )
        )
        return result.scalars().first()

    async def list_for_workspace(self, workspace_id: UUID) -> list[PlatformConnection]:
        result = await self._session.execute(
            select(PlatformConnection)
            .where(PlatformConnection.workspace_id == workspace_id)
            .order_by(PlatformConnection.platform)
        )
        return list(result.scalars().all())

    async def get_connected_channels(self, workspace_id: UUID) -> list[Channel]:
        """Lấy danh sách các Channel tương ứng với những nền tảng đang ở trạng thái CONNECTED.

        Nếu chưa kết nối nền tảng nào, trả về danh sách rỗng [].
        """
        connections = await self.list_for_workspace(workspace_id)
        connected: list[Channel] = []
        for conn in connections:
            if conn.status == ConnectionStatus.CONNECTED:
                channels = PLATFORM_TO_CHANNELS.get(conn.platform, [])
                for c in channels:
                    if c not in connected:
                        connected.append(c)
        return connected

    async def upsert(
        self,
        *,
        workspace_id: UUID,
        platform: Platform,
        access_token: str,
        refresh_token: str | None = None,
        expires_at: datetime | None = None,
        account_name: str | None = None,
        external_account_id: str | None = None,
        external_user_id: str | None = None,
        connected_by: UUID | None = None,
    ) -> PlatformConnection:
        """Nối kênh, hoặc nối lại kênh đã có.

        Cập nhật bản ghi cũ chứ không tạo bản thứ hai — unique constraint
        `(workspace_id, platform)` cũng không cho phép. Nối lại cũng xoá
        `failure_reason` và đưa status về `connected`: chủ tiệm vừa cấp quyền
        mới, giữ lại lý do hỏng cũ chỉ làm UI hiện cảnh báo sai.
        """
        existing = await self.get(workspace_id=workspace_id, platform=platform)
        encrypted = encrypt_token(access_token)
        encrypted_refresh = encrypt_token(refresh_token) if refresh_token else None

        if existing is not None:
            existing.access_token_encrypted = encrypted
            existing.refresh_token_encrypted = encrypted_refresh
            existing.expires_at = expires_at
            existing.account_name = account_name
            existing.external_account_id = external_account_id
            existing.external_user_id = external_user_id
            existing.connected_by = connected_by
            existing.status = ConnectionStatus.CONNECTED
            existing.failure_reason = None
            await self._session.flush()
            return existing

        connection = PlatformConnection(
            workspace_id=workspace_id,
            platform=platform,
            access_token_encrypted=encrypted,
            refresh_token_encrypted=encrypted_refresh,
            expires_at=expires_at,
            account_name=account_name,
            external_account_id=external_account_id,
            external_user_id=external_user_id,
            connected_by=connected_by,
            status=ConnectionStatus.CONNECTED,
        )
        self._session.add(connection)
        await self._session.flush()
        return connection

    def read_access_token(self, connection: PlatformConnection) -> str:
        """Giải mã token để đưa cho adapter.

        Không async vì không chạm DB — tách hẳn ra để chỗ gọi thấy rõ đây là
        lúc plaintext token tồn tại trong bộ nhớ.
        """
        return decrypt_token(connection.access_token_encrypted)

    def read_refresh_token(self, connection: PlatformConnection) -> str | None:
        """Giải mã refresh token nếu có."""
        if not connection.refresh_token_encrypted:
            return None
        return decrypt_token(connection.refresh_token_encrypted)

    async def mark_unusable(
        self,
        connection: PlatformConnection,
        *,
        status: ConnectionStatus,
        reason: str,
    ) -> PlatformConnection:
        """Đánh dấu kết nối không dùng được nữa (token hết hạn, bị gỡ quyền).

        Giữ lại bản ghi thay vì xoá: UI cần biết kênh nào từng nối và vì sao
        hỏng để hiện đúng nút "Nối lại" kèm lý do.
        """
        connection.status = status
        connection.failure_reason = reason[:500]
        await self._session.flush()
        return connection

    async def delete(self, connection: PlatformConnection) -> None:
        """Chủ tiệm chủ động ngắt kết nối — xoá hẳn cả token đã mã hoá."""
        await self._session.delete(connection)
        await self._session.flush()

    async def delete_by_external_user(self, *, platform: Platform, external_user_id: str) -> int:
        """Delete every credential granted by one provider-scoped user.

        Meta may call the deletion endpoint after the person has lost access to
        Havi, so this lookup intentionally has no workspace/user-session input.
        Its caller must authenticate the provider-signed request first.
        """
        result = await self._session.execute(
            select(PlatformConnection).where(
                PlatformConnection.platform == platform,
                PlatformConnection.external_user_id == external_user_id,
            )
        )
        rows = list(result.scalars().all())
        for row in rows:
            await self._session.delete(row)
        await self._session.flush()
        return len(rows)
