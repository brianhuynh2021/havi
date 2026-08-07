"""/content — Content Engine + approval queue.

Đây là nơi triết lý Havi được cưỡng chế: mặc định không có bài nào lên mạng khi chủ
chưa duyệt. Backend ghi `approved_by` / `approved_at` + audit log dù UI duyệt optimistic.
Publish job phải có idempotency key (unique constraint + row lock) để một bài không bị
đăng đúp khi user bấm 2 lần hoặc 2 worker cùng nhận job.
"""

from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query, status

from api.deps import AuthDep, ContentServiceDep, WorkspaceDep
from api.errors import NotImplementedEndpoint
from application.services.content_service import ContentJobNotFound
from core.enums import Channel, ContentStatus
from core.schemas import (
    ApproveRequest,
    BulkApproveRequest,
    BulkApproveResult,
    ContentItem,
    ContentItemUpdate,
    ContentItemVersion,
    ContentJob,
    ContentJobCreate,
    Page,
)

router = APIRouter(prefix="/content", tags=["content"])


def _job_to_schema(job, item_ids: list[UUID]) -> ContentJob:
    return ContentJob(
        id=job.id,
        workspace_id=job.workspace_id,
        status=job.status,
        raw_inputs=job.raw_inputs,
        content_item_ids=item_ids,
        created_at=job.created_at,
    )


@router.post("/jobs", response_model=ContentJob, status_code=status.HTTP_202_ACCEPTED)
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
    created = await content_service.create_job(
        workspace_id=workspace_id,
        raw_inputs=[item.model_dump(mode="json") for item in payload.raw_inputs],
        idempotency_key=idempotency_key,
    )
    item_ids = [i.id for i in await content_service.list_items_for_job(created.job.id)]
    return _job_to_schema(created.job, item_ids)


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
def update_content(content_id: UUID, payload: ContentItemUpdate, auth: AuthDep) -> ContentItem:
    """Sửa text tạo `content_item_version` mới, không ghi đè bản cũ."""
    del content_id, payload, auth
    raise NotImplementedEndpoint()


@router.get("/{content_id}/versions", response_model=list[ContentItemVersion])
def list_versions(content_id: UUID, workspace_id: WorkspaceDep) -> list[ContentItemVersion]:
    del content_id, workspace_id
    raise NotImplementedEndpoint()


@router.post("/{content_id}/approve", response_model=ContentItem)
def approve_content(content_id: UUID, payload: ApproveRequest, auth: AuthDep) -> ContentItem:
    """Duyệt lẻ 1 bài: pending_approval → approved → scheduled.

    Trả 409 nếu trạng thái hiện tại không cho phép (xem core.content_state).
    """
    del content_id, payload, auth
    raise NotImplementedEndpoint()


@router.post("/{content_id}/reject", response_model=ContentItem)
def reject_content(content_id: UUID, auth: AuthDep) -> ContentItem:
    """Từ chối: pending_approval → draft."""
    del content_id, auth
    raise NotImplementedEndpoint()


@router.post("/approve-all", response_model=BulkApproveResult)
def approve_all(payload: BulkApproveRequest, auth: AuthDep) -> BulkApproveResult:
    """Nút "Duyệt & đăng hết" — bài nào không duyệt được thì báo lý do, không fail cả lô."""
    del payload, auth
    raise NotImplementedEndpoint()
