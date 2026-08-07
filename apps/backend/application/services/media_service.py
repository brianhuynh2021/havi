"""Use case cho /media — cấp upload ticket, xác nhận upload, quản lý metadata.

Luồng: client xin ticket → PUT/POST thẳng lên object storage (không qua API) →
gọi `/media/{id}/complete` để API xác nhận object có thật rồi mới chuyển
`pending → raw`. Không có bước xác nhận thì mọi ticket cấp ra đều trông như file
đã tồn tại, và Content Engine sẽ đọc phải asset rỗng.
"""

import uuid
from dataclasses import dataclass
from uuid import UUID

from adapters.persistence.media_repository import MediaRepository
from adapters.storage.object_storage import ObjectStorage, UploadTicket
from core.enums import MediaStatus, MediaType
from core.file_signatures import PREFIX_BYTES_NEEDED, matches_media_type
from domain.models.media import MediaAsset

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


class MediaService:
    def __init__(self, *, media: MediaRepository, storage: ObjectStorage) -> None:
        self._media = media
        self._storage = storage

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

        return await self._media.mark_uploaded(asset, size_bytes=stored.size_bytes)

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

    async def _require_asset(self, *, workspace_id: UUID, asset_id: UUID) -> MediaAsset:
        asset = await self._media.get(workspace_id=workspace_id, asset_id=asset_id)
        if asset is None:
            # 404 chứ không 403: không tiết lộ asset có tồn tại ở tenant khác không.
            raise MediaAssetNotFound()
        return asset
