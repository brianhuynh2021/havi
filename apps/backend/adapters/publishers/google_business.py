"""Google Business Profile Publisher Adapter.

Official integration using Google My Business API v4 `localPosts` endpoints.
Maps status codes to Havi error classification hierarchy:
- TemporaryPublishError (429 rate limit, 5xx backend errors)
- AuthPermissionError (Expired OAuth token, revoked permissions)
- ValidationPublishError (Content violation or invalid media attachment)
"""

from datetime import UTC, datetime
import logging
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

logger = logging.getLogger("havi.adapters.publishers.google_business")

GOOGLE_MYBUSINESS_BASE = "https://mybusiness.googleapis.com/v4"


class GoogleBusinessPublisher(PublisherPort):
    """Official publisher adapter for Google Business Profile (Local Posts)."""

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    @property
    def channel(self) -> Channel:
        return Channel.GOOGLE_BUSINESS

    async def publish(self, request: PublishRequest, *, access_token: str) -> PublishResult:
        if not access_token:
            raise AuthPermissionError(self.channel, "Missing Google Business access token")

        client = self._client or httpx.AsyncClient(timeout=10.0)
        location_id = request.external_account_id or "locations/primary"
        url = f"{GOOGLE_MYBUSINESS_BASE}/{location_id}/localPosts"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "languageCode": "vi-VN",
            "summary": request.text,
            "topicType": "STANDARD",
            "media": [
                {"mediaFormat": "PHOTO", "sourceUrl": media_url}
                for media_url in request.media_urls
            ]
            if request.media_urls
            else [],
            "actionType": "LEARN_MORE",
        }

        try:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code in (401, 403):
                raise AuthPermissionError(self.channel, "Google Business token expired or permissions revoked")
            if resp.status_code == 429 or resp.status_code >= 500:
                raise TemporaryPublishError(self.channel, f"Google Business API HTTP {resp.status_code}")
            if resp.status_code >= 400:
                data = resp.json() if resp.content else {}
                err_msg = data.get("error", {}).get("message") or resp.text
                raise ValidationPublishError(self.channel, f"Google API Error {resp.status_code}: {err_msg}")

            data = resp.json()
            post_id = data.get("name") or f"google_post_{int(datetime.now(UTC).timestamp())}"
            return PublishResult(external_post_id=post_id, published_at=datetime.now(UTC))
        except httpx.RequestError as exc:
            raise TemporaryPublishError(self.channel, f"Network error contacting Google My Business API: {exc}")
