"""Google Business Profile Publisher Adapter.

Official integration using Google My Business API v4 `localPosts` endpoints.
Maps status codes to Havi error classification hierarchy:
- TemporaryPublishError (429 rate limit, 5xx backend errors)
- AuthPermissionError (Expired OAuth token, revoked permissions)
- ValidationPublishError (Content violation or invalid media attachment)
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
        # Đường dẫn đầy đủ `accounts/{a}/locations/{l}` do luồng nối kênh phân
        # giải và lưu lại. Không có mặc định thay thế: đoán một địa điểm rồi
        # đăng bài của khách lên đó là sai nguy hiểm hơn hẳn việc không đăng.
        location_resource = request.external_account_id
        if not location_resource:
            raise ValidationPublishError(
                self.channel,
                "Kết nối Google Business chưa xác định được địa điểm — cần nối lại kênh",
            )
        url = f"{GOOGLE_MYBUSINESS_BASE}/{location_resource}/localPosts"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "languageCode": "vi-VN",
            "summary": request.text,
            "topicType": "STANDARD",
            "media": [
                {"mediaFormat": "PHOTO", "sourceUrl": media_url} for media_url in request.media_urls
            ]
            if request.media_urls
            else [],
            "actionType": "LEARN_MORE",
        }

        try:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code in (401, 403):
                raise AuthPermissionError(
                    self.channel, "Google Business token expired or permissions revoked"
                )
            if resp.status_code == 429:
                raise TemporaryPublishError(
                    self.channel,
                    "Google Business API Quota bị giới hạn (cần đăng ký hạn mức Google Business Profile API)",
                )
            if resp.status_code >= 500:
                raise TemporaryPublishError(
                    self.channel, f"Google Business API HTTP {resp.status_code}"
                )
            if resp.status_code >= 400:
                try:
                    data = resp.json() if resp.content else {}
                    err_msg = data.get("error", {}).get("message") or resp.text
                except Exception:
                    err_msg = resp.text[:200]
                raise ValidationPublishError(
                    self.channel, f"Google API Error {resp.status_code}: {err_msg}"
                )

            try:
                data = resp.json()
            except Exception:
                data = {}
            now = datetime.now(UTC)
            post_id = data.get("name") or f"google_post_{int(now.timestamp())}"
            return PublishResult(external_post_id=post_id, published_at=now)
        except httpx.RequestError as exc:
            raise TemporaryPublishError(
                self.channel,
                f"Network error contacting Google My Business API: {exc}",
            ) from exc
