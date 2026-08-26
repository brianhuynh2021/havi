"""/billing — gói cước, quota token và hoá đơn.

Tích hợp cổng thanh toán VN (VNPay/Momo) qua backend; frontend không thấy secret nào.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from adapters.payment.payos_gateway import PaymentGatewayError
from adapters.persistence.connection_repository import ConnectionRepository
from adapters.persistence.db import DbSessionDep
from adapters.persistence.event_log_repository import EventLogRepository
from adapters.persistence.workspace_member_repository import WorkspaceMemberRepository
from adapters.persistence.workspace_repository import WorkspaceRepository
from api.deps import BillingServiceDep, SettingsDep, WorkspaceDep
from core.enums import BillingCycle, Plan
from core.schemas import ChangePlanRequest, Invoice, Subscription
from domain.policies import plan_limits
from domain.policies import quota as quota_policy
from domain.policies.subscription import PlanChangeNotAllowed

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/subscription", response_model=Subscription)
async def get_subscription(
    workspace_id: WorkspaceDep,
    billing_service: BillingServiceDep,
    session: DbSessionDep,
) -> Subscription:
    state, quota = await billing_service.subscription_state(workspace_id=workspace_id)
    # Trần **hiệu dụng**: gói cộng phần đã mua thêm. Đọc `limits_for` trực tiếp
    # là chặn khách ở đúng cái ghế họ vừa trả tiền.
    workspace = await WorkspaceRepository(session).get_by_id(workspace_id)
    extra_seats = workspace.extra_seats if workspace else 0
    extra_channels = workspace.extra_channels if workspace else 0
    limits = plan_limits.effective_limits(
        plan=state.plan, extra_seats=extra_seats, extra_channels=extra_channels
    )

    # Đếm thật thay vì để frontend đoán: bảng giá và màn Đội ngũ phải hiện đúng
    # con số đang được cưỡng chế ở backend, nếu không người dùng đọc "3 người" rồi
    # bị chặn ở người thứ ba.
    seats_used = await WorkspaceMemberRepository(session).count_members(workspace_id)
    channels_used = len(await ConnectionRepository(session).list_for_workspace(workspace_id))

    # Quy hạn mức về "còn khoảng bao nhiêu bài". Đo từ chính workspace này trong
    # 90 ngày; chưa đủ mẫu thì dùng ước lượng mặc định và **nói ra** là mặc định.
    measured = await EventLogRepository(session).avg_weighted_tokens_per_content_job(
        workspace_id=workspace_id, since=datetime.now(UTC) - timedelta(days=90)
    )
    tokens_per_post = measured or quota_policy.ASSUMED_TOKENS_PER_POST
    posts_remaining = max(0, (quota.limit - quota.used)) // max(1, tokens_per_post)

    days_until_due: int | None = None
    if state.current_period_end is not None:
        delta = state.current_period_end - datetime.now(UTC)
        # Làm tròn xuống: còn 1,9 ngày thì nói "1 ngày" chứ không "2 ngày" — nhắc
        # sớm hơn thực tế thì vô hại, nhắc muộn hơn thì khách mất quyền giữa lúc
        # đang trực khách.
        days_until_due = delta.days

    return Subscription(
        workspace_id=workspace_id,
        plan=state.plan,
        status=state.status,
        current_period_end=state.current_period_end,
        token_quota_used=quota.used,
        token_quota_limit=quota.limit,
        billing_cycle=(
            workspace.billing_cycle if workspace else BillingCycle.MONTHLY
        ),
        extra_seats=extra_seats,
        extra_channels=extra_channels,
        seats_used=seats_used,
        seats_limit=limits.max_seats,
        channels_used=channels_used,
        channels_limit=limits.max_channels,
        posts_remaining_estimate=posts_remaining,
        tokens_per_post=tokens_per_post,
        tokens_per_post_measured=measured is not None,
        days_until_due=days_until_due,
    )


@router.get("/invoices", response_model=list[Invoice])
async def list_invoices(
    workspace_id: WorkspaceDep,
    billing_service: BillingServiceDep,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[Invoice]:
    invoices, _ = await billing_service.list_invoices(
        workspace_id=workspace_id, limit=limit, offset=offset
    )
    return [
        Invoice(
            id=inv.id,
            workspace_id=inv.workspace_id,
            plan=inv.plan,
            amount_vnd=inv.amount_vnd,
            status=inv.status.value if hasattr(inv.status, "value") else str(inv.status),
            issued_at=inv.issued_at,
        )
        for inv in invoices
    ]


@router.post("/plan", response_model=Subscription)
async def change_plan(
    workspace_id: WorkspaceDep,
    billing_service: BillingServiceDep,
    settings: SettingsDep,
    body: ChangePlanRequest,
) -> Subscription:
    if not settings.is_local:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    try:
        state, _ = await billing_service.change_plan(
            workspace_id=workspace_id,
            target=body.plan,
            cycle=body.cycle,
            extra_seats=body.extra_seats,
            extra_channels=body.extra_channels,
        )
    except PlanChangeNotAllowed as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    _, quota = await billing_service.subscription_state(workspace_id=workspace_id)
    return Subscription(
        workspace_id=workspace_id,
        plan=state.plan,
        status=state.status,
        current_period_end=state.current_period_end,
        token_quota_used=quota.used,
        token_quota_limit=quota.limit,
    )


class CheckoutResponse(BaseModel):
    invoice_id: str
    plan: Plan
    amount_vnd: int
    transfer_content: str
    bank_id: str
    account_no: str
    account_name: str
    qr_code_url: str


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(
    workspace_id: WorkspaceDep,
    billing_service: BillingServiceDep,
    settings: SettingsDep,
    body: ChangePlanRequest,
) -> CheckoutResponse:
    """Tạo mã thanh toán VietQR động để nâng cấp gói cước."""
    try:
        invoice, checkout = await billing_service.create_checkout(
            workspace_id=workspace_id,
            target=body.plan,
            settings=settings,
            cycle=body.cycle,
            extra_seats=body.extra_seats,
            extra_channels=body.extra_channels,
        )
    except PlanChangeNotAllowed as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except PaymentGatewayError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return CheckoutResponse(
        invoice_id=str(invoice.id),
        plan=invoice.plan,
        amount_vnd=invoice.amount_vnd,
        transfer_content=checkout.transfer_content,
        bank_id=checkout.bank_id,
        account_no=checkout.account_no,
        account_name=checkout.account_name,
        qr_code_url=checkout.qr_code_url,
    )


@router.get("/invoices/{invoice_id}/status")
async def get_invoice_status(
    invoice_id: UUID,
    workspace_id: WorkspaceDep,
    billing_service: BillingServiceDep,
) -> dict:
    """Kiểm tra trạng thái hoá đơn để Frontend tự động refresh sau khi quét QR."""
    invoice = await billing_service.get_invoice(invoice_id=invoice_id)
    if invoice is None or invoice.workspace_id != workspace_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found",
        )
    return {
        "invoice_id": str(invoice.id),
        "status": invoice.status.value if hasattr(invoice.status, "value") else str(invoice.status),
        "plan": invoice.plan.value,
        "amount_vnd": invoice.amount_vnd,
    }
