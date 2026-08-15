"""Zalo Official Account (OA) Publisher Adapter.

Official integration using Zalo OpenAPI v3 endpoints.
Enforces strict error classification into:
- TemporaryPublishError (429 rate limit, 5xx backend errors)
- AuthPermissionError (Expired OAuth token, invalid access token)
- ValidationPublishError (Content format rejected or media quota exceeded)
"""

import logging
from datetime import UTC, datetime

import httpx

from core.enums import Channel
from domain.ports.publisher import (
    AuthPermissionError,
    PublisherPort,
    PublishRequest,
    PublishResult,
    TemporaryPublishError,
    ValidationPublishError,
)

logger = logging.getLogger("havi.adapters.publishers.zalo")

ZALO_OPENAPI_BASE = "https://openapi.zalo.me/v3.0/oa"


class ZaloPublisher(PublisherPort):
    """Official publisher adapter for Zalo Official Accounts (OA)."""

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    @property
    def channel(self) -> Channel:
        return Channel.ZALO_OA

    async def publish(self, request: PublishRequest, *, access_token: str) -> PublishResult:
        if not access_token:
            raise AuthPermissionError(self.channel, "Missing Zalo OA access token")

        client = self._client or httpx.AsyncClient(timeout=10.0)
        url = f"{ZALO_OPENAPI_BASE}/message/paragraph"
        headers = {
            "access_token": access_token,
            "Content-Type": "application/json",
        }
        payload = {
            "recipient": {"user_id": request.external_account_id or "broadcast"},
            "message": {
                "text": request.text,
                "attachment": {
                    "type": "template",
                    "payload": {
                        "template_type": "media",
                        "elements": [
                            {"media_type": "image", "url": url} for url in request.media_urls[:1]
                        ]
                        if request.media_urls
                        else [],
                    },
                },
            },
        }

        try:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code in (401, 403):
                raise AuthPermissionError(self.channel, "Zalo OA token expired or revoked")
            if resp.status_code == 429 or resp.status_code >= 500:
                raise TemporaryPublishError(self.channel, f"Zalo API HTTP {resp.status_code}")

            data = resp.json()
            error_code = data.get("error", 0)
            message = data.get("message")
            if error_code in (-216, -201):
                raise AuthPermissionError(self.channel, f"Zalo Auth Error {error_code}: {message}")
            if error_code != 0:
                raise ValidationPublishError(self.channel, f"Zalo Error {error_code}: {message}")

            now = datetime.now(UTC)
            msg_id = data.get("data", {}).get("message_id") or f"zalo_msg_{int(now.timestamp())}"
            return PublishResult(external_post_id=msg_id, published_at=now)
        except httpx.RequestError as exc:
            raise TemporaryPublishError(
                self.channel, f"Network error contacting Zalo OpenAPI: {exc}"
            ) from exc
