"""API Router cho CRM Lifecycle Nudges (Chăm sóc khách cũ tự động)."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from api.deps import AuthDep, CrmNudgeServiceDep, WorkspaceDep
from application.services.crm_nudge_service import CrmNudgeNotFound
from core.enums import CrmMessageStatus, CrmNudgeType

router = APIRouter(prefix="/workspaces/{workspace_id}/crm/nudges", tags=["crm-nudges"])


class CrmNudgeResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    lead_id: UUID
    nudge_type: CrmNudgeType
    status: CrmMessageStatus
    message: str
    created_at: datetime
    sent_at: datetime | None

    model_config = {"from_attributes": True}


class CrmNudgeListResponse(BaseModel):
    items: list[CrmNudgeResponse]
    total: int


@router.get("", response_model=CrmNudgeListResponse)
async def list_nudges(
    auth: AuthDep,
    workspace_id: WorkspaceDep,
    service: CrmNudgeServiceDep,
    status_filter: CrmMessageStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> CrmNudgeListResponse:
    """Lấy danh sách tin nhắn chăm sóc khách hàng định kỳ."""
    items, total = await service.list_nudges(
        workspace_id=workspace_id,
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    return CrmNudgeListResponse(
        items=[CrmNudgeResponse.model_validate(n) for n in items],
        total=total,
    )


@router.post("/scan", response_model=list[CrmNudgeResponse])
async def trigger_nudge_scan(
    auth: AuthDep,
    workspace_id: WorkspaceDep,
    service: CrmNudgeServiceDep,
    inactive_days: int = Query(default=30, ge=7, le=180),
) -> list[CrmNudgeResponse]:
    """Chủ động kích hoạt quét khách hàng cũ để tạo tin nhắn chăm sóc."""
    nudges = await service.scan_and_generate_nudges(
        workspace_id=workspace_id, inactive_days=inactive_days
    )
    return [CrmNudgeResponse.model_validate(n) for n in nudges]


@router.post("/{nudge_id}/approve", response_model=CrmNudgeResponse)
async def approve_nudge(
    nudge_id: UUID,
    auth: AuthDep,
    workspace_id: WorkspaceDep,
    service: CrmNudgeServiceDep,
) -> CrmNudgeResponse:
    """Duyệt và gửi tin nhắn chăm sóc tới khách hàng."""
    try:
        nudge = await service.approve_and_send(workspace_id=workspace_id, nudge_id=nudge_id)
        return CrmNudgeResponse.model_validate(nudge)
    except CrmNudgeNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/{nudge_id}/dismiss", response_model=CrmNudgeResponse)
async def dismiss_nudge(
    nudge_id: UUID,
    auth: AuthDep,
    workspace_id: WorkspaceDep,
    service: CrmNudgeServiceDep,
) -> CrmNudgeResponse:
    """Bỏ qua tin nhắn chăm sóc khách hàng."""
    try:
        nudge = await service.dismiss(workspace_id=workspace_id, nudge_id=nudge_id)
        return CrmNudgeResponse.model_validate(nudge)
    except CrmNudgeNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
