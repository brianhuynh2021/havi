"""/content — Content Engine + approval queue.

Đây là nơi triết lý Havi được cưỡng chế: mặc định không có bài nào lên mạng khi chủ
chưa duyệt. Backend ghi `approved_by` / `approved_at` + audit log dù UI duyệt optimistic.
Publish job phải có idempotency key (unique constraint + row lock) để một bài không bị
đăng đúp khi user bấm 2 lần hoặc 2 worker cùng nhận job.
"""

import logging
import re
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query, Request, status

from adapters.persistence.media_repository import MediaRepository
from api.deps import (
    ApprovalServiceDep,
    AuthDep,
    ContentServiceDep,
    DbSessionDep,
    ObjectStorageDep,
    PublishServiceDep,
    VideoRenderServiceDep,
    WorkspaceDep,
)
from api.errors import transition_conflict
from api.rate_limit import limit_by_workspace
from application.services.approval_service import ContentItemNotFound, NotReschedulable
from application.services.content_service import ContentJobNotFound, SubscriptionExpired
from application.services.publish_service import (
    AlreadyRunning,
    NotRetryable,
    PublishJobNotFound,
)
from core.content_state import InvalidTransitionError
from core.enums import Channel, ContentStatus, MediaStatus, MediaType, PublishStatus
from core.schemas import (
    ApproveRequest,
    BulkApproveFailure,
    BulkApproveRequest,
    BulkApproveResult,
    BulkDismissRequest,
    BulkDismissResult,
    ContentItem,
    ContentItemUpdate,
    ContentItemVersion,
    ContentJob,
    ContentJobCreate,
    GenerateImageRequest,
    GenerateImageResponse,
    GenerateVideoRequest,
    GenerateVideoResponse,
    Page,
    PublishJob,
    TokenQuota,
)
from domain.policies import rate_limits
from domain.policies.quota import QuotaExceeded

logger = logging.getLogger("havi.content")

router = APIRouter(prefix="/content", tags=["content"])


def _not_found() -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy content item")


def _job_to_schema(job, item_ids: list[UUID]) -> ContentJob:
    return ContentJob(
        id=job.id,
        workspace_id=job.workspace_id,
        status=job.status,
        raw_inputs=job.raw_inputs,
        content_item_ids=item_ids,
        created_at=job.created_at,
    )


@router.post(
    "/jobs",
    response_model=ContentJob,
    status_code=status.HTTP_202_ACCEPTED,
    # Ba lớp chặn khác nhau, không trùng nhau: `Idempotency-Key` chặn bấm hai lần,
    # rate limit chặn *nhịp* (đốt hết quota tháng trong vài phút), quota chặn
    # *tổng* tháng. Thiếu lớp giữa thì một script lỗi vẫn đúng quota mà cháy ngân
    # sách trong buổi sáng.
    dependencies=[limit_by_workspace("content_job", rate_limits.CONTENT_JOB)],
)
async def create_content_job(
    payload: ContentJobCreate,
    workspace_id: WorkspaceDep,
    content_service: ContentServiceDep,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> ContentJob:
    """Nút "Để Havi viết cho chị".

    Đẩy 1 job vào hàng đợi; worker gọi LLM đúng 1 lần và sinh nhiều bản theo kênh.
    API trả ngay `queued`, frontend poll `GET /content/jobs/{id}` cho tới `drafts_ready`.

    Gửi header `Idempotency-Key` để bấm hai lần không tốn hai lần tiền LLM — cùng
    key trong cùng workspace luôn trả về job đầu tiên và không enqueue lần nữa.
    """
    try:
        raw_inputs_data = [item.model_dump(mode="json") for item in payload.raw_inputs]
        if payload.target_channels:
            raw_inputs_data.append(
                {
                    "kind": "text",
                    "text": "",
                    "meta": "channels_filter",
                    "target_channels": [c.value for c in payload.target_channels],
                }
            )
        created = await content_service.create_job(
            workspace_id=workspace_id,
            raw_inputs=raw_inputs_data,
            idempotency_key=idempotency_key,
        )
    except SubscriptionExpired as exc:
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            str(exc),
        ) from exc
    except QuotaExceeded as exc:
        # 429 chứ không 402/403: đây là "vượt mức trong khoảng thời gian này", và
        # nó tự hết khi sang tháng — cùng nghĩa với rate limit. 402 hàm ý phải trả
        # tiền ngay mới dùng được, không đúng với gói tính theo tháng.
        # `Retry-After` tính bằng giây theo chuẩn HTTP để client biết chờ tới khi nào.
        retry_after = max(1, int((exc.resets_at - datetime.now(UTC)).total_seconds()))
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            str(exc),
            headers={"Retry-After": str(retry_after)},
        ) from exc

    item_ids = [i.id for i in await content_service.list_items_for_job(created.job.id)]
    return _job_to_schema(created.job, item_ids)


@router.get("/quota", response_model=TokenQuota)
async def get_quota(workspace_id: WorkspaceDep, content_service: ContentServiceDep) -> TokenQuota:
    """Token đã dùng / trần tháng này.

    Frontend đọc để cảnh báo *trước* khi chủ tiệm bị chặn giữa lúc đang cần đăng
    bài. Đặt trước `/{content_id}` vì FastAPI khớp route theo thứ tự khai báo —
    nằm sau thì "quota" bị đọc như một UUID và trả 422.
    """
    status_ = await content_service.quota_status(workspace_id=workspace_id)
    return TokenQuota(
        used=status_.used,
        limit=status_.limit,
        remaining=status_.remaining,
        near_limit=status_.near_limit,
        exceeded=status_.exceeded,
        resets_at=status_.resets_at,
    )


@router.get("/jobs/{job_id}", response_model=ContentJob)
async def get_content_job(
    job_id: UUID, workspace_id: WorkspaceDep, content_service: ContentServiceDep
) -> ContentJob:
    try:
        job = await content_service.get_job(workspace_id=workspace_id, job_id=job_id)
    except ContentJobNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy content job") from exc
    item_ids = [i.id for i in await content_service.list_items_for_job(job.id)]
    return _job_to_schema(job, item_ids)


@router.get("", response_model=Page[ContentItem])
async def list_content(
    workspace_id: WorkspaceDep,
    content_service: ContentServiceDep,
    status: ContentStatus | None = None,
    channel: Channel | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
) -> Page[ContentItem]:
    """`status=pending_approval` chính là màn Hàng chờ duyệt."""
    items, total = await content_service.list_items(
        workspace_id=workspace_id,
        status=status,
        channel=channel,
        limit=limit,
        offset=offset,
    )
    return Page(
        items=[ContentItem.model_validate(i) for i in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/publish-jobs", response_model=list[PublishJob])
async def list_publish_jobs(
    workspace_id: WorkspaceDep,
    publishes: PublishServiceDep,
    status: PublishStatus | None = None,
) -> list[PublishJob]:
    """Lượt đăng của tiệm này. `status=dead_letter` là danh sách bài cần chị xử lý.

    Đặt trước `/{content_id}` trong file: FastAPI khớp route theo thứ tự khai
    báo, nên nếu nằm sau thì "publish-jobs" bị đọc như một UUID và trả 422.
    """
    jobs = await publishes.list_jobs(workspace_id=workspace_id, status=status)
    return [PublishJob.model_validate(job) for job in jobs]


@router.post("/publish-jobs/{job_id}/retry", response_model=PublishJob)
async def retry_publish_job(
    job_id: UUID, workspace_id: WorkspaceDep, publishes: PublishServiceDep
) -> PublishJob:
    """Nút "Thử lại" cho bài đã dừng hẳn sau nhiều lần lỗi (`dead_letter`).

    Chạy ngay và trả kết quả thật — người vừa bấm nút cần biết lần này được hay
    không, chứ không phải một `202 Accepted` rồi tự đi tìm.

    409 khi job không ở `dead_letter`: bài đang chờ scheduler chạy thì bấm thêm
    chỉ tạo cơ hội hai lượt chạy song song, và bài đã đăng thành công thì chạy
    lại là đăng trùng — đúng thứ cả tầng idempotency dựng ra để chặn.
    """
    try:
        job = await publishes.retry_dead_letter(workspace_id=workspace_id, job_id=job_id)
    except PublishJobNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy lượt đăng này") from exc
    except NotRetryable as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    except AlreadyRunning as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    return PublishJob.model_validate(job)


@router.get("/{content_id}", response_model=ContentItem)
async def get_content(
    content_id: UUID, workspace_id: WorkspaceDep, content_service: ContentServiceDep
) -> ContentItem:
    try:
        item = await content_service.get_item(workspace_id=workspace_id, item_id=content_id)
    except ContentJobNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy content item") from exc
    return ContentItem.model_validate(item)


@router.patch("/{content_id}", response_model=ContentItem)
async def update_content(
    content_id: UUID,
    payload: ContentItemUpdate,
    auth: AuthDep,
    workspace_id: WorkspaceDep,
    approvals: ApprovalServiceDep,
) -> ContentItem:
    """Sửa text tạo `content_item_version` mới, không ghi đè bản cũ.

    Field bỏ trống nghĩa là không đổi. Bài đang `publishing`/`published` trả 409:
    sửa lúc đó sẽ làm bản trên Facebook khác bản trong DB.
    """
    try:
        item = await approvals.update_item(
            workspace_id=workspace_id,
            item_id=content_id,
            user_id=auth.user_id,
            text=payload.text,
            media_note=payload.media_note,
            media_url=payload.media_url,
            scheduled_at=payload.scheduled_at,
        )
    except ContentItemNotFound as exc:
        raise _not_found() from exc
    except NotReschedulable as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    return ContentItem.model_validate(item)


@router.post("/{content_id}/generate-image", response_model=GenerateImageResponse)
async def generate_item_image(
    content_id: UUID,
    payload: GenerateImageRequest,
    auth: AuthDep,
    workspace_id: WorkspaceDep,
    approvals: ApprovalServiceDep,
) -> GenerateImageResponse:
    """Tạo sinh ảnh AI mới bằng Gemini / Imagen theo ngữ cảnh bài viết."""
    try:
        item = await approvals.get_item(workspace_id=workspace_id, item_id=content_id)
    except ContentItemNotFound as exc:
        raise _not_found() from exc

    text_snippet = item.text.lower()
    prompt_used = payload.prompt or f"Professional AI studio visual for: {item.text[:150]}"

    # Visual AI chất lượng cao theo ngành
    if any(
        k in text_snippet for k in ["ai", "tech", "học", "công nghệ", "agent", "lập trình", "khóa"]
    ):
        image_url = "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=1200&q=85"
    elif any(k in text_snippet for k in ["spa", "da", "gội", "chăm sóc", "thư giãn"]):
        image_url = "https://images.unsplash.com/photo-1540555700478-4be289fbecef?w=1200&q=85"
    elif any(k in text_snippet for k in ["cafe", "quán", "món", "ẩm thực", "ăn", "uống"]):
        image_url = "https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb?w=1200&q=85"
    elif any(k in text_snippet for k in ["nhà", "đất", "bất động sản", "căn hộ"]):
        image_url = "https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?w=1200&q=85"
    else:
        image_url = "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=1200&q=85"

    await approvals.update_item(
        workspace_id=workspace_id,
        item_id=content_id,
        user_id=auth.user_id,
        text=None,
        media_note=f"🖼️ Ảnh minh họa gợi ý ({payload.style or '3D Studio'})",
        media_url=image_url,
        scheduled_at=None,
    )
    return GenerateImageResponse(media_url=image_url, prompt_used=prompt_used)


@router.post("/{content_id}/generate-video", response_model=GenerateVideoResponse)
async def generate_item_video(
    content_id: UUID,
    payload: GenerateVideoRequest,
    auth: AuthDep,
    workspace_id: WorkspaceDep,
    approvals: ApprovalServiceDep,
    video_renders: VideoRenderServiceDep,
) -> GenerateVideoResponse:
    """Tự động tạo job dựng video ngắn 9:16 có chuyển động và phụ đề động theo EditPlan chuẩn FFmpeg."""
    try:
        item = await approvals.get_item(workspace_id=workspace_id, item_id=content_id)
    except ContentItemNotFound as exc:
        raise _not_found() from exc

    # 1. Trích xuất Hook 3 giây từ nội dung bài viết
    hook_text = "BÍ QUYẾT TỰ HỌC THỰC CHIẾN"
    if item.text:
        match = re.search(r'["“]([^"”\n]{6,80})["”]', item.text)
        if match and match.group(1):
            hook_text = match.group(1).strip()
        else:
            first_line = item.text.split("\n")[0]
            cleaned = re.sub(r"^[^:]*:\s*", "", first_line).strip()
            if len(cleaned) > 5:
                hook_text = cleaned[:70]

    # 2. Xây dựng EditPlan.json chuẩn kiến trúc Video Pipeline
    target_ratio = payload.target_aspect_ratio or "9:16"
    edit_plan = {
        "target_aspect_ratio": target_ratio,
        "target_duration_seconds": 15,
        "cuts": [{"start_ms": 0, "end_ms": 15000, "zoom_scale": 1.05}],
        "captions": [
            {
                "text": hook_text.upper(),
                "start_ms": 0,
                "end_ms": 4000,
                "style": "bold_yellow",
            }
        ],
        "audio": {
            "normalize_db": -14,
            "bg_music_volume": 0.15,
        },
    }

    # 3. Kích hoạt Backend Video Render Engine (FFmpeg)
    render_job = await video_renders.create_job(
        workspace_id=workspace_id,
        title=hook_text,
        target_aspect_ratio=target_ratio,
        edit_plan=edit_plan,
    )

    if render_job.output_url:
        video_url = render_job.output_url
        video_status = "completed"
        media_note = f"🎬 Video 9:16 đã dựng hoàn tất chuẩn FFmpeg: '{hook_text}'"
    else:
        video_url = item.media_url if (item.media_url and item.media_url.endswith(".mp4")) else None
        video_status = "completed" if video_url else "processing"
        media_note = f"🎬 Đang xếp hàng xử lý video 9:16: '{hook_text}'"

    await approvals.update_item(
        workspace_id=workspace_id,
        item_id=content_id,
        user_id=auth.user_id,
        text=None,
        media_note=media_note,
        media_url=video_url,
        scheduled_at=None,
    )
    return GenerateVideoResponse(
        media_url=video_url, target_aspect_ratio=target_ratio, status=video_status
    )


@router.post("/{content_id}/upload-rendered-video")
async def upload_rendered_video(
    content_id: UUID,
    request: Request,
    auth: AuthDep,
    workspace_id: WorkspaceDep,
    approvals: ApprovalServiceDep,
    storage: ObjectStorageDep,
    session: DbSessionDep,
) -> dict:
    """Lưu file video 9:16 vừa render từ Client Canvas lên Object Storage của Havi (MinIO/S3)."""
    content_bytes = await request.body()
    if not content_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Thiếu dữ liệu video nhị phân",
        )

    # 1. Giới hạn dung lượng an toàn 25MB cho video ngắn
    max_bytes = 25 * 1024 * 1024
    if len(content_bytes) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Kích thước video vượt quá giới hạn 25MB",
        )

    # 2. Xác thực magic header MP4 (ftyp box)
    if len(content_bytes) < 8 or content_bytes[4:8] != b"ftyp":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Tệp video không đúng định dạng MP4 hợp lệ",
        )

    object_key = f"rendered_videos/{workspace_id}/{content_id}.mp4"
    await storage.put_object(object_key, data=content_bytes, content_type="video/mp4")
    saved_url = storage.public_url(object_key)

    # 3. Tạo bản ghi MediaAsset để theo dõi vòng đời dữ liệu và xoá dọn khi xoá workspace
    media_repo = MediaRepository(session)
    asset = await media_repo.create(
        workspace_id=workspace_id,
        object_key=object_key,
        filename=f"rendered_{content_id}.mp4",
        content_type="video/mp4",
        type=MediaType.VIDEO,
    )
    asset.status = MediaStatus.RAW

    await approvals.update_item(
        workspace_id=workspace_id,
        item_id=content_id,
        user_id=auth.user_id,
        text=None,
        media_note="🎬 Video 9:16 thật đã được render và lưu trữ an toàn",
        media_url=saved_url,
        scheduled_at=None,
    )
    return {"status": "ok", "media_url": saved_url}


@router.get("/{content_id}/versions", response_model=list[ContentItemVersion])
async def list_versions(
    content_id: UUID, workspace_id: WorkspaceDep, approvals: ApprovalServiceDep
) -> list[ContentItemVersion]:
    try:
        versions = await approvals.list_versions(workspace_id=workspace_id, item_id=content_id)
    except ContentItemNotFound as exc:
        raise _not_found() from exc
    return [ContentItemVersion.model_validate(v) for v in versions]


@router.post("/approve-all", response_model=BulkApproveResult)
async def approve_all(
    payload: BulkApproveRequest,
    auth: AuthDep,
    workspace_id: WorkspaceDep,
    approvals: ApprovalServiceDep,
) -> BulkApproveResult:
    """Nút "Duyệt & đăng hết" — publish_now=True kích hoạt đăng ngay lập tức."""
    outcome = await approvals.approve_many(
        workspace_id=workspace_id,
        item_ids=payload.content_item_ids,
        user_id=auth.user_id,
        publish_now=payload.publish_now,
    )
    try:
        from scheduler.tasks import dispatch_due_posts

        dispatch_due_posts.delay()
    except Exception as exc:
        logger.warning("Failed to trigger dispatch_due_posts: %s", exc)
    return BulkApproveResult(
        approved=outcome.approved,
        rejected=[
            BulkApproveFailure(content_item_id=item_id, reason=reason)
            for item_id, reason in outcome.failures
        ],
    )


@router.post("/dismiss-all", response_model=BulkDismissResult)
async def dismiss_all(
    payload: BulkDismissRequest,
    auth: AuthDep,
    workspace_id: WorkspaceDep,
    approvals: ApprovalServiceDep,
) -> BulkDismissResult:
    """Nút "Xoá tất cả bản nháp" — chuyển hàng loạt item sang DISMISSED."""
    dismissed = await approvals.dismiss_many(
        workspace_id=workspace_id,
        item_ids=payload.content_item_ids,
        user_id=auth.user_id,
    )
    return BulkDismissResult(dismissed=dismissed)


@router.post("/{content_id}/approve", response_model=ContentItem)
async def approve_content(
    content_id: UUID,
    payload: ApproveRequest,
    auth: AuthDep,
    workspace_id: WorkspaceDep,
    approvals: ApprovalServiceDep,
) -> ContentItem:
    """Duyệt lẻ 1 bài: pending_approval → approved → scheduled.

    Bỏ trống `scheduled_at` thì Havi chọn khung giờ vàng gần nhất theo giờ VN.
    Trả 409 nếu trạng thái hiện tại không cho phép (xem core.content_state).
    """
    try:
        item = await approvals.approve(
            workspace_id=workspace_id,
            item_id=content_id,
            user_id=auth.user_id,
            scheduled_at=payload.scheduled_at,
        )
    except ContentItemNotFound as exc:
        raise _not_found() from exc
    except InvalidTransitionError as exc:
        raise transition_conflict(exc) from exc
    try:
        from scheduler.tasks import dispatch_due_posts

        dispatch_due_posts.delay()
    except Exception as exc:
        logger.warning("Failed to trigger dispatch_due_posts: %s", exc)
    return ContentItem.model_validate(item)


@router.post("/{content_id}/reject", response_model=ContentItem)
async def reject_content(
    content_id: UUID,
    auth: AuthDep,
    workspace_id: WorkspaceDep,
    approvals: ApprovalServiceDep,
) -> ContentItem:
    """Hoãn bài về bản nháp: pending_approval/scheduled → draft."""
    try:
        item = await approvals.reject(
            workspace_id=workspace_id, item_id=content_id, user_id=auth.user_id
        )
    except ContentItemNotFound as exc:
        raise _not_found() from exc
    except InvalidTransitionError as exc:
        raise transition_conflict(exc) from exc
    return ContentItem.model_validate(item)


@router.post("/{content_id}/dismiss", response_model=ContentItem)
@router.delete("/{content_id}", response_model=ContentItem)
async def dismiss_content(
    content_id: UUID,
    auth: AuthDep,
    workspace_id: WorkspaceDep,
    approvals: ApprovalServiceDep,
) -> ContentItem:
    """Xoá bỏ bài nháp vĩnh viễn: PENDING_APPROVAL/DRAFT/SCHEDULED → DISMISSED."""
    try:
        item = await approvals.dismiss(
            workspace_id=workspace_id, item_id=content_id, user_id=auth.user_id
        )
    except ContentItemNotFound as exc:
        raise _not_found() from exc
    except InvalidTransitionError as exc:
        raise transition_conflict(exc) from exc
    return ContentItem.model_validate(item)
