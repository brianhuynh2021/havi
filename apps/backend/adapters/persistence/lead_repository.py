"""Repository cho Lead — quản lý danh sách khách hàng tiềm năng và CRM state."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.enums import LeadReplyStatus, LeadSource, LeadStage
from domain.models.lead import Lead


@dataclass(frozen=True)
class LeadOutcomes:
    """Số liệu kết quả kinh doanh trong một khoảng thời gian."""

    new_leads: int
    won_leads: int
    closed_leads: int
    returning_customers: int
    total_revenue_vnd: int = 0

    @property
    def won_rate(self) -> float:
        if self.closed_leads <= 0:
            return 0.0
        return round(self.won_leads / self.closed_leads, 4)

    @property
    def average_order_value_vnd(self) -> int:
        if self.won_leads <= 0:
            return 0
        return int(self.total_revenue_vnd / self.won_leads)


class LeadRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def outcomes_in_range(
        self, *, workspace_id: UUID, start: datetime, end: datetime
    ) -> LeadOutcomes:
        """Gom số liệu lead của một kỳ bằng một lượt quét bảng."""
        window = [
            Lead.workspace_id == workspace_id,
            Lead.created_at >= start,
            Lead.created_at < end,
        ]

        totals = await self._session.execute(
            select(
                func.count(Lead.id),
                func.count(Lead.id).filter(Lead.stage == LeadStage.WON),
                func.count(Lead.id).filter(Lead.stage.in_((LeadStage.WON, LeadStage.LOST))),
                func.coalesce(func.sum(Lead.revenue_vnd), 0),
            ).where(*window)
        )
        new_leads, won_leads, closed_leads, total_revenue = totals.one()

        # Khách quay lại = số điện thoại đã từng xuất hiện trước kỳ này.
        earlier_phones = (
            select(Lead.phone)
            .where(
                Lead.workspace_id == workspace_id,
                Lead.created_at < start,
                Lead.phone.is_not(None),
            )
            .scalar_subquery()
        )
        returning = await self._session.execute(
            select(func.count(func.distinct(Lead.phone))).where(
                *window,
                Lead.phone.is_not(None),
                Lead.phone.in_(earlier_phones),
            )
        )

        return LeadOutcomes(
            new_leads=new_leads,
            won_leads=won_leads,
            closed_leads=closed_leads,
            returning_customers=returning.scalar_one(),
            total_revenue_vnd=int(total_revenue),
        )

    async def find_by_phone(self, *, workspace_id: UUID, phone: str) -> Lead | None:
        result = await self._session.execute(
            select(Lead)
            .where(Lead.workspace_id == workspace_id, Lead.phone == phone)
            .order_by(Lead.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def find_by_order_id(self, *, workspace_id: UUID, order_id: str) -> Lead | None:
        result = await self._session.execute(
            select(Lead).where(Lead.workspace_id == workspace_id, Lead.order_id == order_id)
        )
        return result.scalar_one_or_none()

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
        content_item_id: UUID | None = None,
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
            content_item_id=content_item_id,
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
        content_item_id: UUID | None = None,
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
        if content_item_id is not None:
            lead.content_item_id = content_item_id
        await self._session.flush()
        return lead

    async def count_customers_by_channel(
        self, *, workspace_id: UUID, start: datetime, end: datetime
    ) -> dict:
        """Đếm số lead/khách hàng theo channel của bài viết được gắn trực tiếp."""
        from domain.models.content import ContentItem

        result = await self._session.execute(
            select(ContentItem.channel, func.count(func.distinct(Lead.id)))
            .join(ContentItem, Lead.content_item_id == ContentItem.id)
            .where(
                Lead.workspace_id == workspace_id,
                Lead.created_at >= start,
                Lead.created_at < end,
            )
            .group_by(ContentItem.channel)
        )
        return {row[0]: row[1] for row in result.all()}
