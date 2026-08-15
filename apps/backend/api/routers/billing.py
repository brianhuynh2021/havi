"""/billing — gói cước, quota token và hoá đơn.

Tích hợp cổng thanh toán VN (VNPay/Momo) qua backend; frontend không thấy secret nào.
"""

from fastapi import APIRouter, HTTPException, Query, status

from api.deps import BillingServiceDep, WorkspaceDep
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
