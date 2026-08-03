"""/billing — gói cước và quota token.

Tích hợp cổng thanh toán VN (VNPay/Momo) qua backend; frontend không thấy secret nào.
Chạm trần quota thì job bị xếp hàng chứ không lỗi.
"""

from fastapi import APIRouter

from api.deps import WorkspaceDep
from api.errors import NotImplementedEndpoint
from core.schemas import Invoice, Subscription

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/subscription", response_model=Subscription)
def get_subscription(workspace_id: WorkspaceDep) -> Subscription:
    del workspace_id
    raise NotImplementedEndpoint()


@router.get("/invoices", response_model=list[Invoice])
def list_invoices(workspace_id: WorkspaceDep) -> list[Invoice]:
    del workspace_id
    raise NotImplementedEndpoint()
