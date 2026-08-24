"""REST API Router cho Video Render Jobs (Phase 3 Video Pipeline)."""

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from api.deps import ActiveWorkspaceDep, VideoRenderServiceDep, WorkspaceDep
from application.services.video_render_service import VideoRenderJobNotFound
from core.enums import VideoRenderEngine, VideoRenderStatus
from core.request_context import REQUEST_ID_HEADER
from domain.policies.video_edit_plan import InvalidEditPlanError

router = APIRouter(prefix="/workspaces/{workspace_id}/video/render-jobs", tags=["video-render"])


class CreateVideoRenderJobRequest(BaseModel):
    title: str = Field(default="Video ngắn tự động", max_length=200)
    target_aspect_ratio: str = Field(default="9:16", pattern="^(9:16|1:1|16:9)$")
    edit_plan: dict[str, Any] | None = None
    source_media_id: UUID | None = None
    renderer_engine: VideoRenderEngine = VideoRenderEngine.FFMPEG


class VideoRenderJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    title: str
    target_aspect_ratio: str
    status: VideoRenderStatus
    progress_percent: int
    renderer_engine: VideoRenderEngine
    source_media_id: UUID | None = None
    edit_plan: dict[str, Any] = Field(default_factory=dict)
    output_media_id: UUID | None = None
    output_url: str | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime


class ListVideoRenderJobsResponse(BaseModel):
    items: list[VideoRenderJobResponse]
    total: int
    limit: int
    offset: int


@router.post("", response_model=VideoRenderJobResponse, status_code=status.HTTP_201_CREATED)
async def create_render_job(
    req: CreateVideoRenderJobRequest,
    workspace_id: ActiveWorkspaceDep,
    service: VideoRenderServiceDep,
    request_id: str | None = Header(default=None, alias=REQUEST_ID_HEADER),
) -> VideoRenderJobResponse:
    """Tạo một job render video mới và xếp vào hàng đợi `havi.video_render`."""
    try:
        job = await service.create_job(
            workspace_id=workspace_id,
            title=req.title,
            target_aspect_ratio=req.target_aspect_ratio,
            edit_plan=req.edit_plan,
            source_media_id=req.source_media_id,
            renderer_engine=req.renderer_engine,
            request_id=request_id,
        )
        return VideoRenderJobResponse.model_validate(job)
    except InvalidEditPlanError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    except VideoRenderJobNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("", response_model=ListVideoRenderJobsResponse)
async def list_render_jobs(
    workspace_id: WorkspaceDep,
    service: VideoRenderServiceDep,
    job_status: Annotated[VideoRenderStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ListVideoRenderJobsResponse:
    """Lấy danh sách các render jobs của workspace với phân trang."""
    items, total = await service.list_jobs(
        workspace_id=workspace_id,
        status=job_status,
        limit=limit,
        offset=offset,
    )
    return ListVideoRenderJobsResponse(
        items=[VideoRenderJobResponse.model_validate(j) for j in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{job_id}", response_model=VideoRenderJobResponse)
async def get_render_job(
    job_id: UUID,
    workspace_id: WorkspaceDep,
    service: VideoRenderServiceDep,
) -> VideoRenderJobResponse:
    """Kiểm tra tiến độ render (0-100%) và kết quả video đầu ra."""
    try:
        job = await service.get_job(workspace_id=workspace_id, job_id=job_id)
        return VideoRenderJobResponse.model_validate(job)
    except VideoRenderJobNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/{job_id}/retry", response_model=VideoRenderJobResponse)
async def retry_render_job(
    job_id: UUID,
    workspace_id: WorkspaceDep,
    service: VideoRenderServiceDep,
    request_id: str | None = Header(default=None, alias=REQUEST_ID_HEADER),
) -> VideoRenderJobResponse:
    """Thử lại một video render job đã bị thất bại."""
    try:
        job = await service.retry_job(
            workspace_id=workspace_id, job_id=job_id, request_id=request_id
        )
        return VideoRenderJobResponse.model_validate(job)
    except VideoRenderJobNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/{job_id}/cancel")
async def cancel_render_job(
    job_id: UUID,
    workspace_id: WorkspaceDep,
    service: VideoRenderServiceDep,
) -> dict[str, bool]:
    """Huỷ một video render job đang trong hàng đợi."""
    ok = await service.cancel_job(workspace_id=workspace_id, job_id=job_id)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không thể huỷ job (job không tồn tại hoặc đã hoàn tất/thất bại)",
        )
    return {"ok": True}
