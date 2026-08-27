"""Signed state cho OAuth — chống CSRF ở bước callback.

Vấn đề: `/connections/{platform}/callback` là endpoint public (nền tảng gọi
tới, không kèm JWT của user). Không có gì chứng minh callback này thuộc về
đúng người đã bấm "Nối kênh" — kẻ tấn công dụ chủ tiệm mở một callback URL với
`code` của *tài khoản Facebook của kẻ tấn công* thì tiệm bị nối nhầm vào Page
của kẻ đó, và mọi bài sau đó đăng lên trang sai.

Cách chặn: bước `/start` phát một `state` đã ký chứa workspace_id + user_id +
platform. Callback chỉ được chấp nhận khi chữ ký hợp lệ và chưa hết hạn. Vì
state được ký chứ không tra DB, không cần bảng phụ và không có gì để dọn rác.

TTL ngắn (10 phút): đủ cho người dùng bấm qua màn hình cấp quyền của Facebook,
nhưng một link callback bị chụp lại thì hết hạn nhanh.

`nonce` để hai lần bấm "Nối kênh" liên tiếp không sinh ra state giống hệt nhau
— tránh việc log trung gian lộ ra là cùng một phiên.
"""

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt

from core.config import Settings
from core.enums import Platform

STATE_TTL_MINUTES = 10

#: Đánh dấu token này là OAuth state, không phải access token. Không có nó thì
#: một access token hợp lệ cũng lọt qua chỗ kiểm tra state — cùng khoá ký.
_STATE_AUDIENCE = "havi:oauth-state"


class InvalidOAuthState(Exception):
    """State sai chữ ký, hết hạn, hoặc không khớp platform đang callback."""


#: Nơi đưa người dùng về sau callback, theo *khoá* chứ không theo URL.
#:
#: Cố ý không nhận URL từ client — kể cả URL đã ký. Nhận URL là mở đường cho
#: open redirect: chỉ cần một lần khoá ký bị lộ, hoặc một chỗ nào đó quên kiểm,
#: là callback của Havi đẩy chủ tiệm sang domain của kẻ tấn công với vẻ ngoài
#: hợp lệ. Khoá tra trong dict cố định thì giá trị lạ chỉ rơi về mặc định.
RETURN_PATHS: dict[str, str] = {
    "onboarding": "/onboarding",
    "settings": "/cai-dat",
}

DEFAULT_RETURN_KEY = "onboarding"


@dataclass(frozen=True)
class OAuthStatePayload:
    workspace_id: UUID
    user_id: UUID
    platform: Platform
    #: Khoá trong `RETURN_PATHS`. Chủ tiệm nối lại kênh từ Cài đặt phải quay về
    #: Cài đặt — đá họ vào wizard onboarding là bắt làm lại một luồng đã xong.
    return_key: str = DEFAULT_RETURN_KEY

    @property
    def return_path(self) -> str:
        return RETURN_PATHS.get(self.return_key, RETURN_PATHS[DEFAULT_RETURN_KEY])


def create_oauth_state(
    *,
    workspace_id: UUID,
    user_id: UUID,
    platform: Platform,
    settings: Settings,
    return_key: str = DEFAULT_RETURN_KEY,
) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "aud": _STATE_AUDIENCE,
            "ws": str(workspace_id),
            "sub": str(user_id),
            "plt": platform.value,
            # Chuẩn hoá ngay lúc ký: khoá lạ thành mặc định, nên không có đường
            # nào để một giá trị không nằm trong allow-list sống tới callback.
            "ret": return_key if return_key in RETURN_PATHS else DEFAULT_RETURN_KEY,
            "nonce": secrets.token_urlsafe(8),
            "iat": now,
            "exp": now + timedelta(minutes=STATE_TTL_MINUTES),
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def verify_oauth_state(state: str, *, platform: Platform, settings: Settings) -> OAuthStatePayload:
    """Giải mã và kiểm tra state.

    `platform` truyền vào là platform trên URL callback — phải khớp với platform
    đã ký trong state. Không kiểm tra chỗ này thì một state phát cho Facebook
    dùng lại được ở callback Zalo.
    """
    try:
        claims = jwt.decode(
            state,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            audience=_STATE_AUDIENCE,
        )
    except jwt.ExpiredSignatureError as exc:
        raise InvalidOAuthState(
            "Phiên nối kênh đã hết hạn — bạn bấm nối lại từ đầu nhé"
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise InvalidOAuthState("Yêu cầu nối kênh không hợp lệ") from exc

    if claims.get("plt") != platform.value:
        raise InvalidOAuthState("Yêu cầu nối kênh không khớp nền tảng")

    try:
        return OAuthStatePayload(
            workspace_id=UUID(claims["ws"]),
            user_id=UUID(claims["sub"]),
            platform=platform,
            # State cũ (ký trước khi có `ret`) vẫn giải mã được, về mặc định.
            # Không ném lỗi: state sống 10 phút, nên lúc deploy vẫn còn state cũ
            # đang bay — làm chúng hỏng là chủ tiệm đang nối kênh bị đá ra.
            return_key=claims.get("ret", DEFAULT_RETURN_KEY),
        )
    except (KeyError, ValueError) as exc:
        raise InvalidOAuthState("Yêu cầu nối kênh không hợp lệ") from exc
