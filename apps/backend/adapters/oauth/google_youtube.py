"""Google / YouTube OAuth Client — đổi `code` lấy Access Token cho YouTube Channel.

Triển khai `OAuthClientPort` theo chuẩn Google OAuth 2.0:
1. `authorization_url`: redirect tới màn hình cấp quyền Google với scope `youtube.upload`.
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
YOUTUBE_CHANNELS_URL = "https://www.googleapis.com/youtube/v3/channels"
_TRANSIENT_STATUSES = frozenset({408, 429, 500, 502, 503, 504})


class GoogleYouTubeOAuthClient(OAuthClientPort):
    def __init__(self, settings: Settings, *, timeout_seconds: float = 20.0) -> None:
        self._settings = settings
        self._client_id = settings.google_client_id
        self._client_secret = settings.google_client_secret
        self._redirect_uri = getattr(
            settings,
            "youtube_redirect_uri",
            "http://localhost:8000/connections/youtube/callback",
        )
        self._timeout = timeout_seconds

    @property
    def platform(self) -> Platform:
        return Platform.YOUTUBE

    @property
    def is_configured(self) -> bool:
        if bool(self._client_id and self._client_secret):
            return True
        return self._settings.use_fake_publisher or self._settings.env == "local"

    def authorization_url(self, *, state: str) -> str:
        if not (self._client_id and self._client_secret):
            # In local dev / fake mode, return mock callback URL
            return f"http://localhost:8000/connections/youtube/callback?code=mock_youtube_code&state={state}"
        params = {
            "client_id": self._client_id,
            "scope": "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly",
            "response_type": "code",
            "access_type": "offline",
            "prompt": "consent",
            "redirect_uri": self._redirect_uri,
            "state": state,
        }
        return f"{GOOGLE_AUTH_URL}?" + urlencode(params)

    async def exchange_code(self, code: str, **kwargs) -> OAuthAccount:
        if not self.is_configured:
            raise OAuthPermanentError(
                self.platform, "Google/YouTube OAuth chưa được cấu hình client_id / secret"
            )

        if code == "mock_youtube_code" or not (self._client_id and self._client_secret):
            return OAuthAccount(
                external_account_id="youtube_mock_channel_123",
                account_name="YouTube @KenhTiemDemo",
                access_token="mock_youtube_access_token",
                refresh_token="mock_youtube_refresh_token",
                expires_at=datetime.now(UTC) + timedelta(hours=1),
            )

        payload = {
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self._redirect_uri,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                response = await client.post(GOOGLE_TOKEN_URL, data=payload, headers=headers)
            except httpx.RequestError as exc:
                msg = f"Lỗi mạng kết nối Google OAuth: {exc}"
                raise OAuthTemporaryError(self.platform, msg) from exc

        if response.status_code in _TRANSIENT_STATUSES:
            raise OAuthTemporaryError(self.platform, f"Google OAuth HTTP {response.status_code}")
        if response.status_code != 200:
            msg = f"Google OAuth từ chối (HTTP {response.status_code})"
            raise OAuthPermanentError(self.platform, msg)

        try:
            data = response.json()
        except ValueError as exc:
            msg = "Google OAuth trả dữ liệu không phải JSON"
            raise OAuthTemporaryError(self.platform, msg) from exc

        access_token = data.get("access_token")
        if not access_token:
            raise OAuthPermanentError(self.platform, "Google OAuth không trả access_token")

        refresh_token = data.get("refresh_token")
        expires_in = data.get("expires_in", 3600)

        # Lấy thông tin kênh YouTube
        channel_name = "YouTube Channel"
        channel_id = "youtube_channel"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                res = await client.get(
                    YOUTUBE_CHANNELS_URL,
                    params={"part": "snippet", "mine": "true"},
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                if res.status_code == 200:
                    items = res.json().get("items") or []
                    if items:
                        channel_id = items[0].get("id", channel_id)
                        channel_name = items[0].get("snippet", {}).get("title", channel_name)
        except Exception as exc:
            logger.warning("Failed to fetch YouTube channel details: %s", exc)

        return OAuthAccount(
            external_account_id=channel_id,
            account_name=channel_name,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=datetime.now(UTC) + timedelta(seconds=expires_in),
        )
