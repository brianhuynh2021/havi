"""Use case cho /billing — xem gói hiện tại, đổi gói, tra hoá đơn.

**Chưa có cổng thanh toán.** Đổi gói ở đây phát hành một hoá đơn `PENDING` và
chuyển gói ngay; không có đồng nào được thu. Đó là một quyết định có ý thức, chứ
không phải nửa vời bị bỏ quên: hạ tầng VNPay/Momo cần merchant ID thật mới viết
và verify được, và một adapter không chạy được với endpoint thật là adapter không
kiểm chứng được — đúng sai lầm `GoogleBusinessPublisher` đã mắc một lần
(ROADMAP §13.2 gap E).

Hệ quả phải nói thẳng: cho tới khi có cổng thanh toán, `POST /billing/plan` là
đường nâng gói **không mất tiền**. Vì thế nó bị khoá ngoài `HAVI_ENV=local` y như
mọi fake mode khác, và mỗi lượt đổi gói ghi một event `billing.plan_changed`.
"""

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from adapters.persistence.billing_repository import BillingRepository
from adapters.persistence.event_log_repository import EventLogRepository
from adapters.persistence.workspace_repository import WorkspaceRepository
from core.enums import InvoiceStatus, Plan
from core.events import EventLogEntry
from domain.models.workspace import Invoice
from domain.policies import quota, subscription

logger = logging.getLogger("havi.billing")

#: Một kỳ trả tiền. 30 ngày chứ không "1 tháng dương lịch" để mọi kỳ dài bằng
#: nhau — quota thì theo tháng dương lịch (`quota.month_start_utc`) vì chủ tiệm
#: hiểu "mùng 1 có lại", còn kỳ thanh toán thì phải công bằng về số ngày.
BILLING_PERIOD_DAYS = 30


class WorkspaceNotFound(Exception):
    pass


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
        self, *, workspace_id: UUID, target: Plan, now: datetime | None = None
    ) -> tuple[subscription.SubscriptionState, Invoice]:
        """Đổi gói và phát hành hoá đơn `PENDING`.

        Ném `PlanChangeNotAllowed` khi đổi sang gói đang dùng hoặc quay về trial.
        Hoá đơn ở `PENDING` chứ không `PAID`: chưa nhận được tiền thì không được
        ghi là đã trả.
        """
        now = now or datetime.now(UTC)
        workspace = await self._workspaces.get_by_id(workspace_id)
        if workspace is None:
            raise WorkspaceNotFound()

        current = workspace.plan
        subscription.check_plan_change(current=current, target=target)

        amount = subscription.price_for(target)
        paid_until = now + timedelta(days=BILLING_PERIOD_DAYS)
        await self._billing.set_plan(workspace, plan=target, paid_until=paid_until)
        invoice = await self._billing.create_invoice(
            workspace_id=workspace_id,
            plan=target,
            amount_vnd=amount,
            issued_at=now,
            status=InvoiceStatus.PENDING,
        )

        # Đổi gói là thay đổi có hệ quả tiền bạc — phải trả lời được về sau "ai
        # đổi sang gói nào, lúc nào", giống mọi hành vi nhạy cảm khác trong hệ
        # thống (auto-reply, publish).
        await self._events.record(
            EventLogEntry(
                workspace_id=workspace_id,
                job_kind="billing.plan_changed",
                input_summary=f"{current.value} -> {target.value}",
                output_summary=(
                    f"invoice:{invoice.id} amount_vnd:{amount} "
                    f"status:{invoice.status.value} paid_until:{paid_until.isoformat()}"
                ),
            )
        )

        state = subscription.state_for(
            plan=target,
            trial_ends_at=_as_utc(workspace.trial_ends_at),
            paid_until=paid_until,
            now=now,
        )
        return state, invoice

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
