"""Repository cho Lead — quản lý danh sách khách hàng tiềm năng và CRM state."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.enums import LeadReplyStatus, LeadSource, LeadStage
from domain.models.lead import Lead


class LeadRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, *, workspace_id: UUID, lead_id: UUID) -> Lead | None:
        result = await self._session.execute(
            select(Lead).where(
                Lead.id == lead_id,
                Lead.workspace_id == workspace_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        workspace_id: UUID,
        name: str,
        phone: str | None = None,
        source: LeadSource = LeadSource.FANPAGE,
        stage: LeadStage = LeadStage.NEW,
        reply_status: LeadReplyStatus = LeadReplyStatus.NEW,
        message: str | None = None,
        suggested_reply: str | None = None,
        notes: str | None = None,
    ) -> Lead:
        lead = Lead(
            workspace_id=workspace_id,
            name=name,
            phone=phone,
            source=source,
            stage=stage,
            reply_status=reply_status,
            message=message,
            suggested_reply=suggested_reply,
            notes=notes,
        )
        self._session.add(lead)
        await self._session.flush()
        return lead

    async def list_leads(
        self,
        *,
        workspace_id: UUID,
        stage: LeadStage | None = None,
        reply_status: LeadReplyStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Lead], int]:
        filters = [Lead.workspace_id == workspace_id]
        if stage is not None:
            filters.append(Lead.stage == stage)
        if reply_status is not None:
            filters.append(Lead.reply_status == reply_status)

        total = await self._session.execute(select(func.count()).where(*filters))
        rows = await self._session.execute(
            select(Lead)
            .where(*filters)
            .order_by(Lead.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(rows.scalars().all()), total.scalar_one()

    async def update(
        self,
        lead: Lead,
        *,
        name: str | None = None,
        phone: str | None = None,
        stage: LeadStage | None = None,
        reply_status: LeadReplyStatus | None = None,
        notes: str | None = None,
    ) -> Lead:
        if name is not None:
            lead.name = name
        if phone is not None:
            lead.phone = phone
        if stage is not None:
            lead.stage = stage
        if reply_status is not None:
            lead.reply_status = reply_status
        if notes is not None:
            lead.notes = notes
        await self._session.flush()
        return lead
