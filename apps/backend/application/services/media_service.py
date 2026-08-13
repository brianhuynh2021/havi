"""Use case cho /media — cấp upload ticket, xác nhận upload, quản lý metadata.

Luồng: client xin ticket → PUT/POST thẳng lên object storage (không qua API) →
gọi `/media/{id}/complete` để API xác nhận object có thật rồi mới chuyển
`pending → raw`. Không có bước xác nhận thì mọi ticket cấp ra đều trông như file
đã tồn tại, và Content Engine sẽ đọc phải asset rỗng.
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass
from uuid import UUID

from adapters.persistence.media_repository import MediaRepository
from adapters.storage.object_storage import ObjectStorage, UploadTicket
from core.enums import MediaStatus, MediaType
from core.file_signatures import PREFIX_BYTES_NEEDED, matches_media_type
from domain.models.media import MediaAsset
from domain.ports.media import VideoMetadata, VideoProcessorPort

logger = logging.getLogger("havi.media")

# Whitelist theo TECHNICAL_SPEC §3 (image|audio|video). Chặn ở đây thay vì tin
# `content_type` client gửi — presigned POST condition sẽ khoá đúng type này.
ALLOWED_CONTENT_TYPES: dict[MediaType, frozenset[str]] = {
    MediaType.IMAGE: frozenset({"image/jpeg", "image/png", "image/webp", "image/heic"}),
    MediaType.AUDIO: frozenset({"audio/mpeg", "audio/mp4", "audio/aac", "audio/wav", "audio/webm"}),
    MediaType.VIDEO: frozenset({"video/mp4", "video/quicktime", "video/webm"}),
}


class UnsupportedContentType(Exception):
    def __init__(self, content_type: str, media_type: MediaType) -> None:
        self.content_type = content_type
        self.media_type = media_type


class MediaAssetNotFound(Exception):
    pass


class UploadNotFinished(Exception):
    """Client gọi complete nhưng object chưa có trên storage."""


class AlreadyCompleted(Exception):
    pass


class ContentDoesNotMatchType(Exception):
    """Bytes thật không khớp loại đã khai — object đã bị xoá khỏi storage."""

    def __init__(self, media_type: MediaType) -> None:
        self.media_type = media_type


@dataclass
class UploadTicketResult:
    asset: MediaAsset
    ticket: UploadTicket


@dataclass(frozen=True)
class ProbedVideo:
    """Kết quả một lượt đọc clip: thông số và ảnh bìa, mỗi thứ tự hỏng riêng.

    Hai trường độc lập vì hai thất bại độc lập: ffprobe đọc được thông số mà
    ffmpeg không xuất được khung hình là chuyện có thật, và ngược lại. Gộp thành
    một `Optional` sẽ khiến một cái hỏng làm mất luôn cái kia.
    """

    metadata: VideoMetadata | None = None
    thumbnail_object_key: str | None = None


class MediaService:
    def __init__(
        self,
        *,
        media: MediaRepository,
        storage: ObjectStorage,
        video: VideoProcessorPort | None = None,
        max_probe_bytes: int = 200 * 1024 * 1024,
    ) -> None:
        self._media = media
        self._storage = storage
        # `None` = không probe. Giữ optional để test hiện có dựng service không
        # cần ffmpeg, và để môi trường không có ffmpeg vẫn upload được.
        self._video = video
        self._max_probe_bytes = max_probe_bytes

    async def create_upload_ticket(
        self, *, workspace_id: UUID, filename: str, content_type: str, type: MediaType
    ) -> UploadTicketResult:
        allowed = ALLOWED_CONTENT_TYPES.get(type, frozenset())
        if content_type not in allowed:
            raise UnsupportedContentType(content_type, type)

        # workspace_id nằm trong object key để một tenant không thể ghi đè file
        # của tenant khác kể cả khi đoán được key.
        object_key = f"{workspace_id}/{uuid.uuid4()}/{filename}"
        asset = await self._media.create(
            workspace_id=workspace_id,
            object_key=object_key,
            filename=filename,
            content_type=content_type,
            type=type,
        )
        ticket = self._storage.create_upload_ticket(
            object_key=object_key, content_type=content_type
        )
        return UploadTicketResult(asset=asset, ticket=ticket)

    async def complete_upload(self, *, workspace_id: UUID, asset_id: UUID) -> MediaAsset:
        asset = await self._require_asset(workspace_id=workspace_id, asset_id=asset_id)
        if asset.status != MediaStatus.PENDING:
            raise AlreadyCompleted()

        stored = await self._storage.head_object(asset.object_key)
        if stored is None:
            raise UploadNotFinished()

        # Presigned POST không kiểm nội dung — object được lưu với Content-Type
        # lấy từ ticket đã ký, kể cả khi bytes là thứ khác hoàn toàn. Bucket media
        # là public-read nên phải kiểm magic bytes ở đây, không thì thành nơi host
        # file tuỳ ý. Xoá object nếu lệch, đừng để rác public trong bucket.
        prefix = await self._storage.read_prefix(
            asset.object_key, num_bytes=PREFIX_BYTES_NEEDED
        )
        if not matches_media_type(prefix, asset.type):
            await self._storage.delete_object(asset.object_key)
            raise ContentDoesNotMatchType(asset.type)

        probed = await self._probe_video(asset, size_bytes=stored.size_bytes)
        return await self._media.mark_uploaded(
            asset,
            size_bytes=stored.size_bytes,
            video=probed.metadata,
            thumbnail_object_key=probed.thumbnail_object_key,
        )

    async def _probe_video(self, asset: MediaAsset, *, size_bytes: int) -> ProbedVideo:
        """Đọc thông số clip và trích ảnh bìa ngay lúc upload xong.

        Kiểm sớm để chủ tiệm biết clip quay ngang / dài quá ngay lúc còn quay lại
        được, thay vì phát hiện lúc scheduler gọi API nền tảng và đã lỡ giờ đăng
        (`domain/policies/video_constraints.py`).

        Không đọc được thì trả `None` và asset vẫn `RAW`: probe hỏng là sự cố vận
        hành của Havi, không phải lỗi của người dùng, nên không được làm hỏng một
        lần upload đã thành công. Thông số NULL sẽ khiến kiểm ràng buộc kênh từ
        chối một cách rõ ràng thay vì đoán bừa.

        Đọc bytes đúng một lượt cho cả probe và ảnh bìa: clip có thể tới hàng trăm
        MB và tải về hai lần chỉ để lấy thêm một khung hình là trả giá gấp đôi cho
        thứ phụ.
        """
        if asset.type is not MediaType.VIDEO or self._video is None:
            return ProbedVideo()
        if not self._video.is_available:
            return ProbedVideo()
        if size_bytes > self._max_probe_bytes:
            logger.warning(
                "media.probe_skipped_too_large object_key=%s size_bytes=%d",
                asset.object_key,
                size_bytes,
            )
            return ProbedVideo()

        try:
            data = await self._storage.read_object(asset.object_key)
            metadata = await asyncio.to_thread(
                self._video.probe_bytes, data, asset.filename
            )
        except Exception:
            logger.exception("media.probe_failed object_key=%s", asset.object_key)
            return ProbedVideo()

        thumbnail_key = await self._store_thumbnail(asset, data)
        return ProbedVideo(metadata=metadata, thumbnail_object_key=thumbnail_key)

    async def _store_thumbnail(self, asset: MediaAsset, data: bytes) -> str | None:
        """Trích một khung hình rồi ghi cạnh clip. `None` khi không lấy được.

        Ảnh bìa hoàn toàn là tiện lợi cho UI, nên mọi thất bại ở đây đều nuốt vào
        log: một lần upload thành công không được đổ vì Havi không lấy được ảnh
        xem trước. Key nằm cạnh object gốc nên vẫn mang tiền tố `workspace_id` —
        cùng cách chống ghi đè chéo tenant như `create_upload_ticket`.
        """
        if self._video is None:
            return None
        try:
            frame = await asyncio.to_thread(
                self._video.thumbnail_bytes, data, asset.filename
            )
            if frame is None:
                return None
            thumbnail_key = f"{asset.object_key}.thumb.jpg"
            await self._storage.put_object(
                thumbnail_key, data=frame, content_type="image/jpeg"
            )
            return thumbnail_key
        except Exception:
            logger.exception("media.thumbnail_failed object_key=%s", asset.object_key)
            return None

    async def list_media(
        self,
        *,
        workspace_id: UUID,
        type: MediaType | None,
        status: MediaStatus | None,
        tag: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[MediaAsset], int]:
        return await self._media.list_for_workspace(
            workspace_id=workspace_id,
            type=type,
            status=status,
            tag=tag,
            limit=limit,
            offset=offset,
        )

    async def update_media(
        self,
        *,
        workspace_id: UUID,
        asset_id: UUID,
        tags: list[str] | None,
        status: MediaStatus | None,
    ) -> MediaAsset:
        asset = await self._require_asset(workspace_id=workspace_id, asset_id=asset_id)
        return await self._media.update(asset, tags=tags, status=status)

    def public_url(self, asset: MediaAsset) -> str:
        return self._storage.public_url(asset.object_key)

    def public_url_for_key(self, object_key: str) -> str:
        """URL cho object không phải asset gốc — hiện chỉ có ảnh bìa video."""
        return self._storage.public_url(object_key)

    async def _require_asset(self, *, workspace_id: UUID, asset_id: UUID) -> MediaAsset:
        asset = await self._media.get(workspace_id=workspace_id, asset_id=asset_id)
        if asset is None:
            # 404 chứ không 403: không tiết lộ asset có tồn tại ở tenant khác không.
            raise MediaAssetNotFound()
        return asset
