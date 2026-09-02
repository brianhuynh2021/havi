"""YouTube Publisher Adapter — xuất bản video lên YouTube Shorts qua YouTube Data API v3.

Triển khai `PublisherPort` theo chuẩn YouTube Data API v3:
- Endpoint: `https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status`
- Resumable upload với xử lý lỗi nghiêm ngặt:
  - 2xx thiếu video_id hoặc đứt kết nối sau khi đã cấp id -> `AmbiguousPublishError`
  - 408, 429, 500, 502, 503, 504 -> `TemporaryPublishError`
  - 401, 403 -> `AuthPermissionError`
  - 400 và lỗi khác -> `ValidationPublishError`
- Đối soát trạng thái qua `videos.list(part=status,processingDetails)`:
  - `uploadStatus=processed` hoặc `processingStatus=succeeded` -> `SUCCEEDED`
  - `uploadStatus in (failed, rejected)` hoặc `processingStatus in (failed, terminated)` -> `DEAD_LETTER`
  - `uploadStatus in (uploaded, processing)` hoặc `processingStatus=processing` -> `PENDING_RECONCILIATION`
"""

from datetime import UTC, datetime
import logging
import os
from pathlib import Path

import httpx

from core.enums import Channel, PublishFailureKind, PublishStatus
from domain.models.publish import PublishJob
from domain.ports.publisher import (
    AmbiguousPublishError,
    AuthPermissionError,
    PublisherPort,
    PublishRequest,
    PublishResult,
    ReconciliationOutcome,
    TemporaryPublishError,
    ValidationPublishError,
)

logger = logging.getLogger(__name__)

YOUTUBE_UPLOAD_INIT_URL = (
    "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status"
)
YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
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
            # 1. Khởi tạo phiên upload (resumable)
            init_res = await client.post(YOUTUBE_UPLOAD_INIT_URL, json=payload, headers=headers)
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
        if init_res.status_code not in (200, 201):
            raise ValidationPublishError(
                self.channel, f"YouTube từ chối tạo phiên upload: {init_res.text[:200]}"
            )

        upload_location = init_res.headers.get("Location")
        if not upload_location:
            raise AmbiguousPublishError(
                self.channel, "YouTube trả 2xx nhưng không có Location header cho phiên tải video"
            )

        # 2. Tải video bytes
        video_bytes: bytes | None = None
        local_path = video_url[7:] if video_url.startswith("file://") else video_url
        if os.path.exists(local_path):
            video_bytes = Path(local_path).read_bytes()
        else:
            try:
                video_res = await client.get(video_url)
                if video_res.status_code == 200:
                    video_bytes = video_res.content
            except Exception as exc:
                logger.warning("Không thể tải video từ URL %s: %s", video_url, exc)

        if not video_bytes:
            raise ValidationPublishError(
                self.channel, f"Không thể lấy nội dung video để upload lên YouTube: {video_url}"
            )

        # 3. Đẩy video content lên YouTube upload_location
        # Sau khi đã có upload_location, nếu bị timeout hoặc lỗi mạng thì cần xác minh
        # thay vì tự động upload lại từ đầu
        try:
            upload_res = await client.put(
                upload_location,
                content=video_bytes,
                headers={"Content-Type": "video/mp4"},
            )
        except httpx.TimeoutException as exc:
            raise AmbiguousPublishError(
                self.channel,
                f"YouTube không phản hồi khi tải video (upload_location={upload_location[:60]}...). "
                "Cần kiểm tra trạng thái video trên YouTube Studio trước khi đăng lại.",
            ) from exc
        except (httpx.RequestError, OSError) as exc:
            raise AmbiguousPublishError(
                self.channel,
                f"Lỗi kết nối khi tải video lên YouTube: {exc}. Kiểm tra YouTube Studio.",
            ) from exc

        if upload_res.status_code in _TRANSIENT_STATUSES:
            raise TemporaryPublishError(
                self.channel, f"YouTube upload trả về HTTP {upload_res.status_code}"
            )
        if upload_res.status_code in (401, 403):
            raise AuthPermissionError(
                self.channel, "Token Google/YouTube hết hạn trong quá trình upload video"
            )
        if upload_res.status_code not in (200, 201):
            err_detail = upload_res.text[:200]
            msg = f"YouTube upload thất bại (HTTP {upload_res.status_code}): {err_detail}"
            raise ValidationPublishError(self.channel, msg)

        try:
            res_json = upload_res.json()
        except ValueError as exc:
            raise AmbiguousPublishError(
                self.channel, f"YouTube trả 2xx nhưng không phải JSON hợp lệ: {exc}"
            ) from exc

        video_id = res_json.get("id")
        if not video_id:
            raise AmbiguousPublishError(
                self.channel, "YouTube trả 2xx nhưng không có id của video"
            )

        return PublishResult(
            external_post_id=video_id,
            published_at=datetime.now(UTC),
        )

    async def reconcile(
        self,
        *,
        external_post_id: str | None = None,
        access_token: str,
        **kwargs,
    ) -> ReconciliationOutcome:
        """Đối soát trạng thái video YouTube bằng YouTube Data API v3 (`videos.list`).

        Theo COMMERCIAL_READINESS_PROMPT §3.2:
        - `videos.list(id=...)` đọc `status.uploadStatus` và `processingDetails`.
        - `processed` hoặc `processingStatus=succeeded` -> published.
        - `failed/rejected` hoặc `processingStatus=failed/terminated` -> failed kèm lý do.
        - `uploaded/processing` -> in_progress tiếp tục chờ.
        """
        video_id = external_post_id
        if not video_id:
            return ReconciliationOutcome(
                status="failed",
                error_message="Không có video_id để đối soát YouTube",
            )

        params = {
            "part": "status,processingDetails",
            "id": video_id,
        }
        headers = {
            "Authorization": f"Bearer {access_token}",
        }

        async def _query(cli: httpx.AsyncClient) -> httpx.Response:
            return await cli.get(YOUTUBE_VIDEOS_URL, params=params, headers=headers)

        try:
            if self._client is not None:
                resp = await _query(self._client)
            else:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    resp = await _query(client)
        except Exception as exc:
            logger.warning("Lỗi mạng khi đối soát video YouTube %s: %s", video_id, exc)
            return ReconciliationOutcome(
                status="in_progress",
                error_message=f"Lỗi mạng khi kiểm tra YouTube: {exc}",
            )

        if resp.status_code in (401, 403):
            return ReconciliationOutcome(
                status="in_progress",
                error_message="Token YouTube không đủ quyền hoặc hết hạn khi đối soát",
            )

        if resp.status_code != 200:
            return ReconciliationOutcome(
                status="in_progress",
                error_message=f"YouTube API trả HTTP {resp.status_code}: {resp.text[:200]}",
            )

        try:
            data = resp.json()
        except ValueError:
            return ReconciliationOutcome(
                status="in_progress",
                error_message="YouTube API trả dữ liệu không phải JSON",
            )

        items = data.get("items") or []
        if not items:
            return ReconciliationOutcome(
                status="failed",
                error_message=f"Video id '{video_id}' không tồn tại trên YouTube",
            )

        video_item = items[0]
        status_info = video_item.get("status") or {}
        upload_status = status_info.get("uploadStatus", "").lower()
        rejection_reason = status_info.get("rejectionReason")
        failure_reason = status_info.get("failureReason")

        proc_info = video_item.get("processingDetails") or {}
        proc_status = proc_info.get("processingStatus", "").lower()
        proc_failure_reason = proc_info.get("processingFailureReason")

        # Thành công: video đã qua xử lý và sẵn sàng
        if upload_status == "processed" or (
            upload_status == "uploaded" and (proc_status == "succeeded" or not proc_status)
        ):
            return ReconciliationOutcome(
                status="published",
                external_post_id=video_id,
            )

        # Thất bại / bị từ chối
        if upload_status in ("failed", "rejected") or proc_status in ("failed", "terminated"):
            reason = (
                rejection_reason
                or failure_reason
                or proc_failure_reason
                or "Video bị YouTube từ chối hoặc xử lý thất bại"
            )
            return ReconciliationOutcome(
                status="failed",
                error_message=f"YouTube từ chối video: {reason}",
            )

        # Đang xử lý
        return ReconciliationOutcome(
            status="in_progress",
            error_message=f"Video YouTube đang được xử lý (upload_status={upload_status}, proc_status={proc_status})",
        )
