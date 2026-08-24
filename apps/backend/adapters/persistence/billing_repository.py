"""Repository cho gói cước và hoá đơn."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.enums import InvoiceStatus, Plan
from domain.models.workspace import Invoice, Workspace


class BillingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def set_plan(
        self, workspace: Workspace, *, plan: Plan, paid_until: datetime | None
    ) -> Workspace:
        """Ghi gói mới. `trial_ends_at` KHÔNG bị chạm tới.

        Giữ nguyên mốc dùng thử là có chủ đích: nó ghi lại việc tiệm này đã dùng
        hết lượt dùng thử của mình. Xoá nó đi khi nâng gói thì hạ gói xuống sau đó
        sẽ trông như một tiệm chưa từng dùng thử.
        """
        workspace.plan = plan
        workspace.paid_until = paid_until
        await self._session.flush()
        return workspace

    async def create_invoice(
        self,
        *,
        workspace_id: UUID,
        plan: Plan,
        amount_vnd: int,
        issued_at: datetime,
        status: InvoiceStatus = InvoiceStatus.PENDING,
    ) -> Invoice:
        invoice = Invoice(
            workspace_id=workspace_id,
            plan=plan,
            amount_vnd=amount_vnd,
            issued_at=issued_at,
            status=status,
        )
        self._session.add(invoice)
        await self._session.flush()
        return invoice

    async def get_invoice(self, invoice_id: UUID, *, for_update: bool = False) -> Invoice | None:
        query = select(Invoice).where(Invoice.id == invoice_id)
        if for_update:
            query = query.with_for_update()
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def find_by_prefix(self, prefix: str) -> Invoice | None:
        """Tìm hoá đơn có UUID bắt đầu bằng prefix (ví dụ 8 ký tự hex)."""
        from sqlalchemy import String, cast

        clean = prefix.replace("-", "").strip()
        if not clean:
            return None
        result = await self._session.execute(
            select(Invoice)
            .where(cast(Invoice.id, String).ilike(f"{clean}%"))
            .order_by(Invoice.issued_at.desc())
        )
        return result.scalars().first()

    async def get_by_gateway_reference(self, reference: str) -> Invoice | None:
        result = await self._session.execute(
            select(Invoice).where(Invoice.gateway_reference == reference)
        )
        return result.scalar_one_or_none()

    async def get_pending_invoice(self, *, workspace_id: UUID, plan: Plan) -> Invoice | None:
        result = await self._session.execute(
            select(Invoice)
            .where(
                Invoice.workspace_id == workspace_id,
                Invoice.plan == plan,
                Invoice.status == InvoiceStatus.PENDING,
            )
            .order_by(Invoice.issued_at.desc())
        )
        return result.scalars().first()

    async def mark_invoice_paid(self, invoice: Invoice, *, gateway_reference: str) -> Invoice:
        invoice.status = InvoiceStatus.PAID
        invoice.gateway_reference = gateway_reference
        await self._session.flush()
        return invoice

    async def list_invoices(
        self, *, workspace_id: UUID, limit: int = 50, offset: int = 0
    ) -> tuple[list[Invoice], int]:
        from sqlalchemy import func

        filters = [Invoice.workspace_id == workspace_id]
        total = await self._session.execute(select(func.count()).where(*filters))
        rows = await self._session.execute(
            select(Invoice)
            .where(*filters)
            .order_by(Invoice.issued_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(rows.scalars().all()), total.scalar_one()
