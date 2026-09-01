"""TikTok Publisher Adapter — xuất bản video lên TikTok qua Content Posting API.

Triển khai `PublisherPort` theo chuẩn TikTok Content Posting API v2:
- `POST https://open.tiktokapis.com/v2/post/publish/video/init/`
- Chuyển `idempotency_key` và `video_url`.
"""

import logging
import os
from datetime import UTC, datetime
from pathlib import Path

import httpx

from core.enums import Channel
from domain.ports.publisher import (
    AmbiguousPublishError,
    AuthPermissionError,
    PublisherPort,
    PublishRequest,
    PublishResult,
    TemporaryPublishError,
    ValidationPublishError,
)

logger = logging.getLogger(__name__)


TIKTOK_INBOX_INIT_URL = "https://open.tiktokapis.com/v2/post/publish/inbox/video/init/"
TIKTOK_DIRECT_INIT_URL = "https://open.tiktokapis.com/v2/post/publish/video/init/"
_TRANSIENT_STATUSES = frozenset({408, 429, 500, 502, 503, 504})


class TikTokPublisher(PublisherPort):
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
        return Channel.TIKTOK

    async def publish(self, request: PublishRequest, *, access_token: str) -> PublishResult:
        if not access_token:
            raise AuthPermissionError(self.channel, "Thiếu access_token TikTok")

        if not request.media_urls:
            raise ValidationPublishError(
                self.channel, "TikTok bắt buộc phải có ít nhất 1 video URL"
            )

        video_source = request.media_urls[0]

        if self._client is not None:
            return await self._do_publish(
                self._client, video_source, access_token, request.idempotency_key
            )

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            return await self._do_publish(
                client, video_source, access_token, request.idempotency_key
            )

    async def _do_publish(
        self,
        client: httpx.AsyncClient,
        video_source: str,
        access_token: str,
        idempotency_key: str | None,
    ) -> PublishResult:
        # 1. Lấy dữ liệu bytes của Video (từ file path hoặc URL)
        local_path = video_source[7:] if video_source.startswith("file://") else video_source
        video_bytes: bytes | None = None
        if os.path.exists(local_path):
            video_bytes = Path(local_path).read_bytes()
        else:
            try:
                media_resp = await client.get(video_source)
                if media_resp.status_code == 200:
                    video_bytes = media_resp.content
            except Exception as exc:
                logger.warning("Không thể tải video từ URL %s: %s", video_source, exc)

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        }
        if idempotency_key:
            headers["X-Idempotency-Key"] = idempotency_key

        # Nếu có bytes video, sử dụng FILE_UPLOAD (chuẩn truyền tải nhị phân an toàn nhất của TikTok)
        if video_bytes:
            video_size = len(video_bytes)
            init_payload = {
                "source_info": {
                    "source": "FILE_UPLOAD",
                    "video_size": video_size,
                    "chunk_size": video_size,
                    "total_chunk_count": 1,
                },
            }
            try:
                resp = await client.post(TIKTOK_INBOX_INIT_URL, json=init_payload, headers=headers)
            except httpx.TimeoutException as exc:
                # Timeout KHÔNG chứng minh là chưa tạo. TikTok có thể đã nhận
                # request và cấp `publish_id`, chỉ là response không về tới đây.
                # Retry lúc này tạo publish_id thứ hai, tức hai video.
                raise AmbiguousPublishError(
                    self.channel,
                    f"TikTok không phản hồi sau {self._timeout}s. Kiểm tra Hộp thư "
                    "TikTok trước khi đăng lại.",
                ) from exc
            except httpx.RequestError as exc:
                # Không nội suy `exc`: httpx đưa cả URL vào message, mà URL có
                # thể mang tham số nhạy cảm.
                raise TemporaryPublishError(
                    self.channel,
                    f"Lỗi mạng khi gọi TikTok Publish API: {type(exc).__name__}",
                ) from exc

            if resp.status_code in _TRANSIENT_STATUSES:
                raise TemporaryPublishError(self.channel, f"TikTok trả về HTTP {resp.status_code}")
            if resp.status_code in (401, 403):
                raise AuthPermissionError(
                    self.channel, "Token TikTok hết hạn hoặc mất quyền đăng bài"
                )
            if "spam_risk_too_many_pending_share" in resp.text:
                raise TemporaryPublishError(
                    self.channel,
                    "TikTok tạm giữ nhịp do có nhiều video chờ duyệt trong Hộp thư. Vui lòng mở App TikTok bấm Đăng hoặc xoá bớt bản nháp cũ.",
                )
            if resp.status_code >= 400:
                raise ValidationPublishError(
                    self.channel, f"TikTok từ chối video: {resp.text[:200]}"
                )

            body = resp.json()
            data = body.get("data") or {}
            publish_id = data.get("publish_id")
            upload_url = data.get("upload_url")

            if not publish_id:
                err_msg = body.get("error", {}).get("message") or "Không nhận được publish_id"
                raise ValidationPublishError(self.channel, f"TikTok Publish lỗi: {err_msg}")

            if upload_url:
                upload_headers = {
                    "Content-Range": f"bytes 0-{video_size - 1}/{video_size}",
                    "Content-Type": "video/mp4",
                }
                # Từ đây trở đi `publish_id` ĐÃ tồn tại ở phía TikTok. Mọi lỗi
                # sau điểm này là *ambiguous*, không phải temporary: TikTok có
                # thể đã nhận đủ video và vẫn xử lý tiếp dù response về tới đây
                # bị lỗi. Ném `TemporaryPublishError` ở đây nghĩa là worker retry
                # từ đầu, gọi lại `inbox/video/init/` và tạo **publish_id thứ
                # hai** — tức hai video trên cùng một tài khoản.
                #
                # `X-Idempotency-Key` không cứu được: TikTok Content Posting API
                # không tài liệu hoá header này, nên không thể dựa vào nó để
                # chống trùng (Havi vẫn gửi vì vô hại).
                try:
                    up_resp = await client.put(
                        upload_url, content=video_bytes, headers=upload_headers
                    )
                except httpx.RequestError as exc:
                    raise AmbiguousPublishError(
                        self.channel,
                        f"Mất kết nối khi tải video lên TikTok (publish_id={publish_id}): "
                        f"{exc}. Kiểm tra Hộp thư TikTok trước khi đăng lại.",
                    ) from exc
                if up_resp.status_code not in (200, 201):
                    raise AmbiguousPublishError(
                        self.channel,
                        f"Tải video lên TikTok trả HTTP {up_resp.status_code} "
                        f"(publish_id={publish_id}). Kiểm tra Hộp thư TikTok trước "
                        "khi đăng lại.",
                    )

            return PublishResult(
                external_post_id=publish_id,
                published_at=datetime.now(UTC),
            )

        # Fallback: PULL_FROM_URL
        payload = {
            "source_info": {
                "source": "PULL_FROM_URL",
                "video_url": video_source,
            },
        }
        try:
            resp = await client.post(TIKTOK_INBOX_INIT_URL, json=payload, headers=headers)
        except httpx.TimeoutException as exc:
            raise AmbiguousPublishError(
                self.channel,
                f"TikTok không phản hồi sau {self._timeout}s. Kiểm tra Hộp thư "
                "TikTok trước khi đăng lại.",
            ) from exc
        except httpx.RequestError as exc:
            raise TemporaryPublishError(
                self.channel,
                f"Lỗi mạng khi gọi TikTok Publish API: {type(exc).__name__}",
            ) from exc

        if resp.status_code in _TRANSIENT_STATUSES:
            raise TemporaryPublishError(self.channel, f"TikTok trả về HTTP {resp.status_code}")
        if resp.status_code in (401, 403):
            raise AuthPermissionError(self.channel, "Token TikTok hết hạn hoặc mất quyền đăng bài")
        if resp.status_code >= 400:
            raise ValidationPublishError(self.channel, f"TikTok từ chối video: {resp.text[:200]}")

        body = resp.json()
        data = body.get("data") or {}
        publish_id = data.get("publish_id")
        if not publish_id:
            raise ValidationPublishError(self.channel, "Không nhận được publish_id từ TikTok")

        return PublishResult(
            external_post_id=publish_id,
            published_at=datetime.now(UTC),
        )
