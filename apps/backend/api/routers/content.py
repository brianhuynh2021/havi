"""/content — Content Engine + approval queue.

Đây là nơi triết lý Havi được cưỡng chế: mặc định không có bài nào lên mạng khi chủ
chưa duyệt. Backend ghi `approved_by` / `approved_at` + audit log dù UI duyệt optimistic.
Publish job phải có idempotency key (unique constraint + row lock) để một bài không bị
đăng đúp khi user bấm 2 lần hoặc 2 worker cùng nhận job.
"""

import logging
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query, status

from api.deps import (
    ApprovalServiceDep,
    AuthDep,
    ContentServiceDep,
    PublishServiceDep,
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
from core.enums import Channel, ContentStatus, PublishStatus
from core.schemas import (
    ApproveRequest,
    BulkApproveFailure,
    BulkApproveRequest,
    BulkApproveResult,
    ContentItem,
    ContentItemUpdate,
    ContentItemVersion,
    ContentJob,
    ContentJobCreate,
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
        created = await content_service.create_job(
            workspace_id=workspace_id,
            raw_inputs=[item.model_dump(mode="json") for item in payload.raw_inputs],
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
            scheduled_at=payload.scheduled_at,
        )
    except ContentItemNotFound as exc:
        raise _not_found() from exc
    except NotReschedulable as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    return ContentItem.model_validate(item)


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
    """Nút "Duyệt & đăng hết" — bài nào không duyệt được thì báo lý do, không fail cả lô."""
    outcome = await approvals.approve_many(
        workspace_id=workspace_id,
        item_ids=payload.content_item_ids,
        user_id=auth.user_id,
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
    """Từ chối: pending_approval → draft."""
    try:
        item = await approvals.reject(
            workspace_id=workspace_id, item_id=content_id, user_id=auth.user_id
        )
    except ContentItemNotFound as exc:
        raise _not_found() from exc
    except InvalidTransitionError as exc:
        raise transition_conflict(exc) from exc
    return ContentItem.model_validate(item)
