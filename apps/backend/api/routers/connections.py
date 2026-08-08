"""/connections/* — OAuth nền tảng.

Access/refresh token mã hoá bằng `TOKEN_ENCRYPTION_KEY` và KHÔNG BAO GIỜ nằm trong
response. Không được publish khi `status != connected`.

`/callback` là endpoint public duy nhất ở đây — Facebook điều hướng trình duyệt
tới, không kèm JWT. Danh tính đến từ `state` đã ký ở `/start`, xem
`core.oauth_state`.
"""

import logging

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import RedirectResponse

from api.deps import AuthDep, ConnectionServiceDep, WorkspaceDep
from application.services.connection_service import (
    ConnectionNotFound,
    PlatformNotConfigured,
    PlatformNotSupported,
)
from core.config import get_settings
from core.enums import Platform
from core.oauth_state import InvalidOAuthState
from core.schemas import OAuthStartResponse, PlatformConnection
from core.token_crypto import TokenEncryptionUnavailable

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/connections", tags=["connections"])


def _unsupported(exc: PlatformNotSupported) -> HTTPException:
    return HTTPException(
        status.HTTP_501_NOT_IMPLEMENTED, f"Chưa hỗ trợ nối {exc.platform.value}"
    )


def _not_configured() -> HTTPException:
    """503 chứ không 500: đây là lỗi vận hành (thiếu client id/secret hoặc khoá
    mã hoá), không phải lỗi của người dùng và không phải bug."""
    return HTTPException(
        status.HTTP_503_SERVICE_UNAVAILABLE,
        "Kênh này chưa được cấu hình trên hệ thống — chị báo Havi giúp em nhé",
    )


@router.get("", response_model=list[PlatformConnection])
async def list_connections(
    workspace_id: WorkspaceDep, connections: ConnectionServiceDep
) -> list[PlatformConnection]:
    """Bước 2 Onboarding + trang Cài đặt: chấm xanh/đỏ theo `status`."""
    return await connections.list_connections(workspace_id)


@router.post("/{platform}/start", response_model=OAuthStartResponse)
async def start_oauth(
    platform: Platform,
    auth: AuthDep,
    workspace_id: WorkspaceDep,
    connections: ConnectionServiceDep,
) -> OAuthStartResponse:
    """Trả URL màn hình cấp quyền của nền tảng, kèm `state` đã ký.

    Frontend điều hướng trình duyệt tới `authorization_url`. `state` sống 10
    phút — đủ để bấm qua màn hình Facebook, nhưng một link bị chụp lại thì hết
    hạn nhanh.
    """
    try:
        url, state = connections.start(
            workspace_id=workspace_id, user_id=auth.user_id, platform=platform
        )
    except PlatformNotSupported as exc:
        raise _unsupported(exc) from exc
    except PlatformNotConfigured as exc:
        raise _not_configured() from exc
    return OAuthStartResponse(authorization_url=url, state=state)


@router.get("/{platform}/callback", include_in_schema=False)
async def oauth_callback(
    platform: Platform,
    connections: ConnectionServiceDep,
    state: str | None = None,
    code: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
) -> RedirectResponse:
    """Nền tảng điều hướng về đây sau khi chủ tiệm bấm cấp quyền.

    Luôn redirect về web thay vì trả JSON: đây là điểm đến của trình duyệt, chủ
    tiệm phải thấy giao diện Havi chứ không phải một cục JSON.

    `error` có giá trị khi chủ tiệm bấm Huỷ ở màn hình Facebook — đó là lựa
    chọn hợp lệ, không phải lỗi hệ thống, nên đưa về UI với thông báo nhẹ nhàng.
    """
    web_base = get_settings().cors_origins[0] if get_settings().cors_origins else ""
    settings_url = f"{web_base}/onboarding"

    if error:
        # Không đưa `error_description` thô của nền tảng vào URL — nó là chuỗi
        # do bên thứ ba kiểm soát, đi thẳng vào trang của mình là mở đường cho
        # nội dung lạ hiển thị trên UI Havi.
        return RedirectResponse(
            f"{settings_url}?ket_noi=loi&ly_do=huy", status_code=302
        )

    # Thiếu `state` cũng phải xử như lỗi thường: đây là endpoint public, ai
    # cũng gọi được, và trả 422 vào mặt trình duyệt là hiện JSON thô cho chủ tiệm.
    if not code or not state:
        return RedirectResponse(
            f"{settings_url}?ket_noi=loi&ly_do=thieu_thong_tin", status_code=302
        )

    try:
        await connections.complete(platform=platform, code=code, state=state)
    except InvalidOAuthState:
        return RedirectResponse(
            f"{settings_url}?ket_noi=loi&ly_do=het_han", status_code=302
        )
    except (PlatformNotSupported, PlatformNotConfigured, TokenEncryptionUnavailable):
        return RedirectResponse(
            f"{settings_url}?ket_noi=loi&ly_do=chua_cau_hinh", status_code=302
        )
    except Exception:  # noqa: BLE001 — callback không được trả 500 vào mặt user
        logger.exception("OAuth callback %s lỗi ngoài dự kiến", platform.value)
        return RedirectResponse(
            f"{settings_url}?ket_noi=loi&ly_do=he_thong", status_code=302
        )

    return RedirectResponse(f"{settings_url}?ket_noi=ok", status_code=302)


@router.delete("/{platform}", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect(
    platform: Platform,
    auth: AuthDep,
    workspace_id: WorkspaceDep,
    connections: ConnectionServiceDep,
) -> None:
    """Chủ tiệm chủ động ngắt kênh — xoá hẳn cả token đã mã hoá."""
    del auth
    try:
        await connections.disconnect(workspace_id=workspace_id, platform=platform)
    except ConnectionNotFound as exc:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Kênh này chưa được nối"
        ) from exc
