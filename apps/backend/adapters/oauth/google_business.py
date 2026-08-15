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
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
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

    async def exchange_code(self, *, code: str) -> OAuthAccount:
        if not (self._client_id and self._client_secret):
            # Local dev mock fallback
            return OAuthAccount(
                external_account_id="locations/mock_location_123",
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
            raise OAuthTemporaryError(f"Google Token API network failure: {exc}") from exc

        if resp.status_code in _TRANSIENT_STATUSES:
            raise OAuthTemporaryError(f"Google Token API transient error: HTTP {resp.status_code}")

        if resp.status_code >= 400:
            raise OAuthPermanentError(f"Google Token API rejected code: {resp.text}")

        token_data = resp.json()
        access_token = token_data.get("access_token")
        if not access_token:
            raise OAuthPermanentError(f"Google response missing access_token: {token_data}")

        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in", 3600)

        # Lấy thông tin user / location name
        location_id = "locations/primary"
        account_name = "Google Business Profile"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                res = await client.get(
                    GOOGLE_USERINFO_URL,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                if res.status_code == 200:
                    info = res.json()
                    location_id = f"locations/{info.get('id', 'primary')}"
                    account_name = info.get("name", "Google Business Profile")
        except Exception as exc:
            logger.warning("Failed to fetch Google Business account details: %s", exc)

        return OAuthAccount(
            external_account_id=location_id,
            account_name=account_name,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=datetime.now(UTC) + timedelta(seconds=expires_in),
        )
