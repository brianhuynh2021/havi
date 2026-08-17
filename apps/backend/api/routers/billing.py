"""/billing — gói cước, quota token và hoá đơn.

Tích hợp cổng thanh toán VN (VNPay/Momo) qua backend; frontend không thấy secret nào.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from api.deps import BillingServiceDep, SettingsDep, WorkspaceDep
from core.enums import Plan
from core.schemas import ChangePlanRequest, Invoice, Subscription
from domain.policies.subscription import PlanChangeNotAllowed

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/subscription", response_model=Subscription)
async def get_subscription(
    workspace_id: WorkspaceDep, billing_service: BillingServiceDep
) -> Subscription:
    state, quota = await billing_service.subscription_state(workspace_id=workspace_id)
    return Subscription(
        workspace_id=workspace_id,
        plan=state.plan,
        status=state.status,
        current_period_end=state.current_period_end,
        token_quota_used=quota.used,
        token_quota_limit=quota.limit,
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
    body: ChangePlanRequest,
) -> Subscription:
    try:
        state, _ = await billing_service.change_plan(workspace_id=workspace_id, target=body.plan)
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
        )
    except PlanChangeNotAllowed as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
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
