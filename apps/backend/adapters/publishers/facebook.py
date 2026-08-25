"""Adapter đăng bài lên Facebook Page qua Graph API chính thức.

Chỉ dùng API chính thức (ROADMAP §1 nguyên tắc #4) — không crawl, không tự động
hoá trái điều khoản.

**Chế độ Development vẫn đăng thật được.** Người được thêm vào app với vai trò
Admin/Developer/Tester nối được Page của chính họ và đăng bài thật mà không cần
App Review. Đủ cho closed beta 5-10 tiệm: thêm thủ công từng người. App Review +
Business Verification (cần pháp nhân) chỉ bắt buộc khi mở public signup.

Phần quan trọng nhất của file này là `_classify_error`: Graph API trả lỗi kèm
`code`/`error_subcode`, và map sai một mã nghĩa là hoặc retry vô tận một thứ
không bao giờ chạy, hoặc bỏ cuộc trên một lỗi mạng thoáng qua.

Luật ngầm xuyên suốt file: **chỉ retry khi chắc chắn chưa có gì lên Trang.**
Đăng trùng lên tường khách là lỗi không sửa được, nên chỗ nào không chứng minh
được điều đó (Graph trả 2xx mà thiếu ID bài) thì đi dead-letter cho người đối
soát, chứ không thử lại.
"""

import logging
import os
from datetime import UTC, datetime

import httpx

from core.config import Settings
from core.enums import Channel
from domain.ports.publisher import (
    AmbiguousPublishError,
    AuthPermissionError,
    PublisherPort,
    PublishRequest,
    PublishResult,
    ReelStatus,
    TemporaryPublishError,
    ValidationPublishError,
)

logger = logging.getLogger(__name__)

GRAPH_VERSION = "v21.0"
GRAPH_BASE = f"https://graph.facebook.com/{GRAPH_VERSION}"

#: Mã lỗi Graph API nghĩa là token/quyền hỏng — KHÔNG retry, cần nối lại kênh.
#: 190 = token hết hạn hoặc bị thu hồi; 200/10 = thiếu quyền; 102 = phiên hỏng.
_AUTH_CODES = {102, 190, 200, 10}

#: Rate limit và lỗi tạm — retry được. 4 = app quá giới hạn, 17 = user quá giới
#: hạn, 32 = page quá giới hạn, 613 = gọi quá nhanh, 1/2 = lỗi nội bộ Graph.
_TEMPORARY_CODES = {1, 2, 4, 17, 32, 613}


class FacebookPublisher(PublisherPort):
    def __init__(self, settings: Settings, *, timeout_seconds: float = 20.0) -> None:
        self._settings = settings
        self._timeout = timeout_seconds

    @property
    def channel(self) -> Channel:
        return Channel.FACEBOOK_PAGE

    async def publish(self, request: PublishRequest, *, access_token: str) -> PublishResult:
        page_id = request.external_account_id
        if not page_id:
            # Không có Page ID thì không biết đăng lên đâu. Lỗi cấu hình, không
            # phải lỗi mạng — retry vô nghĩa.
            raise ValidationPublishError(
                self.channel, "Kết nối thiếu Page ID. Vào Cài đặt → Kết nối để nối lại."
            )

        # Ảnh và text đi ba đường khác nhau ở Graph API — gộp vào một endpoint
        # là không được:
        #   không ảnh  → /feed với `message`
        #   một ảnh    → /photos với `url` + `caption`
        #   nhiều ảnh  → upload từng ảnh `published=false` lấy media_fbid, rồi
        #                /feed với `attached_media`
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            is_video = bool(
                request.media_urls
                and any(u.endswith((".mp4", ".mov", ".webm")) for u in request.media_urls)
            )
            if (getattr(request, "channel", None) == Channel.REELS) or is_video:
                body = await self._post_reel(client, page_id, request, access_token)
            elif not request.media_urls:
                body = await self._post(
                    client,
                    f"{GRAPH_BASE}/{page_id}/feed",
                    {"message": request.text},
                    access_token,
                )
            elif len(request.media_urls) == 1:
                body = await self._post_photo(
                    client,
                    f"{GRAPH_BASE}/{page_id}/photos",
                    request.media_urls[0],
                    request.text,
                    access_token,
                    published=True,
                )
            else:
                body = await self._post_album(client, page_id, request, access_token)
        # /feed trả `id`, /photos trả `post_id` (và `id` là ID ảnh, không phải
        # bài). Lấy nhầm thì đối soát về sau tra không ra bài.
        external_id = body.get("post_id") or body.get("id")
        if not external_id:
            # Graph trả 2xx tức là bài rất có thể ĐÃ lên Trang, chỉ là Havi
            # không cầm được ID. Retry ở đây là con đường thẳng tới đăng bài
            # thứ hai lên tường khách — lỗi không sửa được (ROADMAP §1 #8).
            # Nên xếp permanent: job vào dead-letter, người vận hành mở Trang
            # đối soát rồi bấm đăng lại nếu thật sự chưa lên.
            logger.error(
                "Graph API 2xx nhưng không có ID bài cho page %s — kiểm tra Trang "
                "xem bài đã lên chưa trước khi đăng lại",
                page_id,
            )
            raise ValidationPublishError(
                self.channel,
                "Facebook không trả mã bài đăng — cần kiểm tra Trang trước khi đăng lại",
            )

        return PublishResult(external_post_id=str(external_id), published_at=datetime.now(UTC))

    async def _post_photo(
        self,
        client: httpx.AsyncClient,
        url: str,
        media_url: str,
        caption: str | None,
        access_token: str,
        published: bool = True,
    ) -> dict:
        """Đăng 1 ảnh lên /photos.

        - Với ảnh local (localhost/127.0.0.1/minio), Facebook server không thể tải URL
          từ máy dev nên Havi đọc bytes local và POST file nhị phân `source`.
        - Với URL công khai, gửi trực tiếp `url` kèm `published` để Facebook tự fetch.
        """
        is_local = any(host in media_url for host in ("localhost", "127.0.0.1", "minio"))
        if is_local:
            try:
                img_res = await client.get(
                    media_url,
                    headers={
                        "User-Agent": (
                            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                        )
                    },
                    follow_redirects=True,
                )
                if img_res.status_code == 200 and len(img_res.content) > 0:
                    content_type = img_res.headers.get("content-type", "image/jpeg")
                    if "html" in content_type:
                        content_type = "image/jpeg"
                    files = {"source": ("image.jpg", img_res.content, content_type)}
                    data = {
                        "access_token": access_token,
                        "published": "true" if published else "false",
                    }
                    if caption:
                        data["caption"] = caption
                    response = await client.post(url, data=data, files=files)
                    if response.status_code < 400:
                        return response.json()
                    logger.error(
                        "Facebook _post_photo failed (%s): %s",
                        response.status_code,
                        response.text,
                    )
                    raise self._classify_error(response)
            except Exception as exc:
                if isinstance(
                    exc,
                    (
                        AmbiguousPublishError,
                        AuthPermissionError,
                        ValidationPublishError,
                        TemporaryPublishError,
                    ),
                ):
                    raise
                logger.warning(
                    "Failed to upload local image bytes, falling back to URL upload: %s", exc
                )

        payload: dict[str, str] = {
            "url": media_url,
        }
        if caption:
            payload["caption"] = caption
        if not published:
            payload["published"] = "false"
        return await self._post(client, url, payload, access_token)

    async def _post_album(
        self,
        client: httpx.AsyncClient,
        page_id: str,
        request: PublishRequest,
        access_token: str,
    ) -> dict:
        """Bài nhiều ảnh: upload ảnh ở dạng chưa publish rồi mới ghép thành bài.

        `published=false` là điểm mấu chốt — ảnh nằm im chờ ghép, không tự hiện
        lên Trang thành nhiều bài rời rạc. Nhờ vậy nếu bước /feed cuối cùng
        hỏng thì chủ tiệm không thấy gì lạ trên Trang, chỉ còn vài ảnh mồ côi
        mà Facebook tự dọn.
        """
        media_ids: list[str] = []
        for media_url in request.media_urls:
            photo = await self._post_photo(
                client,
                f"{GRAPH_BASE}/{page_id}/photos",
                media_url,
                caption=None,
                access_token=access_token,
                published=False,
            )
            photo_id = photo.get("id")
            if not photo_id:
                # Ảnh chưa publish nên chưa có gì lên Trang — retry an toàn.
                raise TemporaryPublishError(
                    self.channel, "Graph API không trả về ID ảnh khi tải ảnh lên"
                )
            media_ids.append(str(photo_id))

        payload = {"message": request.text}
        for index, media_id in enumerate(media_ids):
            # Graph nhận dạng attached_media[0], attached_media[1]…
            payload[f"attached_media[{index}]"] = f'{{"media_fbid":"{media_id}"}}'
        return await self._post(client, f"{GRAPH_BASE}/{page_id}/feed", payload, access_token)

    async def _post_reel(
        self,
        client: httpx.AsyncClient,
        page_id: str,
        request: PublishRequest,
        access_token: str,
    ) -> dict:
        """Đăng Video Reels lên Page qua Reels Publishing API — ba pha.

        `start` → upload bytes tới `rupload.facebook.com` → `finish`. Ranh giới
        quan trọng nhất là sau `start`: từ lúc đó Facebook đã cấp `video_id` và
        mọi lỗi tiếp theo đều **mơ hồ** — có thể video đã lên Trang, có thể chưa.
        Retry ở đó là cách tạo ra hai Reels giống hệt nhau. Vì vậy mọi hỏng hóc
        sau `start` đều là `AmbiguousPublishError`, và người xử lý phải đi đối
        soát chứ không được đăng lại.

        `finish` trả 200 **không** có nghĩa là video đã lên Trang: Reels xử lý
        bất đồng bộ. Việc xác minh nằm ở `verify_reel`.
        """
        init_url = f"{GRAPH_BASE}/{page_id}/video_reels"
        init_res = await client.post(
            init_url,
            data={"upload_phase": "start", "access_token": access_token},
        )
        if init_res.status_code >= 400:
            # Chưa có gì được tạo — phân loại bình thường, retry an toàn.
            raise self._classify_error(init_res)

        init_data = init_res.json()
        video_id = init_data.get("video_id")
        upload_url = init_data.get("upload_url")
        if not video_id or not upload_url:
            raise TemporaryPublishError(
                self.channel,
                "Graph API không trả về video_id/upload_url ở pha start của Reels",
            )

        video_bytes = await self._load_reel_bytes(client, request)
        if not video_bytes:
            # Không có bytes thì không đăng. Trước đây chỗ này rơi về một file
            # mẫu trong /tmp, nghĩa là Trang của khách nhận video của người khác.
            raise ValidationPublishError(
                self.channel,
                "Không đọc được nội dung video để đăng Reels — thiếu file nguồn.",
            )

        try:
            up_res = await client.post(
                upload_url,
                headers={
                    "Authorization": f"OAuth {access_token}",
                    "offset": "0",
                    "file_size": str(len(video_bytes)),
                },
                content=video_bytes,
            )
        except httpx.HTTPError as exc:
            raise AmbiguousPublishError(
                self.channel,
                f"Mất kết nối khi tải video lên Reels (video_id={video_id}): {exc}",
            ) from exc

        if up_res.status_code >= 400:
            logger.error(
                "Facebook Reels binary upload HTTP %d: %s", up_res.status_code, up_res.text[:200]
            )
            raise AmbiguousPublishError(
                self.channel,
                f"Tải video lên Reels hỏng ở HTTP {up_res.status_code} "
                f"(video_id={video_id}) — phải đối soát trước khi thử lại.",
            )

        try:
            finish_res = await client.post(
                init_url,
                data={
                    "upload_phase": "finish",
                    "video_id": video_id,
                    "video_state": "PUBLISHED",
                    "description": request.text,
                    "access_token": access_token,
                },
            )
        except httpx.HTTPError as exc:
            raise AmbiguousPublishError(
                self.channel,
                f"Mất kết nối ở pha finish của Reels (video_id={video_id}): {exc}",
            ) from exc

        if finish_res.status_code >= 400:
            raise AmbiguousPublishError(
                self.channel,
                f"Pha finish của Reels trả HTTP {finish_res.status_code} "
                f"(video_id={video_id}) — phải đối soát trước khi thử lại.",
            )

        # Trả đúng video_id thật. Không bao giờ bịa một id thay thế: id bịa nghĩa
        # là về sau không đối soát được, mà đối soát là thứ duy nhất chặn đăng trùng.
        return {"id": str(video_id), "reel_pending_verification": True}

    async def _load_reel_bytes(
        self, client: httpx.AsyncClient, request: PublishRequest
    ) -> bytes | None:
        """Đọc bytes video từ URL đã ký hoặc đường dẫn cục bộ. `None` = không có."""
        if not request.media_urls:
            return None

        raw_url = request.media_urls[0]
        if raw_url.startswith("file://"):
            local_path = raw_url[len("file://") :]
            if os.path.exists(local_path):
                with open(local_path, "rb") as f:
                    return f.read()
            return None

        if raw_url.startswith(("http://", "https://")):
            try:
                res = await client.get(raw_url)
            except httpx.HTTPError as exc:
                logger.warning("Không tải được video từ %s: %s", raw_url, exc)
                return None
            if res.status_code == 200 and res.content:
                return res.content
            return None

        if os.path.exists(raw_url):
            with open(raw_url, "rb") as f:
                return f.read()
        return None

    async def verify_reel(self, video_id: str, *, access_token: str) -> ReelStatus:
        """Đọc lại trạng thái Reel trên Graph API.

        `finish` trả 200 chỉ nghĩa là Facebook nhận job. Reels xử lý bất đồng bộ
        và có thể hỏng sau đó (video lỗi, vi phạm chính sách). Chỉ khi
        `publishing_phase.status == "published"` mới được coi là đã đăng.
        """
        url = f"{GRAPH_BASE}/{video_id}"
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                res = await client.get(
                    url,
                    params={
                        "fields": "id,status,permalink_url",
                        "access_token": access_token,
                    },
                )
            except httpx.HTTPError as exc:
                raise TemporaryPublishError(
                    self.channel, f"Không đọc được trạng thái Reel {video_id}: {exc}"
                ) from exc

            if res.status_code == 404:
                return ReelStatus(video_id=video_id, phase="not_found")
            if res.status_code >= 400:
                raise self._classify_error(res)

            body = res.json()
            phase_block = (body.get("status") or {}).get("publishing_phase") or {}
            phase = str(phase_block.get("status") or "").lower()
            return ReelStatus(
                video_id=str(body.get("id") or video_id),
                phase=phase or "unknown",
                permalink_url=body.get("permalink_url"),
                error_message=phase_block.get("errors") and str(phase_block["errors"])[:300],
            )

    async def _post(
        self, client: httpx.AsyncClient, url: str, payload: dict, access_token: str
    ) -> dict:
        """POST tới Graph và chuẩn hoá lỗi.

        Token đi trong form body chứ không phải query string: query string nằm
        trong access log của mọi proxy trên đường đi.
        """
        try:
            response = await client.post(url, data={**payload, "access_token": access_token})
        except httpx.TimeoutException as exc:
            # Timeout KHÔNG chứng minh là chưa đăng — Facebook có thể đã nhận.
            # Unique constraint chỉ chặn tạo job thứ hai, không chặn chính job
            # gọi Graph API lần nữa. Vì vậy phải dừng ở reconciliation.
            raise AmbiguousPublishError(
                self.channel, f"Facebook không phản hồi sau {self._timeout}s"
            ) from exc
        except httpx.HTTPError as exc:
            # Chỉ lấy tên loại lỗi, không nội suy `exc` — httpx đưa cả URL vào
            # message, mà URL có thể mang tham số nhạy cảm.
            raise TemporaryPublishError(
                self.channel, f"Lỗi mạng khi gọi Facebook: {type(exc).__name__}"
            ) from exc

        if response.status_code >= 400:
            raise self._classify_error(response)

        try:
            return response.json()
        except ValueError as exc:
            raise TemporaryPublishError(
                self.channel, "Graph API trả dữ liệu không đọc được"
            ) from exc

    def _classify_error(self, response: httpx.Response) -> Exception:
        """Map lỗi Graph API sang ba loại mà worker biết xử.

        Ưu tiên `code` của Graph hơn HTTP status: Graph trả 400 cho cả token
        hết hạn lẫn nội dung bị từ chối, mà hai thứ đó cần xử khác hẳn nhau.
        """
        try:
            error = response.json().get("error", {})
        except ValueError:
            error = {}

        code = error.get("code")
        # Chỉ lấy `error.message`, KHÔNG rơi về `response.text`: body lỗi của
        # Graph đôi khi vọng lại tham số đã gửi, mà tham số đó có `access_token`.
        # Detail này đi thẳng vào `publish_jobs.failure_detail` và log, nên một
        # lần rơi về body thô là token nằm trong DB dưới dạng chữ thường.
        message = str(error.get("message") or "")[:300]
        if not message:
            message = f"Graph API trả HTTP {response.status_code} không kèm mô tả"
        detail = f"[{code}] {message}" if code else message

        if code in _AUTH_CODES:
            return AuthPermissionError(self.channel, detail)
        if code in _TEMPORARY_CODES:
            return TemporaryPublishError(self.channel, detail)

        # HTTP status là lớp phân loại thứ hai khi mã lỗi lạ.
        if response.status_code == 429:
            return TemporaryPublishError(self.channel, detail)
        if response.status_code in (401, 403):
            return AuthPermissionError(self.channel, detail)
        if response.status_code >= 500:
            return TemporaryPublishError(self.channel, detail)

        # Còn lại (400 với mã lạ) coi là lỗi nội dung: retry cùng payload sẽ
        # hỏng y hệt, nên đưa vào dead-letter để người xem.
        logger.warning("Graph API unclassified error: %s", detail)
        return ValidationPublishError(self.channel, detail)
