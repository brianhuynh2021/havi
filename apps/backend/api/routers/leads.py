"""/leads — CRM quản lý khách hàng tiềm năng."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from api.deps import AuthDep, LeadServiceDep, WorkspaceDep
from application.services.lead_service import LeadNotFound
from core.enums import LeadReplyStatus, LeadStage
from core.schemas import Lead, LeadCreate, LeadUpdate, Page

router = APIRouter(prefix="/leads", tags=["leads"])


@router.get("", response_model=Page[Lead])
async def list_leads(
    workspace_id: WorkspaceDep,
    lead_service: LeadServiceDep,
    stage: LeadStage | None = None,
    reply_status: LeadReplyStatus | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
) -> Page[Lead]:
    leads, total = await lead_service.list_leads(
        workspace_id=workspace_id,
        stage=stage,
        reply_status=reply_status,
        limit=limit,
        offset=offset,
    )
    return Page[Lead](items=leads, total=total, limit=limit, offset=offset)


@router.post("", response_model=Lead, status_code=status.HTTP_201_CREATED)
async def create_lead(
    payload: LeadCreate,
    workspace_id: WorkspaceDep,
    lead_service: LeadServiceDep,
    auth: AuthDep,
) -> Lead:
    del auth
    return await lead_service.create_lead(
        workspace_id=workspace_id,
        name=payload.name,
        phone=payload.phone,
        source=payload.source,
        message=payload.message,
    )


@router.patch("/{lead_id}", response_model=Lead)
async def update_lead(
    lead_id: UUID,
    payload: LeadUpdate,
    workspace_id: WorkspaceDep,
    lead_service: LeadServiceDep,
    auth: AuthDep,
) -> Lead:
    del auth
    try:
        return await lead_service.update_lead(
            workspace_id=workspace_id,
            lead_id=lead_id,
            name=payload.name,
            phone=payload.phone,
            stage=payload.stage,
            notes=payload.notes,
        )
    except LeadNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy khách hàng này",
        ) from exc
