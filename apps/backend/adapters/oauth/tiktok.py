"""TikTok OAuth Client — đổi `code` lấy Access Token của TikTok Account.

Triển khai `OAuthClientPort` theo chuẩn TikTok Login Kit v2:
1. `authorization_url`: redirect người dùng tới màn hình xin cấp quyền của TikTok.
2. `exchange_code`: POST tới `https://open.tiktokapis.com/v2/oauth/token/` kèm
   client_key & client_secret để lấy access_token + refresh_token.
"""

import base64
import hashlib
import hmac
import logging
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

import httpx

from adapters.oauth.base import (
    OAuthAccount,
    OAuthClientPort,
    OAuthPermanentError,
    OAuthTemporaryError,
)
from core.config import Settings
from core.enums import Platform

logger = logging.getLogger(__name__)

TIKTOK_AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"
TIKTOK_TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"

#: Quyền Havi xin ở TikTok. `video.upload` chứ không phải `video.publish`: app
#: chưa qua audit chỉ được đẩy clip vào Hộp thư để chủ tài khoản tự bấm đăng
#: (xem ROADMAP Phase C). Xin quyền chưa được cấp thì TikTok từ chối cả lượt uỷ
#: quyền, nên đây không phải chỗ để "xin thêm cho chắc".
#:
#: Phải khớp với `_REQUIREMENTS[Platform.TIKTOK]` trong
#: `domain/policies/connection_capabilities.py` — hai chỗ lệch nhau là kênh nối
#: xong mà Havi tự coi là không đăng được.
TIKTOK_SCOPES: tuple[str, ...] = ("user.info.basic", "video.upload")
_TRANSIENT_STATUSES = frozenset({408, 429, 500, 502, 503, 504})


def _get_pkce_verifier(state: str, secret: str) -> str:
    """Tạo deterministic code_verifier từ HMAC(secret, state)."""
    h = hmac.new(secret.encode("utf-8"), state.encode("utf-8"), hashlib.sha256).digest()
    b64 = base64.urlsafe_b64encode(h).decode("utf-8").rstrip("=")
    return (b64 * 3)[:64]


def _get_pkce_challenge(verifier: str) -> str:
    """Tạo S256 code_challenge từ code_verifier."""
    sha256_hash = hashlib.sha256(verifier.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(sha256_hash).decode("utf-8").rstrip("=")


class TikTokOAuthClient(OAuthClientPort):
    def __init__(self, settings: Settings, *, timeout_seconds: float = 20.0) -> None:
        self._settings = settings
        self._client_key = getattr(settings, "tiktok_client_key", "")
        self._client_secret = getattr(settings, "tiktok_client_secret", "")
        self._redirect_uri = getattr(
            settings,
            "tiktok_redirect_uri",
            "http://localhost:8000/connections/tiktok/callback",
        )
        self._timeout = timeout_seconds

    @property
    def platform(self) -> Platform:
        return Platform.TIKTOK

    @property
    def is_configured(self) -> bool:
        if bool(self._client_key and self._client_secret):
            return True
        return self._settings.use_fake_publisher or self._settings.env == "local"

    def authorization_url(self, *, state: str) -> str:
        if not (self._client_key and self._client_secret):
            # In local dev / fake mode, return mock callback URL
            return f"http://localhost:8000/connections/tiktok/callback?code=mock_tiktok_code&state={state}"

        verifier = _get_pkce_verifier(state, self._client_secret)
        challenge = _get_pkce_challenge(verifier)

        params = {
            "client_key": self._client_key,
            "scope": ",".join(TIKTOK_SCOPES),
            "response_type": "code",
            "redirect_uri": self._redirect_uri,
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
        return f"{TIKTOK_AUTH_URL}?" + urlencode(params)

    async def exchange_code(self, code: str, *, state: str | None = None) -> OAuthAccount:
        if not self.is_configured:
            raise OAuthPermanentError(
                self.platform, "TikTok OAuth chưa được cấu hình client_key / secret"
            )

        if code == "mock_tiktok_code" or not (self._client_key and self._client_secret):
            return OAuthAccount(
                external_account_id="tiktok_mock_user_123",
                account_name="TikTok @tiem_demo",
                access_token="mock_tiktok_access_token",
                refresh_token="mock_tiktok_refresh_token",
                expires_at=datetime.now(UTC) + timedelta(days=30),
                # Khớp `TIKTOK_SCOPES` để luồng mock ở local đi qua đúng nhánh
                # capability như luồng thật. Thiếu dòng này thì local luôn rơi vào
                # `granted_scopes=None` và không bao giờ chạm tới lỗi thiếu quyền.
                granted_scopes=("user.info.basic", "video.upload"),
            )

        payload = {
            "client_key": self._client_key,
            "client_secret": self._client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self._redirect_uri,
        }
        if state and self._client_secret:
            payload["code_verifier"] = _get_pkce_verifier(state, self._client_secret)
        elif self._client_secret:
            payload["code_verifier"] = _get_pkce_verifier("default", self._client_secret)
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                response = await client.post(TIKTOK_TOKEN_URL, data=payload, headers=headers)
            except httpx.RequestError as exc:
                msg = f"Lỗi mạng kết nối TikTok OAuth: {exc}"
                raise OAuthTemporaryError(self.platform, msg) from exc

        if response.status_code in _TRANSIENT_STATUSES:
            raise OAuthTemporaryError(self.platform, f"TikTok OAuth HTTP {response.status_code}")
        if response.status_code != 200:
            msg = f"TikTok OAuth từ chối (HTTP {response.status_code})"
            raise OAuthPermanentError(self.platform, msg)

        try:
            data = response.json()
        except ValueError as exc:
            msg = "TikTok OAuth trả dữ liệu không phải JSON"
            raise OAuthTemporaryError(self.platform, msg) from exc

        data_body = data.get("data") if isinstance(data.get("data"), dict) else data
        access_token = data_body.get("access_token") or data.get("access_token")
        if not access_token:
            err_msg = (
                data.get("error_description")
                or data.get("message")
                or data.get("description")
                or f"Không có access_token trong response: {data}"
            )
            raise OAuthPermanentError(self.platform, f"TikTok OAuth lỗi: {err_msg}")

        open_id = data_body.get("open_id") or data.get("open_id") or "tiktok_user"
        expires_in = data_body.get("expires_in") or data.get("expires_in") or 86400
        refresh_token = data_body.get("refresh_token") or data.get("refresh_token")

        # Quyền TikTok *thực sự* cấp, không phải quyền Havi đã hỏi. Người dùng bỏ
        # tick được từng mục ở màn hình uỷ quyền, nên hai thứ có thể khác nhau.
        #
        # `domain/policies/connection_capabilities.py` đọc giá trị này để quyết
        # định TikTok có đăng được không. Không ghi thì `granted_scopes` là None
        # = "kết nối cũ, không rõ" và Havi cho đăng theo diện nghi ngờ có lợi —
        # tức lỗi thiếu quyền chỉ lộ ra khi bài đã lỗi, không lộ lúc nối kênh.
        #
        # TikTok trả chuỗi phân tách bằng dấu phẩy; chuẩn OAuth2 dùng khoảng
        # trắng. Chấp cả hai vì không có gì bảo đảm TikTok giữ nguyên định dạng.
        raw_scope = data_body.get("scope") or data.get("scope") or ""
        granted_scopes = tuple(
            sorted({part for part in raw_scope.replace(",", " ").split() if part})
        )

        account_name = f"TikTok @{open_id[:10]}"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as user_client:
                user_info_resp = await user_client.get(
                    "https://open.tiktokapis.com/v2/user/info/?fields=open_id,union_id,avatar_url,display_name",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                if user_info_resp.status_code == 200:
                    user_data = (user_info_resp.json().get("data") or {}).get("user") or {}
                    display_name = user_data.get("display_name")
                    username = user_data.get("username")
                    if display_name:
                        # Trước đây chỗ này ghép cứng "(@huynhnguyen333)" cho mọi
                        # display_name có chứa "huynh" — handle riêng của một
                        # người lọt vào code. Bất kỳ chủ tiệm tên Huynh/Huỳnh
                        # cũng bị gắn handle của người khác vào tên kênh.
                        account_name = display_name
                    elif username:
                        account_name = f"@{username}"
        except Exception:
            logger.warning("Không thể lấy chi tiết profile TikTok, dùng fallback open_id")

        return OAuthAccount(
            external_account_id=open_id,
            account_name=account_name,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=datetime.now(UTC) + timedelta(seconds=expires_in),
            granted_scopes=granted_scopes,
        )

    async def refresh_access_token(self, refresh_token: str) -> OAuthAccount:
        """Làm mới access_token bằng refresh_token theo TikTok OAuth v2 spec.

        POST https://open.tiktokapis.com/v2/oauth/token/
        grant_type=refresh_token
        """
        if not self.is_configured:
            raise OAuthPermanentError(
                self.platform, "TikTok OAuth chưa được cấu hình client_key / secret"
            )

        if not (self._client_key and self._client_secret) or refresh_token == "mock_tiktok_refresh_token":
            return OAuthAccount(
                external_account_id="tiktok_mock_user_123",
                account_name="TikTok @tiem_demo",
                access_token="mock_refreshed_tiktok_access_token",
                refresh_token="mock_refreshed_tiktok_refresh_token",
                expires_at=datetime.now(UTC) + timedelta(days=30),
                granted_scopes=("user.info.basic", "video.upload"),
            )

        payload = {
            "client_key": self._client_key,
            "client_secret": self._client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                response = await client.post(TIKTOK_TOKEN_URL, data=payload, headers=headers)
            except httpx.RequestError as exc:
                raise OAuthTemporaryError(
                    self.platform, f"Lỗi mạng refresh TikTok token: {exc}"
                ) from exc

        if response.status_code in _TRANSIENT_STATUSES:
            raise OAuthTemporaryError(
                self.platform, f"TikTok OAuth HTTP {response.status_code}"
            )
        if response.status_code != 200:
            raise OAuthPermanentError(
                self.platform,
                f"TikTok từ chối refresh token (HTTP {response.status_code})",
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise OAuthTemporaryError(
                self.platform, "TikTok OAuth trả dữ liệu không phải JSON"
            ) from exc

        data_body = data.get("data") if isinstance(data.get("data"), dict) else data
        new_access_token = data_body.get("access_token")
        new_refresh_token = data_body.get("refresh_token") or refresh_token
        expires_in = data_body.get("expires_in") or 86400
        open_id = data_body.get("open_id") or "tiktok_user"

        if not new_access_token:
            raise OAuthPermanentError(
                self.platform, "Không nhận được access_token mới khi refresh TikTok"
            )

        raw_scope = data_body.get("scope") or ""
        granted_scopes = tuple(
            sorted({part for part in raw_scope.replace(",", " ").split() if part})
        )

        return OAuthAccount(
            external_account_id=open_id,
            account_name=f"TikTok @{open_id[:10]}",
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            expires_at=datetime.now(UTC) + timedelta(seconds=expires_in),
            granted_scopes=granted_scopes or ("user.info.basic", "video.upload"),
        )
