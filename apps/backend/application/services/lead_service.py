"""Lead service — quản lý CRM khách tiềm năng."""

from uuid import UUID

from adapters.persistence.lead_repository import LeadRepository
from core.enums import LeadReplyStatus, LeadSource, LeadStage
from domain.models.lead import Lead


class LeadNotFound(Exception):
    pass


class LeadService:
    def __init__(self, *, leads: LeadRepository) -> None:
        self._leads = leads

    async def list_leads(
        self,
        *,
        workspace_id: UUID,
        stage: LeadStage | None = None,
        reply_status: LeadReplyStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Lead], int]:
        return await self._leads.list_leads(
            workspace_id=workspace_id,
            stage=stage,
            reply_status=reply_status,
            limit=limit,
            offset=offset,
        )

    async def create_lead(
        self,
        *,
        workspace_id: UUID,
        name: str,
        phone: str | None = None,
        source: LeadSource = LeadSource.FANPAGE,
        message: str | None = None,
        suggested_reply: str | None = None,
    ) -> Lead:
        return await self._leads.create(
            workspace_id=workspace_id,
            name=name,
            phone=phone,
            source=source,
            stage=LeadStage.NEW,
            reply_status=LeadReplyStatus.AWAITING_APPROVAL,
            message=message,
            suggested_reply=suggested_reply,
        )

    async def update_lead(
        self,
        *,
        workspace_id: UUID,
        lead_id: UUID,
        name: str | None = None,
        phone: str | None = None,
        stage: LeadStage | None = None,
        reply_status: LeadReplyStatus | None = None,
        notes: str | None = None,
    ) -> Lead:
        lead = await self._leads.get(workspace_id=workspace_id, lead_id=lead_id)
        if lead is None:
            raise LeadNotFound()

        return await self._leads.update(
            lead,
            name=name,
            phone=phone,
            stage=stage,
            reply_status=reply_status,
            notes=notes,
        )
