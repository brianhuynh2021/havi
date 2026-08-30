"""/connections/* — OAuth nền tảng.

Access/refresh token mã hoá bằng `TOKEN_ENCRYPTION_KEY` và KHÔNG BAO GIỜ nằm trong
response. Không được publish khi `status != connected`.

`/callback` là endpoint public duy nhất ở đây — Facebook điều hướng trình duyệt
tới, không kèm JWT. Danh tính đến từ `state` đã ký ở `/start`, xem
`core.oauth_state`.
"""

import base64
import hashlib
import hmac
import json
import logging
import uuid
from urllib.parse import parse_qs, quote

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse

from adapters.oauth.base import OAuthPermanentError, OAuthTemporaryError
from adapters.persistence.connection_repository import ConnectionRepository
from adapters.persistence.db import DbSessionDep
from api.deps import AuthDep, ConnectionServiceDep, WorkspaceDep
from application.services.connection_service import (
    ConnectionNotFound,
    PlatformNotConfigured,
    PlatformNotSupported,
)
from core.config import get_settings
from core.enums import OAuthReturnTarget, Platform
from core.oauth_state import InvalidOAuthState
from core.schemas import OAuthStartResponse, PlatformConnection
from core.token_crypto import TokenEncryptionUnavailable
from domain.policies.plan_limits import PlanLimitExceeded

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/connections", tags=["connections"])


def _unsupported(exc: PlatformNotSupported) -> HTTPException:
    return HTTPException(status.HTTP_501_NOT_IMPLEMENTED, f"Chưa hỗ trợ nối {exc.platform.value}")


def _not_configured() -> HTTPException:
    """503 chứ không 500: đây là lỗi vận hành (thiếu client id/secret hoặc khoá
    mã hoá), không phải lỗi của người dùng và không phải bug."""
    return HTTPException(
        status.HTTP_503_SERVICE_UNAVAILABLE,
        "Kênh này chưa được cấu hình trên hệ thống — bạn báo Havi giúp nhé",
    )


@router.get("", response_model=list[PlatformConnection])
async def list_connections(
    workspace_id: WorkspaceDep, connections: ConnectionServiceDep
) -> list[PlatformConnection]:
    """Bước 2 Onboarding + trang Cài đặt: chấm xanh/đỏ theo `status`."""
    return await connections.list_connections(workspace_id)


#: Ràng buộc nội dung của từng nền tảng. Chỉ là dữ liệu mô tả — nền tảng nào
#: thực sự nối được thì do `ConnectionService` quyết, xem `list_capabilities`.
PLATFORM_CAPABILITIES: dict[Platform, dict] = {
    Platform.FACEBOOK: {
        "name": "Facebook Page",
        "supported_media": ["image", "video"],
        "max_text_length": 63206,
        "supported_features": [
            "feed_posts",
            "photo_attachments",
            "data_deletion_callback",
        ],
    },
    Platform.ZALO_OA: {
        "name": "Zalo Official Account",
        "supported_media": ["image"],
        "max_text_length": 2000,
        "supported_features": ["paragraph_messages", "broadcast_care"],
    },
    Platform.TIKTOK: {
        "name": "TikTok Account",
        "supported_media": ["video"],
        "max_text_length": 4000,
        "supported_features": ["short_form_video", "direct_post"],
    },
    Platform.YOUTUBE: {
        "name": "YouTube Channel",
        "supported_media": ["video"],
        "max_text_length": 5000,
        "supported_features": ["shorts_video", "video_upload"],
    },
    Platform.GOOGLE_BUSINESS: {
        "name": "Google Business Profile",
        "supported_media": ["image"],
        "max_text_length": 1500,
        "supported_features": ["local_posts", "call_to_action_buttons"],
    },
}


@router.get("/capabilities")
async def list_capabilities(connections: ConnectionServiceDep) -> dict:
    """Các kênh Havi thực sự nối được, kèm ràng buộc nội dung của từng kênh.

    Danh sách suy ra từ OAuth client đã đăng ký chứ không viết tay. Bản viết tay
    trước đó quảng cáo Google Business trong khi `_oauth_clients()` không có
    client nào cho nó — onboarding hiện kênh, chủ tiệm bấm nối, và nhận 501.
    Danh sách tự suy thì thêm publisher mà quên OAuth sẽ không lộ ra ngoài được.
    """
    return {
        "platforms": [
            {"platform": platform.value, **PLATFORM_CAPABILITIES[platform]}
            for platform in connections.supported_platforms()
            if platform in PLATFORM_CAPABILITIES
        ]
    }


@router.post("/{platform}/start", response_model=OAuthStartResponse)
async def start_oauth(
    platform: Platform,
    auth: AuthDep,
    workspace_id: WorkspaceDep,
    connections: ConnectionServiceDep,
    tro_ve: OAuthReturnTarget = OAuthReturnTarget.ONBOARDING,
) -> OAuthStartResponse:
    """Trả URL màn hình cấp quyền của nền tảng, kèm `state` đã ký.

    Frontend điều hướng trình duyệt tới `authorization_url`. `state` sống 10
    phút — đủ để bấm qua màn hình Facebook, nhưng một link bị chụp lại thì hết
    hạn nhanh.

    `tro_ve` nói nơi đưa người dùng về sau khi cấp quyền xong (onboarding hay
    Cài đặt). Là enum chứ không phải URL: enum thì giá trị lạ bị FastAPI chặn ở
    422, còn nhận URL là mở đường cho open redirect.
    """
    try:
        url, state = connections.start(
            workspace_id=workspace_id,
            user_id=auth.user_id,
            platform=platform,
            return_key=tro_ve.value,
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
    settings = get_settings()
    web_base = settings.web_base_url

    # Đường về nằm trong state đã ký (`return_key`), không phải hằng số:
    # chủ tiệm bấm "Nối lại" từ trang Cài đặt phải quay về Cài đặt. Hardcode
    # `/onboarding` là đá người đã dùng app hàng tháng vào lại wizard onboarding.
    # State thiếu/hỏng thì `return_path_for` trả mặc định, không ném.
    return_path = connections.return_path_for(state, platform=platform) if state else "/onboarding"
    return_url = f"{web_base}{return_path}"

    if error:
        # Không đưa `error_description` thô của nền tảng vào URL — nó là chuỗi
        # do bên thứ ba kiểm soát, đi thẳng vào trang của mình là mở đường cho
        # nội dung lạ hiển thị trên UI Havi.
        return RedirectResponse(f"{return_url}?ket_noi=loi&ly_do=huy", status_code=302)

    # Thiếu `state` cũng phải xử như lỗi thường: đây là endpoint public, ai
    # cũng gọi được, và trả 422 vào mặt trình duyệt là hiện JSON thô cho chủ tiệm.
    if not code or not state:
        return RedirectResponse(f"{return_url}?ket_noi=loi&ly_do=thieu_thong_tin", status_code=302)

    try:
        await connections.complete(platform=platform, code=code, state=state)
    except InvalidOAuthState:
        return RedirectResponse(f"{return_url}?ket_noi=loi&ly_do=het_han", status_code=302)
    except (PlatformNotSupported, PlatformNotConfigured, TokenEncryptionUnavailable):
        return RedirectResponse(f"{return_url}?ket_noi=loi&ly_do=chua_cau_hinh", status_code=302)
    except PlanLimitExceeded:
        # Đụng trần kênh của gói. Lý do riêng chứ không gộp vào `he_thong`: người
        # dùng vừa bấm cho phép trên Facebook xong, nên câu "lỗi hệ thống" sẽ đẩy
        # họ đi thử lại mãi trong khi việc cần làm là nâng gói.
        return RedirectResponse(f"{return_url}?ket_noi=loi&ly_do=het_han_muc", status_code=302)
    except OAuthTemporaryError as exc:
        # Nền tảng lỗi tạm — bấm nối lại là được, nên nói đúng như vậy.
        logger.warning("OAuth %s tạm lỗi: %s", platform.value, exc.detail)
        return RedirectResponse(f"{return_url}?ket_noi=loi&ly_do=tam_loi", status_code=302)
    except OAuthPermanentError as exc:
        # Thiếu quyền, không có Page, code hỏng... Adapter đã soạn sẵn câu tiếng
        # Việt nói rõ phải làm gì; gộp vào `he_thong` là ném đi thông tin đó và
        # để chủ tiệm bấm lại mãi mà không biết vì sao.
        logger.warning("OAuth %s bị từ chối: %s", platform.value, exc.detail)
        return RedirectResponse(
            f"{return_url}?ket_noi=loi&ly_do=tu_choi&chi_tiet={quote(exc.detail[:200])}",
            status_code=302,
        )
    except Exception:  # noqa: BLE001 — callback không được trả 500 vào mặt user
        logger.exception("OAuth callback %s unexpected error", platform.value)
        return RedirectResponse(f"{return_url}?ket_noi=loi&ly_do=he_thong", status_code=302)

    return RedirectResponse(f"{return_url}?ket_noi=ok", status_code=302)


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
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Kênh này chưa được nối") from exc


def _facebook_deletion_user_id(*, signed_request: str, app_secret: str) -> str:
    """Verify Meta's HMAC-SHA256 signed request and return its app-scoped user ID."""
    try:
        encoded_signature, encoded_payload = signed_request.split(".", 1)
        signature = base64.urlsafe_b64decode(
            encoded_signature + "=" * (-len(encoded_signature) % 4)
        )
        expected = hmac.new(
            app_secret.encode("utf-8"),
            encoded_payload.encode("ascii"),
            hashlib.sha256,
        ).digest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError("invalid signature")

        payload = base64.urlsafe_b64decode(encoded_payload + "=" * (-len(encoded_payload) % 4))
        data = json.loads(payload.decode("utf-8"))
    except (ValueError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid signed request") from exc

    if str(data.get("algorithm") or "").upper() != "HMAC-SHA256":
        raise ValueError("unsupported signed request algorithm")
    user_id = data.get("user_id")
    if not user_id:
        raise ValueError("signed request has no user_id")
    return str(user_id)


@router.post("/facebook/data-deletion", include_in_schema=False)
async def facebook_data_deletion(request: Request, session: DbSessionDep) -> JSONResponse:
    """Callback xử lý yêu cầu xóa dữ liệu từ Facebook (Meta Data Deletion Request).

    Meta yêu cầu endpoint trả URL hướng dẫn/xác nhận xóa kèm `confirmation_code`.
    """
    settings = get_settings()
    if not settings.facebook_client_secret:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Facebook Data Deletion chưa được cấu hình",
        )
    body = (await request.body()).decode("utf-8", errors="replace")
    signed_request = (parse_qs(body, max_num_fields=10).get("signed_request") or [None])[0]
    if not signed_request:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Thiếu signed_request của Meta",
        )

    try:
        external_user_id = _facebook_deletion_user_id(
            signed_request=signed_request,
            app_secret=settings.facebook_client_secret,
        )
    except ValueError as exc:
        # Không trả chi tiết chữ ký/payload: callback public và dữ liệu đó không
        # cần xuất hiện trong response hay log.
        logger.warning("facebook_data_deletion.invalid_signed_request")
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "signed_request không hợp lệ",
        ) from exc

    deleted = await ConnectionRepository(session).delete_by_external_user(
        platform=Platform.FACEBOOK,
        external_user_id=external_user_id,
    )
    confirmation_code = f"del_{uuid.uuid4().hex[:12]}"
    logger.info(
        "facebook_data_deletion.completed connections=%s confirmation=%s",
        deleted,
        confirmation_code,
    )

    status_url = f"{settings.web_base_url}/data-deletion?confirmation_code={confirmation_code}"
    return JSONResponse(
        content={
            "url": status_url,
            "confirmation_code": confirmation_code,
        }
    )
