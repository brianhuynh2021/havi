"""Use case cho /billing — gói hiện tại, checkout VietQR và hoá đơn.

`POST /billing/plan` chỉ là tiện ích local. Ở production, gói chỉ được kích hoạt
sau webhook PayOS/VietQR có chữ ký hợp lệ, số tiền/tiền tệ khớp chính xác và mã
giao dịch duy nhất; việc cập nhật invoice/workspace chạy dưới row lock.
"""

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from adapters.payment.payos_gateway import (
    VietQRCheckout,
    create_payos_payment_link,
)
from adapters.persistence.billing_repository import BillingRepository
from adapters.persistence.event_log_repository import EventLogRepository
from adapters.persistence.workspace_repository import WorkspaceRepository
from core.config import Settings
from core.enums import BillingCycle, InvoiceStatus, Plan
from core.events import EventLogEntry
from domain.models.workspace import Invoice
from domain.policies import quota, subscription

logger = logging.getLogger("havi.billing")

BILLING_PERIOD_DAYS = 30


class WorkspaceNotFound(Exception):
    pass


class InvoiceNotFound(Exception):
    pass


class UnderpaidInvoiceError(Exception):
    """Số tiền hoặc tiền tệ không khớp chính xác với hoá đơn."""


class InvoiceInvalidStatusError(Exception):
    """Trạng thái hoá đơn không hợp lệ để thanh toán."""


class DuplicatePaymentReferenceError(Exception):
    """Mã giao dịch cổng thanh toán đã được dùng cho hoá đơn khác."""


class BillingService:
    def __init__(
        self,
        *,
        billing: BillingRepository,
        workspaces: WorkspaceRepository,
        events: EventLogRepository,
    ) -> None:
        self._billing = billing
        self._workspaces = workspaces
        self._events = events

    async def subscription_state(
        self, *, workspace_id: UUID, now: datetime | None = None
    ) -> tuple[subscription.SubscriptionState, quota.QuotaStatus]:
        """Gói hiện tại kèm quota đã dùng — hai thứ màn Gói cước cần cùng lúc."""
        now = now or datetime.now(UTC)
        workspace = await self._workspaces.get_by_id(workspace_id)
        if workspace is None:
            raise WorkspaceNotFound()

        state = subscription.state_for(
            plan=workspace.plan,
            trial_ends_at=_as_utc(workspace.trial_ends_at),
            paid_until=_as_utc(workspace.paid_until),
            now=now,
        )
        used = await self._events.tokens_used_since(
            workspace_id=workspace_id, since=quota.month_start_utc(now)
        )
        return state, quota.evaluate(plan=workspace.plan, used=used, now=now)

    async def change_plan(
        self,
        *,
        workspace_id: UUID,
        target: Plan,
        cycle: BillingCycle = BillingCycle.MONTHLY,
        extra_seats: int = 0,
        extra_channels: int = 0,
        now: datetime | None = None,
    ) -> tuple[subscription.SubscriptionState, Invoice]:
        """Yêu cầu đổi gói và phát hành hoá đơn `PENDING`.

        Ném `PlanChangeNotAllowed` khi đổi sang gói đang dùng hoặc quay về trial.
        Hoá đơn ở `PENDING` chứ không `PAID`: chỉ tạo hoá đơn để thanh toán qua VietQR/PayOS.
        Gói chỉ được nâng cấp và kích hoạt khi webhook thanh toán xác thực thành công.
        """
        now = now or datetime.now(UTC)
        workspace = await self._workspaces.get_by_id(workspace_id)
        if workspace is None:
            raise WorkspaceNotFound()

        current = workspace.plan
        subscription.check_plan_change(current=current, target=target)

        amount = subscription.invoice_amount(
            plan=target,
            cycle=cycle,
            extra_seats=extra_seats,
            extra_channels=extra_channels,
        )
        invoice = await self._billing.create_invoice(
            workspace_id=workspace_id,
            plan=target,
            amount_vnd=amount,
            issued_at=now,
            status=InvoiceStatus.PENDING,
            billing_cycle=cycle,
            extra_seats=extra_seats,
            extra_channels=extra_channels,
        )

        # Ghi nhận yêu cầu đổi gói vào audit log
        await self._events.record(
            EventLogEntry(
                workspace_id=workspace_id,
                job_kind="billing.plan_change_requested",
                input_summary=f"{current.value} -> {target.value}",
                output_summary=(
                    f"invoice:{invoice.id} amount_vnd:{amount} "
                    f"cycle:{cycle.value} seats:+{extra_seats} channels:+{extra_channels} "
                    f"status:{invoice.status.value}"
                ),
            )
        )

        state = subscription.state_for(
            plan=workspace.plan,
            trial_ends_at=_as_utc(workspace.trial_ends_at),
            paid_until=_as_utc(workspace.paid_until),
            now=now,
        )
        return state, invoice

    async def get_invoice(self, *, invoice_id: UUID) -> Invoice | None:
        return await self._billing.get_invoice(invoice_id)

    async def get_invoice_by_code(self, *, code: str) -> Invoice | None:
        """Tìm hoá đơn qua mã UUID hoặc 8 ký tự hex rút gọn."""
        try:
            full_id = UUID(code)
            return await self._billing.get_invoice(full_id)
        except ValueError:
            return await self._billing.find_by_prefix(code)

    async def create_checkout(
        self,
        *,
        workspace_id: UUID,
        target: Plan,
        settings: Settings,
        cycle: BillingCycle = BillingCycle.MONTHLY,
        extra_seats: int = 0,
        extra_channels: int = 0,
        now: datetime | None = None,
    ) -> tuple[Invoice, VietQRCheckout]:
        """Tạo hoá đơn PENDING và mã VietQR cho gói, chu kỳ và phụ phí mong muốn."""
        now = now or datetime.now(UTC)
        workspace = await self._workspaces.get_by_id(workspace_id)
        if workspace is None:
            raise WorkspaceNotFound()

        subscription.check_plan_change(current=workspace.plan, target=target)
        amount = subscription.invoice_amount(
            plan=target, cycle=cycle, extra_seats=extra_seats, extra_channels=extra_channels
        )

        # Dùng lại hoá đơn PENDING **chỉ khi số tiền khớp**. Đổi chu kỳ hay đổi số
        # ghế ra một số tiền khác, nên hoá đơn cũ không còn mô tả đúng thứ khách
        # đang mua — và mã VietQR gắn với số tiền đó sẽ thu sai.
        pending = await self._billing.get_pending_invoice(workspace_id=workspace_id, plan=target)
        if pending is None or pending.amount_vnd != amount:
            pending = await self._billing.create_invoice(
                workspace_id=workspace_id,
                plan=target,
                amount_vnd=amount,
                issued_at=now,
                status=InvoiceStatus.PENDING,
                billing_cycle=cycle,
                extra_seats=extra_seats,
                extra_channels=extra_channels,
            )

        checkout = await create_payos_payment_link(
            settings=settings,
            invoice_id=pending.id,
            amount_vnd=amount,
        )
        return pending, checkout

    async def process_payment_success(
        self,
        *,
        invoice_id: UUID,
        gateway_reference: str,
        amount_paid_vnd: int,
        currency: str = "VND",
        now: datetime | None = None,
    ) -> Invoice:
        """Xử lý webhook thanh toán thành công: nâng gói, kích hoạt 30 ngày, đổi status sang PAID."""
        now = now or datetime.now(UTC)
        invoice = await self._billing.get_invoice(invoice_id, for_update=True)
        if invoice is None:
            raise InvoiceNotFound(f"Invoice {invoice_id} not found")

        # Idempotency: nếu đã PAID từ trước thì không cộng dồn thêm lần nữa
        if invoice.status == InvoiceStatus.PAID:
            logger.info("Hoá đơn %s đã ở trạng thái PAID (idempotent)", invoice_id)
            return invoice

        if invoice.status != InvoiceStatus.PENDING:
            logger.warning(
                "Hoá đơn %s có trạng thái %s không thể thanh toán",
                invoice_id,
                invoice.status,
            )
            raise InvoiceInvalidStatusError(
                f"Hoá đơn {invoice_id} đang ở trạng thái {invoice.status.value}"
            )

        normalized_reference = gateway_reference.strip()
        if not normalized_reference:
            raise InvoiceInvalidStatusError("Giao dịch thiếu mã tham chiếu duy nhất")

        existing_reference = await self._billing.get_by_gateway_reference(normalized_reference)
        if existing_reference is not None and existing_reference.id != invoice.id:
            raise DuplicatePaymentReferenceError("Mã giao dịch đã được dùng cho một hoá đơn khác")

        # Đối chiếu chính xác số tiền và VND. Không chấp nhận cả thiếu lẫn thừa:
        # một webhook bị gắn nhầm invoice vẫn có thể có số tiền lớn hơn.
        if currency.upper() != "VND" or amount_paid_vnd != invoice.amount_vnd:
            logger.warning(
                "Thanh toán không khớp hoá đơn %s: nhận %s %s, cần %s VND",
                invoice_id,
                amount_paid_vnd,
                currency,
                invoice.amount_vnd,
            )
            await self._events.record(
                EventLogEntry(
                    workspace_id=invoice.workspace_id,
                    job_kind="billing.payment_mismatch_alert",
                    input_summary=(
                        f"gateway_ref:{normalized_reference} amount:{amount_paid_vnd} "
                        f"currency:{currency.upper()} expected:{invoice.amount_vnd} VND"
                    ),
                    output_summary=(
                        f"invoice:{invoice.id} status:{invoice.status.value} REJECTED_MISMATCH"
                    ),
                )
            )
            raise UnderpaidInvoiceError("Số tiền hoặc tiền tệ không khớp chính xác với hoá đơn")

        workspace = await self._workspaces.get_by_id_for_update(invoice.workspace_id)
        if workspace is None:
            raise WorkspaceNotFound()

        current_paid = _as_utc(workspace.paid_until)
        base_time = current_paid if current_paid and current_paid > now else now
        # Kéo hạn theo số tháng **được dùng**, không theo số tháng thu tiền: gói
        # năm thu 10 tháng nhưng phục vụ 12. Lấy nhầm con số kia là bán 12 tháng
        # rồi chỉ cấp 10.
        served = subscription.months_served(invoice.billing_cycle)
        new_paid_until = base_time + timedelta(days=BILLING_PERIOD_DAYS * served)

        await self._billing.set_plan(
            workspace,
            plan=invoice.plan,
            paid_until=new_paid_until,
            billing_cycle=invoice.billing_cycle,
            extra_seats=invoice.extra_seats,
            extra_channels=invoice.extra_channels,
        )
        updated_invoice = await self._billing.mark_invoice_paid(
            invoice, gateway_reference=normalized_reference
        )

        await self._events.record(
            EventLogEntry(
                workspace_id=workspace.id,
                job_kind="billing.payment_received",
                input_summary=f"gateway_ref:{normalized_reference} amount:{amount_paid_vnd} VND",
                output_summary=(
                    f"invoice:{invoice.id} plan:{invoice.plan.value} "
                    f"paid_until:{new_paid_until.isoformat()}"
                ),
            )
        )
        return updated_invoice

    async def list_invoices(
        self, *, workspace_id: UUID, limit: int, offset: int
    ) -> tuple[list[Invoice], int]:
        return await self._billing.list_invoices(
            workspace_id=workspace_id, limit=limit, offset=offset
        )


def _as_utc(value: datetime | None) -> datetime | None:
    """Gắn UTC cho datetime naive đọc từ Postgres.

    Các cột này là `TIMESTAMP WITHOUT TIME ZONE`, nên driver trả về datetime naive
    và so sánh với `datetime.now(UTC)` sẽ ném `TypeError`. Giá trị luôn được ghi
    bằng UTC, nên gắn nhãn UTC là đúng chứ không phải đoán.
    """
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=UTC)
