"""/media — Media Library. Upload thẳng lên object storage, API chỉ lưu metadata."""

from uuid import UUID

from fastapi import APIRouter, Query, status

from api.deps import WorkspaceDep
from api.errors import NotImplementedEndpoint
from core.enums import MediaStatus, MediaType
from core.schemas import MediaAsset, MediaUpdate, MediaUploadRequest, MediaUploadTicket, Page

router = APIRouter(prefix="/media", tags=["media"])


@router.get("", response_model=Page[MediaAsset])
def list_media(
    workspace_id: WorkspaceDep,
    type: MediaType | None = None,
    status: MediaStatus | None = None,
    tag: str | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
) -> Page[MediaAsset]:
    del workspace_id, type, status, tag, limit, offset
    raise NotImplementedEndpoint()


@router.post(
    "/upload-ticket", response_model=MediaUploadTicket, status_code=status.HTTP_201_CREATED
)
def create_upload_ticket(
    payload: MediaUploadRequest, workspace_id: WorkspaceDep
) -> MediaUploadTicket:
    """Cấp presigned URL. Client PUT thẳng lên storage, không đi qua API."""
    del payload, workspace_id
    raise NotImplementedEndpoint()


@router.patch("/{asset_id}", response_model=MediaAsset)
def update_media(asset_id: UUID, payload: MediaUpdate, workspace_id: WorkspaceDep) -> MediaAsset:
    del asset_id, payload, workspace_id
    raise NotImplementedEndpoint()
