"""Zalo OA OAuth Client — đổi `code` lấy Access Token & Refresh Token của Zalo Official Account.

Triển khai `OAuthClientPort` theo chuẩn OpenAPI v4 của Zalo Platform:
1. `authorization_url`: redirect người dùng tới màn hình xin cấp quyền của Zalo.
2. `exchange_code`: gửi POST request tới `https://oauth.zaloapp.com/v4/oa/access_token` với secret_key & code để lấy access_token + refresh_token.
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

ZALO_AUTH_URL = "https://oauth.zaloapp.com/v4/permission"
ZALO_TOKEN_URL = "https://oauth.zaloapp.com/v4/oa/access_token"
_TRANSIENT_STATUSES = frozenset({408, 429, 500, 502, 503, 504})


class ZaloOAuthClient(OAuthClientPort):
    def __init__(self, settings: Settings, *, timeout_seconds: float = 20.0) -> None:
        self._settings = settings
        self._client_id = settings.zalo_client_id
        self._client_secret = settings.zalo_client_secret
        self._redirect_uri = getattr(settings, "zalo_redirect_uri", "http://localhost:8000/connections/zalo_oa/callback")
        self._timeout = timeout_seconds

    @property
    def platform(self) -> Platform:
        return Platform.ZALO_OA

    @property
    def is_configured(self) -> bool:
        if bool(self._client_id and self._client_secret):
            return True
        return self._settings.use_fake_publisher or self._settings.env == "local"

    def authorization_url(self, *, state: str) -> str:
        if not (self._client_id and self._client_secret):
            # In local dev environment, bypass real Zalo server and return mock callback URL
            return f"http://localhost:8000/connections/zalo_oa/callback?code=mock_zalo_code&state={state}"
        params = {
            "app_id": self._client_id,
            "redirect_uri": self._redirect_uri,
            "state": state,
        }
        return f"{ZALO_AUTH_URL}?" + urlencode(params)

    async def exchange_code(self, code: str) -> OAuthAccount:
        if not self.is_configured:
            raise OAuthPermanentError(self.platform, "Zalo OAuth chưa được cấu hình client_id / secret")

        if code == "mock_zalo_code" or not (self._client_id and self._client_secret):
            return OAuthAccount(
                external_account_id="zalo_oa_mock_123",
                account_name="Zalo Official Account (Tiệm Demo)",
                access_token="mock_zalo_access_token",
                refresh_token="mock_zalo_refresh_token",
                expires_at=datetime.now(UTC) + timedelta(days=90),
            )

        headers = {
            "secret_key": self._client_secret,
            "Content-Type": "application/x-www-form-urlencoded",
        }
        payload = {
            "code": code,
            "app_id": self._client_id,
            "grant_type": "authorization_code",
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                response = await client.post(ZALO_TOKEN_URL, data=payload, headers=headers)
            except httpx.RequestError as exc:
                raise OAuthTemporaryError(f"Lỗi mạng kết nối Zalo OAuth: {exc}") from exc

        if response.status_code in _TRANSIENT_STATUSES:
            raise OAuthTemporaryError(f"Zalo OAuth HTTP {response.status_code}")
        if response.status_code != 200:
            raise OAuthPermanentError(f"Zalo OAuth từ chối (HTTP {response.status_code})")

        try:
            data = response.json()
        except ValueError as exc:
            raise OAuthTemporaryError("Zalo OAuth trả dữ liệu không phải JSON") from exc

        if "error" in data and data["error"] != 0 and "access_token" not in data:
            msg = data.get("message") or data.get("error_description") or f"Code {data.get('error')}"
            raise OAuthPermanentError(f"Zalo OAuth thất bại: {msg}")

        access_token = data.get("access_token")
        if not access_token:
            raise OAuthPermanentError("Zalo OAuth không trả access_token")

        refresh_token = data.get("refresh_token")
        expires_in = data.get("expires_in")
        expires_at = (
            datetime.now(UTC) + timedelta(seconds=int(expires_in))
            if expires_in
            else None
        )

        oa_id = data.get("oa_id")
        oa_name = data.get("oa_name")

        if access_token and not (oa_id and oa_name):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    oa_res = await client.get(
                        "https://openapi.zalo.me/v2.0/oa/getoa",
                        headers={"access_token": access_token},
                    )
                    if oa_res.status_code == 200:
                        oa_info = oa_res.json().get("data", {})
                        if isinstance(oa_info, dict):
                            oa_id = oa_info.get("oa_id") or oa_id
                            oa_name = oa_info.get("name") or oa_name
            except Exception:
                pass

        final_oa_id = str(oa_id or "zalo_oa_default")
        final_oa_name = str(oa_name or (f"Zalo OA ({final_oa_id})" if final_oa_id != "zalo_oa_default" else "Zalo Official Account"))

        return OAuthAccount(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            account_name=final_oa_name,
            external_account_id=final_oa_id,
        )
