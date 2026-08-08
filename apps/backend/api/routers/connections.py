"""/connections/* — OAuth nền tảng.

Access/refresh token mã hoá bằng `TOKEN_ENCRYPTION_KEY` và KHÔNG BAO GIỜ nằm trong
response. Không được publish khi `status != connected`.

Hai endpoint ở đây khác nhau về bản chất, đừng nhầm:

- `/start` là **API call** từ frontend đang đăng nhập → trả JSON có URL để
  frontend tự điều hướng.
- `/callback` là **điều hướng trình duyệt** do Facebook gọi tới, không có JWT →
  trả 302 về app. Trả JSON ở đây thì chủ tiệm nhìn thấy một trang chữ thô sau
  khi bấm cấp quyền.
"""

import logging
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import RedirectResponse

from api.deps import AuthDep, ConnectionServiceDep, SettingsDep, WorkspaceDep
from application.services.connection_service import (
    ConnectionNotFound,
    InvalidOAuthState,
    NotWorkspaceMember,
    OAuthError,
    PlatformNotConfigured,
    PlatformNotSupported,
    TokenEncryptionUnavailable,
)
from core.enums import Platform
from core.schemas import OAuthStartResponse, PlatformConnection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/connections", tags=["connections"])


@router.get("", response_model=list[PlatformConnection])
async def list_connections(
    workspace_id: WorkspaceDep, connections: ConnectionServiceDep
) -> list[PlatformConnection]:
    """Bước 2 Onboarding + trang Cài đặt: chấm xanh/đỏ theo `status`.

    Chỉ trả kênh đã thật sự nối. Kênh chưa nối vắng mặt khỏi danh sách chứ
    không trả về kèm status giả — UI không được hiện TikTok/Zalo là "đã nối"
    khi đó chỉ là fixture.
    """
    return await connections.list_connections(workspace_id)


@router.post("/{platform}/start", response_model=OAuthStartResponse)
def start_oauth(
    platform: Platform,
    auth: AuthDep,
    workspace_id: WorkspaceDep,
    connections: ConnectionServiceDep,
) -> OAuthStartResponse:
    """Phát URL cấp quyền kèm `state` đã ký.

    Trả `state` về cho frontend để nó đối chiếu khi người dùng quay lại — lớp
    kiểm tra thứ hai bên cạnh chữ ký mà backend tự verify ở `/callback`.
    """
    try:
        url, state = connections.start(
            workspace_id=workspace_id, user_id=auth.user_id, platform=platform
        )
    except PlatformNotSupported as exc:
        raise HTTPException(
            status.HTTP_501_NOT_IMPLEMENTED, f"Chưa hỗ trợ nối {platform.value}"
        ) from exc
    except PlatformNotConfigured as exc:
        # Lỗi vận hành (thiếu env), không phải lỗi người dùng. 503 để phân biệt
        # với 501 "tính năng chưa làm" — hai thứ này cần hai hành động khác nhau.
        logger.error("Thiếu cấu hình OAuth cho %s", platform.value)
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Chức năng nối kênh đang tạm ngưng — em báo kỹ thuật xử lý ngay",
        ) from exc
    return OAuthStartResponse(authorization_url=url, state=state)


@router.get("/{platform}/callback", include_in_schema=False)
async def oauth_callback(
    platform: Platform,
    settings: SettingsDep,
    connections: ConnectionServiceDep,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
) -> RedirectResponse:
    """Facebook điều hướng về đây sau màn hình cấp quyền.

    `code`/`state` optional vì khi chủ tiệm bấm "Huỷ", Facebook gọi lại đúng URL
    này với `error=access_denied` và KHÔNG có `code`. Khai báo bắt buộc thì
    FastAPI trả 422 JSON và chủ tiệm mắc kẹt ở một trang lỗi thô.

    Luôn trả 302 về app — kể cả khi hỏng, kèm `?ket_noi=loi&ly_do=...` để UI nói
    được chuyện gì đã xảy ra. `include_in_schema=False` vì đây không phải
    endpoint frontend gọi, để nó khỏi lọt vào TypeScript client.
    """
    if error or not code or not state:
        # `access_denied` là người dùng tự bấm Huỷ — không phải lỗi hệ thống,
        # không log ở mức error.
        reason = error_description or error or "Thiếu mã xác thực từ nền tảng"
        return _back_to_app(settings, ok=False, reason=reason)

    try:
        connection = await connections.complete(platform=platform, code=code, state=state)
    except InvalidOAuthState as exc:
        # State hỏng/hết hạn/lệch platform — có thể là CSRF thật. Log để đếm.
        logger.warning("OAuth state không hợp lệ cho %s: %s", platform.value, exc)
        return _back_to_app(settings, ok=False, reason=str(exc))
    except NotWorkspaceMember as exc:
        return _back_to_app(settings, ok=False, reason=str(exc))
    except PlatformNotSupported:
        return _back_to_app(settings, ok=False, reason=f"Chưa hỗ trợ nối {platform.value}")
    except PlatformNotConfigured:
        logger.error("Thiếu cấu hình OAuth cho %s", platform.value)
        return _back_to_app(
            settings, ok=False, reason="Chức năng nối kênh đang tạm ngưng"
        )
    except TokenEncryptionUnavailable:
        # Thà không nối được còn hơn lưu token trần vào DB.
        logger.error("Chưa cấu hình TOKEN_ENCRYPTION_KEY — không lưu được token nền tảng")
        return _back_to_app(
            settings, ok=False, reason="Hệ thống chưa sẵn sàng lưu kết nối an toàn"
        )
    except OAuthError as exc:
        # `exc.detail` đã được adapter lọc sạch — không chứa token hay secret.
        logger.warning("Nối %s thất bại: %s", platform.value, exc.detail)
        return _back_to_app(settings, ok=False, reason=exc.detail)

    return _back_to_app(
        settings, ok=True, platform=platform, account_name=connection.account_name
    )


@router.delete("/{platform}", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect(
    platform: Platform, workspace_id: WorkspaceDep, connections: ConnectionServiceDep
) -> None:
    """Ngắt kênh — xoá hẳn bản ghi kèm token đã mã hoá.

    Bài đang `scheduled` trên kênh này sẽ hỏng ở bước publish với
    `AUTH_PERMISSION` (`PublishService.run_job` kiểm tra connection trước khi
    gọi adapter) và không retry vô ích. Cố ý không tự huỷ lịch ở đây: chủ tiệm
    nối lại kênh trong ngày thì bài vẫn đăng đúng như đã duyệt.
    """
    try:
        await connections.disconnect(workspace_id=workspace_id, platform=platform)
    except ConnectionNotFound as exc:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"Chưa nối kênh {platform.value}"
        ) from exc


def _back_to_app(
    settings: SettingsDep,
    *,
    ok: bool,
    platform: Platform | None = None,
    account_name: str | None = None,
    reason: str | None = None,
) -> RedirectResponse:
    """302 về frontend kèm kết quả trên query string.

    303 chứ không 302 sẽ đúng chuẩn hơn, nhưng callback này là GET nên 302 giữ
    nguyên method — không có khác biệt thực tế.
    """
    params: dict[str, str] = {"ket_noi": "ok" if ok else "loi"}
    if platform is not None:
        params["kenh"] = platform.value
    if account_name:
        params["trang"] = account_name
    if reason:
        # Cắt ngắn: query string quá dài bị một số proxy chặn, và UI cũng không
        # hiển thị nổi cả đoạn.
        params["ly_do"] = reason[:200]
    return RedirectResponse(
        url=f"{settings.oauth_success_redirect_url}?{urlencode(params)}",
        status_code=status.HTTP_302_FOUND,
    )
