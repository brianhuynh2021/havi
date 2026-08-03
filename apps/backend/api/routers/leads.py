"""/leads và /crm-messages — pipeline khách tiềm năng + tin nuôi khách.

Quy tắc copy bắt buộc: câu seeding luôn minh bạch danh tính ("mình là chủ Spa An Nhiên…")
— KHÔNG BAO GIỜ giả danh khách hàng. Ràng buộc này thuộc về prompt trong backend.
Mọi `crm_message` dừng ở `pending_approval` cho tới khi chủ bấm gửi.
"""

from uuid import UUID

from fastapi import APIRouter, Query, status

from api.deps import AuthDep, WorkspaceDep
from api.errors import NotImplementedEndpoint
from core.enums import CrmMessageStatus, LeadStage
from core.schemas import CrmMessage, Lead, LeadCreate, LeadUpdate, Page

router = APIRouter(tags=["leads"])


@router.get("/leads", response_model=Page[Lead])
def list_leads(
    workspace_id: WorkspaceDep,
    stage: LeadStage | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
) -> Page[Lead]:
    del workspace_id, stage, limit, offset
    raise NotImplementedEndpoint()


@router.post("/leads", response_model=Lead, status_code=status.HTTP_201_CREATED)
def create_lead(payload: LeadCreate, auth: AuthDep) -> Lead:
    del payload, auth
    raise NotImplementedEndpoint()


@router.get("/leads/{lead_id}", response_model=Lead)
def get_lead(lead_id: UUID, workspace_id: WorkspaceDep) -> Lead:
    del lead_id, workspace_id
    raise NotImplementedEndpoint()


@router.patch("/leads/{lead_id}", response_model=Lead)
def update_lead(lead_id: UUID, payload: LeadUpdate, auth: AuthDep) -> Lead:
    """Kéo-thả kanban đổi `stage`."""
    del lead_id, payload, auth
    raise NotImplementedEndpoint()


@router.get("/leads/{lead_id}/messages", response_model=list[CrmMessage])
def list_lead_messages(lead_id: UUID, workspace_id: WorkspaceDep) -> list[CrmMessage]:
    del lead_id, workspace_id
    raise NotImplementedEndpoint()


@router.get("/crm-messages", response_model=Page[CrmMessage])
def list_crm_messages(
    workspace_id: WorkspaceDep,
    status: CrmMessageStatus | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
) -> Page[CrmMessage]:
    del workspace_id, status, limit, offset
    raise NotImplementedEndpoint()


@router.post("/crm-messages/{message_id}/send", response_model=CrmMessage)
def send_crm_message(message_id: UUID, auth: AuthDep) -> CrmMessage:
    """Nút "Gửi trả lời này" — chủ duyệt từng tin, không có gửi hàng loạt tự động."""
    del message_id, auth
    raise NotImplementedEndpoint()
