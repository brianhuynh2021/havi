"""TikTok Publisher Adapter — xuất bản video lên TikTok qua Content Posting API.

Triển khai `PublisherPort` theo chuẩn TikTok Content Posting API v2:
- `POST https://open.tiktokapis.com/v2/post/publish/video/init/`
- Chuyển `idempotency_key` và `video_url`.
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

logger = logging.getLogger(__name__)

TIKTOK_PUBLISH_INIT_URL = "https://open.tiktokapis.com/v2/post/publish/video/init/"
_TRANSIENT_STATUSES = frozenset({408, 429, 500, 502, 503, 504})


class TikTokPublisher(PublisherPort):
    def __init__(
        self,
        *,
        client: httpx.AsyncClient | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        self._client = client
        self._timeout = timeout_seconds

    @property
    def channel(self) -> Channel:
        return Channel.TIKTOK

    async def publish(self, request: PublishRequest, *, access_token: str) -> PublishResult:
        if not access_token:
            raise AuthPermissionError(self.channel, "Thiếu access_token TikTok")

        if not request.media_urls:
            raise ValidationPublishError(
                self.channel, "TikTok bắt buộc phải có ít nhất 1 video URL"
            )

        video_url = request.media_urls[0]
        payload = {
            "post_info": {
                "title": request.text[:150] if request.text else "Video từ Havi AI",
                "privacy_level": "PUBLIC_TO_EVERYONE",
                "disable_duet": False,
                "disable_stitch": False,
                "disable_comment": False,
            },
            "source_info": {
                "source": "PULL_FROM_URL",
                "video_url": video_url,
            },
        }

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        }
        if request.idempotency_key:
            headers["X-Idempotency-Key"] = request.idempotency_key

        if self._client is not None:
            return await self._do_publish(self._client, payload, headers)

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            return await self._do_publish(client, payload, headers)

    async def _do_publish(
        self,
        client: httpx.AsyncClient,
        payload: dict,
        headers: dict,
    ) -> PublishResult:
        try:
            response = await client.post(TIKTOK_PUBLISH_INIT_URL, json=payload, headers=headers)
        except httpx.RequestError as exc:
            raise TemporaryPublishError(
                self.channel, f"Lỗi mạng khi gọi TikTok Publish API: {exc}"
            ) from exc

        if response.status_code in _TRANSIENT_STATUSES:
            raise TemporaryPublishError(self.channel, f"TikTok trả về HTTP {response.status_code}")
        if response.status_code in (401, 403):
            raise AuthPermissionError(self.channel, "Token TikTok hết hạn hoặc mất quyền đăng bài")
        if response.status_code >= 400:
            err_detail = response.text[:200]
            msg = f"TikTok từ chối video (HTTP {response.status_code}): {err_detail}"
            raise ValidationPublishError(self.channel, msg)

        try:
            body = response.json()
        except ValueError as exc:
            raise TemporaryPublishError(
                self.channel, "TikTok trả về dữ liệu không phải JSON"
            ) from exc

        data = body.get("data") or {}
        publish_id = data.get("publish_id")
        if not publish_id:
            err = body.get("error", {})
            err_code = err.get("code")
            err_msg = err.get("message") or "Không nhận được publish_id"
            if err_code in ("access_token_invalid", "scope_not_authorized"):
                raise AuthPermissionError(self.channel, f"TikTok auth error: {err_msg}")
            raise ValidationPublishError(self.channel, f"TikTok publish error: {err_msg}")

        return PublishResult(
            external_post_id=publish_id,
            published_at=datetime.now(UTC),
        )
