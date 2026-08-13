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
    """Số liệu kết quả kinh doanh trong một khoảng thời gian.

    `walk_ins` đếm lead đã chốt (`WON`) chứ không phải một nguồn check-in riêng:
    Havi chưa nối POS, và `WON` là bằng chứng gần nhất mà hệ thống thực sự có
    rằng khách đã tới tiệm. `/analytics` phải nói rõ điều đó ra thay vì để con số
    trông như đếm được từ cửa.
    """

    new_leads: int
    won_leads: int
    closed_leads: int
    returning_customers: int

    @property
    def won_rate(self) -> float:
        if self.closed_leads <= 0:
            return 0.0
        return round(self.won_leads / self.closed_leads, 4)


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
                func.count(Lead.id).filter(
                    Lead.stage.in_((LeadStage.WON, LeadStage.LOST))
                ),
            ).where(*window)
        )
        new_leads, won_leads, closed_leads = totals.one()

        # Khách quay lại = số điện thoại đã từng xuất hiện trước kỳ này. Số điện
        # thoại là khoá duy nhất nhận diện được người thật mà Havi đang có; lead
        # không có số thì không tính, còn hơn đoán theo tên trùng.
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
        )

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
