"""Application Service cho POS & Sales Attribution (Station 5)."""

from uuid import UUID

from adapters.persistence.event_log_repository import EventLogRepository
from adapters.persistence.lead_repository import LeadRepository
from core.enums import LeadReplyStatus, LeadSource, LeadStage
from core.events import EventLogEntry
from domain.models.lead import Lead
from domain.policies.sales_attribution import PosOrder, format_pos_notes


class SalesService:
    def __init__(
        self,
        *,
        lead_repo: LeadRepository,
        event_repo: EventLogRepository,
    ) -> None:
        self._leads = lead_repo
        self._events = event_repo

    async def ingest_pos_order(self, *, workspace_id: UUID, order: PosOrder) -> Lead:
        """Tiếp nhận đơn hàng POS, đối soát khách hàng, cập nhật stage WON và doanh thu."""
        # 1. Chống trùng theo order_id
        if order.order_id:
            existing_by_order = await self._leads.find_by_order_id(
                workspace_id=workspace_id, order_id=order.order_id
            )
            if existing_by_order:
                return existing_by_order

        # 2. Tìm khách theo số điện thoại
        existing_lead: Lead | None = None
        if order.customer_phone:
            existing_lead = await self._leads.find_by_phone(
                workspace_id=workspace_id, phone=order.customer_phone
            )

        note_entry = format_pos_notes(order)

        if existing_lead:
            new_notes = (
                f"{existing_lead.notes}\n{note_entry}" if existing_lead.notes else note_entry
            )
            lead = await self._leads.update(
                existing_lead,
                stage=LeadStage.WON,
                reply_status=LeadReplyStatus.BOOKED,
                notes=new_notes,
            )
            lead.revenue_vnd = (lead.revenue_vnd or 0) + order.amount_vnd
            lead.order_id = order.order_id or lead.order_id
        else:
            lead = await self._leads.create(
                workspace_id=workspace_id,
                name=order.customer_name,
                phone=order.customer_phone,
                source=LeadSource.POS,
                stage=LeadStage.WON,
                reply_status=LeadReplyStatus.BOOKED,
                notes=note_entry,
            )
            lead.revenue_vnd = order.amount_vnd
            lead.order_id = order.order_id

        await self._events.record(
            EventLogEntry(
                workspace_id=workspace_id,
                job_kind="pos.order_ingested",
                input_summary=f"Order #{order.order_id} ({order.source}) - {order.amount_vnd:,.0f}đ",
                output_summary=f"Lead {lead.id} marked as WON",
            )
        )
        return lead
