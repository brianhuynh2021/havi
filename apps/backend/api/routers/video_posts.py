"""REST API cho luồng video: tải clip lên → duyệt → đăng lên Facebook Reels.

Havi không dựng và không sửa video (xem `application/services/video_post_service`).
Nên ở đây không có endpoint render, không có retry-render, không có preview bản
dựng — chỉ có vòng đời của một clip đã có sẵn.
"""

import logging
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from api.deps import (
    ActiveWorkspaceDep,
    VideoPostServiceDep,
    VideoPublishServiceDep,
    WorkspaceDep,
)
from application.services.video_post_service import (
    ClipNotPublishable,
    VideoPostNotFound,
)
from application.services.video_publish_service import (
    ChannelNotConnected,
    VideoNotReadyForPublish,
)
from core.enums import Channel, VideoPostStatus
from core.request_context import REQUEST_ID_HEADER

router = APIRouter(prefix="/workspaces/{workspace_id}/video/posts", tags=["video"])

logger = logging.getLogger("havi.api.video_posts")


class CreateVideoPostRequest(BaseModel):
    """Clip phải đã upload xong qua `/media` trước khi gọi endpoint này."""

    source_media_id: UUID
    caption: str = Field(default="", max_length=2200)
    channel: Channel = Channel.REELS


class UpdateVideoPostRequest(BaseModel):
    caption: str = Field(max_length=2200)


class VideoPostResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    caption: str
    channel: Channel
    status: VideoPostStatus
    source_media_id: UUID | None = None
    scheduled_at: datetime | None = None
    error_message: str | None = None
    published_at: datetime | None = None
    created_at: datetime


class ListVideoPostsResponse(BaseModel):
    items: list[VideoPostResponse]
    total: int
    limit: int
    offset: int


class EligibleChannelsResponse(BaseModel):
    """Kênh mà clip vừa upload đăng được — UI hiện ngay, không đợi tới lúc đăng."""

    channels: list[Channel]


def _unprocessable(reasons: list[str]) -> HTTPException:
    """422 kèm nguyên danh sách lý do, để UI hiện hết một lượt."""
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail={"message": "Clip này chưa đăng được", "reasons": reasons},
    )


@router.post("", response_model=VideoPostResponse, status_code=status.HTTP_201_CREATED)
async def create_video_post(
    req: CreateVideoPostRequest,
    workspace_id: ActiveWorkspaceDep,
    service: VideoPostServiceDep,
) -> VideoPostResponse:
    """Đưa một clip đã upload vào hàng chờ duyệt."""
    try:
        post = await service.create_from_upload(
            workspace_id=workspace_id,
            source_media_id=req.source_media_id,
            caption=req.caption,
            channel=req.channel,
        )
    except ClipNotPublishable as exc:
        raise _unprocessable(exc.reasons) from exc
    except VideoPostNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return VideoPostResponse.model_validate(post)


@router.get("", response_model=ListVideoPostsResponse)
async def list_video_posts(
    workspace_id: WorkspaceDep,
    service: VideoPostServiceDep,
    post_status: Annotated[VideoPostStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ListVideoPostsResponse:
    items, total = await service.list(
        workspace_id=workspace_id, status=post_status, limit=limit, offset=offset
    )
    return ListVideoPostsResponse(
        items=[VideoPostResponse.model_validate(p) for p in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/eligible-channels", response_model=EligibleChannelsResponse)
async def eligible_channels_for_clip(
    workspace_id: WorkspaceDep,
    service: VideoPostServiceDep,
    source_media_id: Annotated[UUID, Query()],
) -> EligibleChannelsResponse:
    try:
        channels = await service.channels_for_clip(
            workspace_id=workspace_id, source_media_id=source_media_id
        )
    except VideoPostNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return EligibleChannelsResponse(channels=channels)


@router.get("/{post_id}", response_model=VideoPostResponse)
async def get_video_post(
    post_id: UUID,
    workspace_id: WorkspaceDep,
    service: VideoPostServiceDep,
) -> VideoPostResponse:
    try:
        post = await service.get(workspace_id=workspace_id, post_id=post_id)
    except VideoPostNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return VideoPostResponse.model_validate(post)


@router.patch("/{post_id}", response_model=VideoPostResponse)
async def update_video_post(
    post_id: UUID,
    req: UpdateVideoPostRequest,
    workspace_id: ActiveWorkspaceDep,
    service: VideoPostServiceDep,
) -> VideoPostResponse:
    try:
        post = await service.update_caption(
            workspace_id=workspace_id, post_id=post_id, caption=req.caption
        )
    except ClipNotPublishable as exc:
        raise _unprocessable(exc.reasons) from exc
    except VideoPostNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return VideoPostResponse.model_validate(post)


class ApproveVideoPostRequest(BaseModel):
    """`scheduled_at=None` = gửi ngay ở lượt worker kế tiếp."""

    scheduled_at: datetime | None = None


class ApproveVideoPostResponse(BaseModel):
    post: VideoPostResponse
    queued_for_publish: bool


@router.post("/{post_id}/approve", response_model=ApproveVideoPostResponse)
async def approve_video_post(
    post_id: UUID,
    req: ApproveVideoPostRequest,
    workspace_id: ActiveWorkspaceDep,
    publish_service: VideoPublishServiceDep,
    request_id: str | None = Header(default=None, alias=REQUEST_ID_HEADER),
) -> ApproveVideoPostResponse:
    """Chủ tiệm duyệt → xếp hàng đăng lên Facebook Reels.

    Chỉ chuyển sang `APPROVED` và xếp hàng. Việc gửi bytes và đọc lại nền tảng
    chạy ở worker vì cả hai đều chờ Facebook, và giữ một HTTP request mở trong
    lúc chờ là cách dễ nhất để nhận một timeout không biết đã đăng hay chưa.
    """
    try:
        post = await publish_service.approve(
            workspace_id=workspace_id, post_id=post_id, scheduled_at=req.scheduled_at
        )
    except VideoNotReadyForPublish as exc:
        raise _unprocessable([str(exc)]) from exc
    except ChannelNotConnected as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc

    # Có hẹn giờ thì không xếp hàng ngay: task quét bảng theo `scheduled_at` sẽ
    # nhặt đúng lúc. Xếp hàng ngay ở đây là gửi luôn, tức là bỏ qua giờ đã hẹn.
    if req.scheduled_at is not None:
        return ApproveVideoPostResponse(
            post=VideoPostResponse.model_validate(post), queued_for_publish=False
        )

    queued = False
    try:
        from worker.tasks import publish_video_post

        publish_video_post.apply_async(
            args=[str(workspace_id), str(post_id), request_id],
            queue="havi.video_publish",
        )
        queued = True
    except Exception:  # noqa: BLE001 — Redis offline lúc chạy local/test
        # Không đánh hỏng request: bài đã ở `APPROVED`, worker quét lại sẽ nhặt
        # được. Nhưng phải báo cho UI biết nó chưa vào hàng đợi.
        logger.warning("Không xếp được video %s vào hàng đợi đăng", post_id)

    return ApproveVideoPostResponse(
        post=VideoPostResponse.model_validate(post), queued_for_publish=queued
    )


@router.post("/{post_id}/cancel")
async def cancel_video_post(
    post_id: UUID,
    workspace_id: ActiveWorkspaceDep,
    service: VideoPostServiceDep,
) -> dict[str, bool]:
    """Huỷ một video chưa gửi đi.

    Đã gửi sang Facebook thì không huỷ được: huỷ ở Havi không gỡ bài khỏi Trang,
    nên cho phép huỷ lúc đó chỉ là nói dối chủ tiệm.
    """
    ok = await service.cancel(workspace_id=workspace_id, post_id=post_id)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Không huỷ được: video không tồn tại, hoặc đã gửi đăng rồi.",
        )
    return {"ok": True}
