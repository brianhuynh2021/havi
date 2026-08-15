"""TikTok OAuth Client — đổi `code` lấy Access Token của TikTok Account.

Triển khai `OAuthClientPort` theo chuẩn TikTok Login Kit v2:
1. `authorization_url`: redirect người dùng tới màn hình xin cấp quyền của TikTok.
2. `exchange_code`: POST tới `https://open.tiktokapis.com/v2/oauth/token/` kèm
   client_key & client_secret để lấy access_token + refresh_token.
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

TIKTOK_AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"
TIKTOK_TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
_TRANSIENT_STATUSES = frozenset({408, 429, 500, 502, 503, 504})


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
        params = {
            "client_key": self._client_key,
            "scope": "user.info.basic,video.upload,video.publish",
            "response_type": "code",
            "redirect_uri": self._redirect_uri,
            "state": state,
        }
        return f"{TIKTOK_AUTH_URL}?" + urlencode(params)

    async def exchange_code(self, code: str) -> OAuthAccount:
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
            )

        payload = {
            "client_key": self._client_key,
            "client_secret": self._client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self._redirect_uri,
        }
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

        data_body = data.get("data") or {}
        access_token = data_body.get("access_token")
        if not access_token:
            err_msg = (
                data.get("error_description") or data.get("message") or "Không có access_token"
            )
            raise OAuthPermanentError(self.platform, f"TikTok OAuth lỗi: {err_msg}")

        open_id = data_body.get("open_id") or "tiktok_user"
        expires_in = data_body.get("expires_in", 86400)
        refresh_token = data_body.get("refresh_token")

        return OAuthAccount(
            external_account_id=open_id,
            account_name=f"TikTok @{open_id[:10]}",
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=datetime.now(UTC) + timedelta(seconds=expires_in),
        )
