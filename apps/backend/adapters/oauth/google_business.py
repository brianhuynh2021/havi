"""Google Business Profile OAuth Client — đổi `code` lấy Access Token cho Google Business / Google Maps.

Triển khai `OAuthClientPort` theo chuẩn Google OAuth 2.0:
1. `authorization_url`: redirect tới màn hình cấp quyền Google với scope `business.manage`.
2. `exchange_code`: POST tới `https://oauth2.googleapis.com/token`.
"""

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

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
# Business Profile tách làm nhiều API con; `mybusiness.googleapis.com/v4` chỉ
# còn giữ localPosts, còn danh sách tài khoản và địa điểm nằm ở hai host riêng.
GOOGLE_ACCOUNTS_URL = "https://mybusinessaccountmanagement.googleapis.com/v1/accounts"
GOOGLE_LOCATIONS_URL = "https://mybusinessbusinessinformation.googleapis.com/v1"
_TRANSIENT_STATUSES = frozenset({408, 429, 500, 502, 503, 504})


class GoogleBusinessOAuthClient(OAuthClientPort):
    def __init__(self, settings: Settings, *, timeout_seconds: float = 20.0) -> None:
        self._settings = settings
        self._client_id = settings.google_client_id
        self._client_secret = settings.google_client_secret
        self._redirect_uri = getattr(
            settings,
            "google_business_redirect_uri",
            "http://localhost:8000/connections/google_business/callback",
        )
        self._timeout = timeout_seconds

    @property
    def platform(self) -> Platform:
        return Platform.GOOGLE_BUSINESS

    @property
    def is_configured(self) -> bool:
        if bool(self._client_id and self._client_secret):
            return True
        return self._settings.use_fake_publisher or self._settings.env == "local"

    def authorization_url(self, *, state: str) -> str:
        if not (self._client_id and self._client_secret):
            # In local dev / fake mode, return mock callback URL
            return (
                f"http://localhost:8000/connections/google_business/callback"
                f"?code=mock_google_business_code&state={state}"
            )
        params = {
            "client_id": self._client_id,
            "scope": (
                "https://www.googleapis.com/auth/business.manage "
                "https://www.googleapis.com/auth/userinfo.email "
                "https://www.googleapis.com/auth/userinfo.profile"
            ),
            "response_type": "code",
            "redirect_uri": self._redirect_uri,
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }
        return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str, **kwargs) -> OAuthAccount:
        if not (self._client_id and self._client_secret):
            # Local dev mock fallback
            return OAuthAccount(
                external_account_id="accounts/mock_account_123/locations/mock_location_123",
                account_name="Tiệm Havi Spa (Google Maps)",
                access_token="mock_google_business_access_token",
                refresh_token="mock_google_business_refresh_token",
                expires_at=datetime.now(UTC) + timedelta(hours=1),
            )

        payload = {
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self._redirect_uri,
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(GOOGLE_TOKEN_URL, data=payload)
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise OAuthTemporaryError(
                self.platform, f"Google Token API network failure: {exc}"
            ) from exc

        if resp.status_code in _TRANSIENT_STATUSES:
            raise OAuthTemporaryError(
                self.platform, f"Google Token API transient error: HTTP {resp.status_code}"
            )

        if resp.status_code >= 400:
            raise OAuthPermanentError(self.platform, f"Google Token API rejected code: {resp.text}")

        token_data = resp.json()
        access_token = token_data.get("access_token")
        if not access_token:
            raise OAuthPermanentError(
                self.platform, f"Google response missing access_token: {token_data}"
            )

        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in", 3600)

        resource, account_name = await self._resolve_location(access_token)

        return OAuthAccount(
            external_account_id=resource,
            account_name=account_name,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=datetime.now(UTC) + timedelta(seconds=expires_in),
        )

    async def _resolve_location(self, access_token: str) -> tuple[str, str]:
        """Tìm địa điểm Google Business thật mà tài khoản này quản lý.

        Trước đây chỗ này gọi `userinfo` rồi gắn `locations/` vào trước `id` của
        **người dùng**. Kết quả trông giống một location ID nhưng không phải::

            locations/117064704841566717018   ← đây là Google account ID

        Kết nối được lưu là CONNECTED, giao diện báo đã nối Google Business, và
        mọi bài đăng chết ở dead-letter với một trang HTML 404 của Google — vì
        đường dẫn đó không trỏ tới tài nguyên nào. Chuyện này đã xảy ra thật hai
        lần.

        Bịa ra một mã rồi báo thành công là cùng loại sai với việc báo "đã đăng"
        khi chưa gửi đi. Nên ở đây: hỏi đúng hai API của Business Profile, và nếu
        không tìm được địa điểm nào thì **hỏng ngay lúc nối**, kèm lý do đọc được
        — chứ không hỏng ba ngày sau ở một bài đăng không liên quan.

        Trả về `("accounts/{a}/locations/{l}", tên địa điểm)` — nguyên đường dẫn
        tài nguyên, vì đó chính là thứ `localPosts` cần.
        """
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            headers = {"Authorization": f"Bearer {access_token}"}

            accounts = await self._get_list(
                client, GOOGLE_ACCOUNTS_URL, headers=headers, key="accounts", what="tài khoản"
            )
            if not accounts:
                raise OAuthPermanentError(
                    self.platform,
                    "Tài khoản Google này chưa quản lý hồ sơ doanh nghiệp nào trên Google "
                    "Business Profile. Cần tạo hoặc xin quyền quản trị hồ sơ trước khi nối.",
                )

            for account in accounts:
                account_resource = account.get("name")
                if not account_resource:
                    continue
                locations = await self._get_list(
                    client,
                    f"{GOOGLE_LOCATIONS_URL}/{account_resource}/locations",
                    headers=headers,
                    params={"readMask": "name,title"},
                    key="locations",
                    what="địa điểm",
                )
                for location in locations:
                    location_resource = location.get("name")
                    if location_resource:
                        # `name` trả về dạng `locations/{id}`; ghép với account
                        # thành đường dẫn đầy đủ mà v4 localPosts yêu cầu.
                        return (
                            f"{account_resource}/{location_resource}",
                            location.get("title") or "Google Business Profile",
                        )

        raise OAuthPermanentError(
            self.platform,
            "Không tìm thấy địa điểm nào trong hồ sơ Google Business của tài khoản này. "
            "Havi cần một địa điểm cụ thể để biết đăng bài lên đâu.",
        )

    async def _get_list(
        self,
        client: httpx.AsyncClient,
        url: str,
        *,
        headers: dict[str, str],
        key: str,
        what: str,
        params: dict[str, str] | None = None,
    ) -> list[dict]:
        """Gọi một API danh sách của Business Profile, phân loại lỗi rồi trả mảng.

        Lỗi tạm (mạng, 5xx, 429) phải là `OAuthTemporaryError` để người dùng bấm
        nối lại là xong. Riêng 403 ở đây gần như luôn là **chưa được Google duyệt
        hạn mức** Business Profile API — mặc định dự án mới có quota bằng 0 — nên
        nói thẳng ra, thay vì để người dùng đi kiểm tra lại mật khẩu Google.
        """
        try:
            res = await client.get(url, headers=headers, params=params)
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise OAuthTemporaryError(
                self.platform, f"Không gọi được Google Business Profile API: {exc}"
            ) from exc

        if res.status_code in _TRANSIENT_STATUSES:
            raise OAuthTemporaryError(
                self.platform,
                f"Google Business Profile API tạm thời lỗi khi lấy {what}: HTTP {res.status_code}",
            )
        if res.status_code == 403:
            raise OAuthPermanentError(
                self.platform,
                "Google từ chối truy cập Business Profile API (403). Dự án Google Cloud cần "
                "được duyệt hạn mức Business Profile API trước khi Havi đăng bài lên Google "
                "Maps được.",
            )
        if res.status_code >= 400:
            raise OAuthPermanentError(
                self.platform,
                f"Google Business Profile API từ chối yêu cầu lấy {what}: HTTP {res.status_code}",
            )

        try:
            payload = res.json()
        except ValueError as exc:
            # Google trả HTML thay vì JSON nghĩa là đường dẫn sai, không phải dữ
            # liệu sai. Đừng nhét nguyên trang HTML vào thông báo lỗi.
            raise OAuthPermanentError(
                self.platform,
                f"Google trả về nội dung không phải JSON khi lấy {what} — sai địa chỉ API.",
            ) from exc

        items = payload.get(key)
        return items if isinstance(items, list) else []

    async def refresh_access_token(self, refresh_token: str) -> OAuthAccount:
        """Làm mới access token Google Business bằng refresh_token."""
        if not self.is_configured:
            raise OAuthPermanentError(
                self.platform, "Google Business OAuth chưa được cấu hình client_id / secret"
            )

        if refresh_token == "mock_google_business_refresh_token" or not (self._client_id and self._client_secret):
            return OAuthAccount(
                external_account_id="accounts/mock_account_123/locations/mock_location_123",
                account_name="Tiệm Havi Spa (Google Maps)",
                access_token="mock_refreshed_google_business_access_token",
                refresh_token=refresh_token,
                expires_at=datetime.now(UTC) + timedelta(hours=1),
                granted_scopes=["https://www.googleapis.com/auth/business.manage", "business.manage"],
            )

        payload = {
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(GOOGLE_TOKEN_URL, data=payload)
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise OAuthTemporaryError(self.platform, f"Lỗi mạng khi làm mới Google Business token: {exc}") from exc

        if resp.status_code in _TRANSIENT_STATUSES:
            raise OAuthTemporaryError(self.platform, f"Google OAuth HTTP {resp.status_code}")
        if resp.status_code in (400, 401, 403):
            raise OAuthPermanentError(self.platform, f"Google refresh token hết hạn hoặc bị thu hồi (HTTP {resp.status_code})")
        if resp.status_code != 200:
            raise OAuthPermanentError(self.platform, f"Google OAuth từ chối refresh token: HTTP {resp.status_code}")

        try:
            token_data = resp.json()
        except ValueError as exc:
            raise OAuthTemporaryError(self.platform, "Google OAuth trả dữ liệu không phải JSON") from exc

        access_token = token_data.get("access_token")
        if not access_token:
            raise OAuthPermanentError(self.platform, "Google OAuth không trả access_token khi làm mới")

        new_refresh = token_data.get("refresh_token") or refresh_token
        expires_in = token_data.get("expires_in", 3600)
        scope_str = token_data.get("scope") or ""
        raw_scopes = [s.strip() for s in scope_str.split(" ") if s.strip()]
        scopes = list(raw_scopes)
        if "https://www.googleapis.com/auth/business.manage" in raw_scopes and "business.manage" not in raw_scopes:
            scopes.append("business.manage")

        return OAuthAccount(
            external_account_id="",
            account_name="",
            access_token=access_token,
            refresh_token=new_refresh,
            expires_at=datetime.now(UTC) + timedelta(seconds=expires_in),
            granted_scopes=scopes if scopes else None,
        )
