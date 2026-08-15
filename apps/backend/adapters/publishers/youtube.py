"""YouTube Publisher Adapter — xuất bản video lên YouTube Shorts qua YouTube Data API v3.

Triển khai `PublisherPort` theo chuẩn YouTube Data API v3:
- Endpoint: `https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status`
- Tự động gắn thẻ `#Shorts` vào tiêu đề/mô tả nếu là video dọc.
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

YOUTUBE_UPLOAD_URL = (
    "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status"
)
_TRANSIENT_STATUSES = frozenset({408, 429, 500, 502, 503, 504})


class YouTubePublisher(PublisherPort):
    def __init__(
        self,
        *,
        client: httpx.AsyncClient | None = None,
        timeout_seconds: float = 60.0,
    ) -> None:
        self._client = client
        self._timeout = timeout_seconds

    @property
    def channel(self) -> Channel:
        return Channel.YOUTUBE

    async def publish(self, request: PublishRequest, *, access_token: str) -> PublishResult:
        if not access_token:
            raise AuthPermissionError(self.channel, "Thiếu access_token Google/YouTube")

        if not request.media_urls:
            raise ValidationPublishError(
                self.channel, "YouTube Shorts bắt buộc phải có ít nhất 1 video URL"
            )

        title = request.text.split("\n")[0][:90] if request.text else "Havi AI Video"
        if "#Shorts" not in title and "#shorts" not in title:
            title = f"{title} #Shorts"

        description = request.text or "Video được xuất bản bởi Havi AI"
        if "#Shorts" not in description:
            description = f"{description}\n\n#Shorts"

        snippet = {
            "title": title,
            "description": description,
            "categoryId": "22",  # People & Blogs
        }
        status_info = {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
        }
        payload = {"snippet": snippet, "status": status_info}

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8",
            "X-Upload-Content-Type": "video/mp4",
        }

        video_url = request.media_urls[0]

        if self._client is not None:
            return await self._do_publish(self._client, payload, headers, video_url)

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            return await self._do_publish(client, payload, headers, video_url)

    async def _do_publish(
        self,
        client: httpx.AsyncClient,
        payload: dict,
        headers: dict,
        video_url: str,
    ) -> PublishResult:
        try:
            # 1. Khởi tạo phiên upload
            init_res = await client.post(YOUTUBE_UPLOAD_URL, json=payload, headers=headers)
        except httpx.RequestError as exc:
            raise TemporaryPublishError(
                self.channel, f"Lỗi mạng khi khởi tạo YouTube Upload: {exc}"
            ) from exc

        if init_res.status_code in _TRANSIENT_STATUSES:
            raise TemporaryPublishError(self.channel, f"YouTube trả về HTTP {init_res.status_code}")
        if init_res.status_code in (401, 403):
            raise AuthPermissionError(
                self.channel, "Token Google/YouTube hết hạn hoặc mất quyền upload video"
            )
        if init_res.status_code != 200:
            raise ValidationPublishError(
                self.channel, f"YouTube từ chối tạo phiên upload: {init_res.text[:200]}"
            )

        upload_location = init_res.headers.get("Location")
        if not upload_location:
            raise TemporaryPublishError(
                self.channel, "YouTube không trả Location header cho resumable upload"
            )

        # 2. Tải bytes từ media_url và đẩy lên YouTube
        try:
            video_res = await client.get(video_url)
            if video_res.status_code != 200:
                raise ValidationPublishError(
                    self.channel, f"Không thể tải video từ URL: {video_url}"
                )
            video_bytes = video_res.content

            upload_res = await client.put(
                upload_location,
                content=video_bytes,
                headers={"Content-Type": "video/mp4"},
            )
        except httpx.RequestError as exc:
            raise TemporaryPublishError(
                self.channel, f"Lỗi mạng khi truyền video lên YouTube: {exc}"
            ) from exc

        if upload_res.status_code in _TRANSIENT_STATUSES:
            raise TemporaryPublishError(
                self.channel, f"YouTube upload trả về HTTP {upload_res.status_code}"
            )
        if upload_res.status_code not in (200, 201):
            err_detail = upload_res.text[:200]
            msg = f"YouTube upload thất bại (HTTP {upload_res.status_code}): {err_detail}"
            raise ValidationPublishError(self.channel, msg)

        try:
            res_json = upload_res.json()
            video_id = res_json.get("id") or f"yt_{int(datetime.now(UTC).timestamp())}"
        except ValueError:
            video_id = f"yt_{int(datetime.now(UTC).timestamp())}"

        return PublishResult(
            external_post_id=video_id,
            published_at=datetime.now(UTC),
        )
