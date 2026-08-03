"""/content — Content Engine + approval queue.

Đây là nơi triết lý Havi được cưỡng chế: mặc định không có bài nào lên mạng khi chủ
chưa duyệt. Backend ghi `approved_by` / `approved_at` + audit log dù UI duyệt optimistic.
Publish job phải có idempotency key (unique constraint + row lock) để một bài không bị
đăng đúp khi user bấm 2 lần hoặc 2 worker cùng nhận job.
"""

from uuid import UUID

from fastapi import APIRouter, Query, status

from api.deps import AuthDep, WorkspaceDep
from api.errors import NotImplementedEndpoint
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


@router.post("/jobs", response_model=ContentJob, status_code=status.HTTP_202_ACCEPTED)
def create_content_job(payload: ContentJobCreate, auth: AuthDep) -> ContentJob:
    """Nút "Để Havi viết cho chị".

    Đẩy 1 job vào hàng đợi; worker gọi LLM đúng 1 lần và sinh 4-5 bản theo kênh.
    API trả ngay `queued`, frontend poll `GET /content/jobs/{id}` cho tới `drafts_ready`.
    """
    del payload, auth
    raise NotImplementedEndpoint()


@router.get("/jobs/{job_id}", response_model=ContentJob)
def get_content_job(job_id: UUID, workspace_id: WorkspaceDep) -> ContentJob:
    del job_id, workspace_id
    raise NotImplementedEndpoint()


@router.get("", response_model=Page[ContentItem])
def list_content(
    workspace_id: WorkspaceDep,
    status: ContentStatus | None = None,
    channel: Channel | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
) -> Page[ContentItem]:
    """`status=pending_approval` chính là màn Hàng chờ duyệt."""
    del workspace_id, status, channel, limit, offset
    raise NotImplementedEndpoint()


@router.get("/{content_id}", response_model=ContentItem)
def get_content(content_id: UUID, workspace_id: WorkspaceDep) -> ContentItem:
    del content_id, workspace_id
    raise NotImplementedEndpoint()


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
