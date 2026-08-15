"""Repository cho CRM Re-engagement Nudges."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.enums import CrmMessageStatus, CrmNudgeType
from domain.models.crm_nudge import CrmNudge
from domain.models.lead import Lead


class CrmNudgeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        workspace_id: UUID,
        lead_id: UUID,
        message: str,
        nudge_type: CrmNudgeType = CrmNudgeType.INACTIVE_30_DAYS,
    ) -> CrmNudge:
        nudge = CrmNudge(
            workspace_id=workspace_id,
            lead_id=lead_id,
            message=message,
            nudge_type=nudge_type,
            status=CrmMessageStatus.PENDING_APPROVAL,
        )
        self._session.add(nudge)
        await self._session.flush()
        return nudge

    async def get(self, *, workspace_id: UUID, nudge_id: UUID) -> CrmNudge | None:
        stmt = select(CrmNudge).where(
            CrmNudge.workspace_id == workspace_id,
            CrmNudge.id == nudge_id,
        )
        res = await self._session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_by_workspace(
        self,
        *,
        workspace_id: UUID,
        status: CrmMessageStatus | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[CrmNudge], int]:
        filters = [CrmNudge.workspace_id == workspace_id]
        if status is not None:
            filters.append(CrmNudge.status == status)

        count_stmt = select(func.count(CrmNudge.id)).where(*filters)
        total_res = await self._session.execute(count_stmt)
        total = total_res.scalar_one()

        stmt = (
            select(CrmNudge)
            .where(*filters)
            .order_by(desc(CrmNudge.created_at))
            .limit(limit)
            .offset(offset)
        )
        items_res = await self._session.execute(stmt)
        return list(items_res.scalars().all()), total

    async def mark_sent(self, *, workspace_id: UUID, nudge_id: UUID) -> CrmNudge | None:
        nudge = await self.get(workspace_id=workspace_id, nudge_id=nudge_id)
        if nudge:
            nudge.status = CrmMessageStatus.SENT
            nudge.sent_at = datetime.now(UTC)
            await self._session.flush()
        return nudge

    async def mark_dismissed(self, *, workspace_id: UUID, nudge_id: UUID) -> CrmNudge | None:
        nudge = await self.get(workspace_id=workspace_id, nudge_id=nudge_id)
        if nudge:
            nudge.status = CrmMessageStatus.DISMISSED
            await self._session.flush()
        return nudge

    async def has_recent_nudge_for_lead(self, *, lead_id: UUID, within_days: int = 30) -> bool:
        cutoff = datetime.now(UTC) - timedelta(days=within_days)
        stmt = select(func.count(CrmNudge.id)).where(
            CrmNudge.lead_id == lead_id,
            CrmNudge.created_at >= cutoff,
        )
        res = await self._session.execute(stmt)
        return (res.scalar_one() or 0) > 0

    async def list_inactive_leads(
        self, *, workspace_id: UUID, inactive_days: int = 30
    ) -> list[Lead]:
        cutoff = datetime.now(UTC) - timedelta(days=inactive_days)
        stmt = (
            select(Lead)
            .where(
                Lead.workspace_id == workspace_id,
                Lead.created_at <= cutoff,
            )
            .order_by(desc(Lead.created_at))
        )
        res = await self._session.execute(stmt)
        return list(res.scalars().all())
