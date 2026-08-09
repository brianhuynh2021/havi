"""/media — Media Library. Upload thẳng lên object storage, API chỉ lưu metadata."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from api.deps import MediaServiceDep, WorkspaceDep
from api.rate_limit import limit_by_workspace
from application.services.media_service import (
    AlreadyCompleted,
    ContentDoesNotMatchType,
    MediaAssetNotFound,
    UnsupportedContentType,
    UploadNotFinished,
)
from core.enums import MediaStatus, MediaType
from core.schemas import MediaAsset, MediaUpdate, MediaUploadRequest, MediaUploadTicket, Page
from domain.policies import rate_limits

router = APIRouter(prefix="/media", tags=["media"])


def _to_schema(asset, media_service: MediaServiceDep) -> MediaAsset:
    return MediaAsset(
        id=asset.id,
        workspace_id=asset.workspace_id,
        url=media_service.public_url(asset),
        filename=asset.filename,
        content_type=asset.content_type,
        type=asset.type,
        tags=asset.tags,
        status=asset.status,
        size_bytes=asset.size_bytes,
        uploaded_at=asset.uploaded_at,
    )


@router.get("", response_model=Page[MediaAsset])
async def list_media(
    workspace_id: WorkspaceDep,
    media_service: MediaServiceDep,
    type: MediaType | None = None,
    status: MediaStatus | None = None,
    tag: str | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
) -> Page[MediaAsset]:
    assets, total = await media_service.list_media(
        workspace_id=workspace_id,
        type=type,
        status=status,
        tag=tag,
        limit=limit,
        offset=offset,
    )
    return Page(
        items=[_to_schema(asset, media_service) for asset in assets],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/upload-ticket",
    response_model=MediaUploadTicket,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        limit_by_workspace("media_ticket", rate_limits.MEDIA_UPLOAD_TICKET)
    ],
)
async def create_upload_ticket(
    payload: MediaUploadRequest, workspace_id: WorkspaceDep, media_service: MediaServiceDep
) -> MediaUploadTicket:
    """Cấp presigned POST. Client upload thẳng lên storage, không đi qua API.

    Dung lượng tối đa được enforce bằng condition `content-length-range` trong
    ticket — storage tự từ chối file quá lớn, API không phải tin client.

    Asset tạo ra ở trạng thái `pending`; gọi `/media/{id}/complete` sau khi upload
    xong để chuyển sang `raw`.
    """
    try:
        result = await media_service.create_upload_ticket(
            workspace_id=workspace_id,
            filename=payload.filename,
            content_type=payload.content_type,
            type=payload.type,
        )
    except UnsupportedContentType as exc:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            f"Không hỗ trợ định dạng {exc.content_type} cho loại {exc.media_type.value}",
        ) from exc
    return MediaUploadTicket(
        asset_id=result.asset.id,
        upload_url=result.ticket.upload_url,
        fields=result.ticket.fields,
        expires_at=result.ticket.expires_at,
    )


@router.post("/{asset_id}/complete", response_model=MediaAsset)
async def complete_upload(
    asset_id: UUID, workspace_id: WorkspaceDep, media_service: MediaServiceDep
) -> MediaAsset:
    """Xác nhận upload xong — API kiểm object có thật trên storage rồi mới đổi status."""
    try:
        asset = await media_service.complete_upload(
            workspace_id=workspace_id, asset_id=asset_id
        )
    except MediaAssetNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy media asset") from exc
    except AlreadyCompleted as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, "Asset này đã upload xong trước đó") from exc
    except UploadNotFinished as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Chưa thấy file trên storage — upload lại hoặc chờ upload xong",
        ) from exc
    except ContentDoesNotMatchType as exc:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Nội dung file không phải {exc.media_type.value} — file đã bị xoá, upload lại",
        ) from exc
    return _to_schema(asset, media_service)


@router.patch("/{asset_id}", response_model=MediaAsset)
async def update_media(
    asset_id: UUID,
    payload: MediaUpdate,
    workspace_id: WorkspaceDep,
    media_service: MediaServiceDep,
) -> MediaAsset:
    try:
        asset = await media_service.update_media(
            workspace_id=workspace_id,
            asset_id=asset_id,
            tags=payload.tags,
            status=payload.status,
        )
    except MediaAssetNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy media asset") from exc
    return _to_schema(asset, media_service)
