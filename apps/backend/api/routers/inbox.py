"""/inbox — 1 luồng gộp comment / review / message từ mọi nền tảng.

Reply KHÔNG có full_auto: luôn phải bấm gửi. Ngoại lệ duy nhất là FAQ chủ đã duyệt
sẵn từng câu trong brand profile.
"""

from uuid import UUID

from fastapi import APIRouter, Query, status

from api.deps import AuthDep, WorkspaceDep
from api.errors import NotImplementedEndpoint
from core.enums import InboxItemStatus, Platform
from core.schemas import InboxItem, InboxReplyRequest, Page

router = APIRouter(prefix="/inbox", tags=["inbox"])


@router.get("", response_model=Page[InboxItem])
def list_inbox(
    workspace_id: WorkspaceDep,
    status: InboxItemStatus | None = None,
    platform: Platform | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
) -> Page[InboxItem]:
    del workspace_id, status, platform, limit, offset
    raise NotImplementedEndpoint()


@router.post("/{item_id}/reply", response_model=InboxItem)
def send_reply(item_id: UUID, payload: InboxReplyRequest, auth: AuthDep) -> InboxItem:
    """Nút "Gửi" / "Sửa rồi gửi" — chỉ chạy khi có action của người thật."""
    del item_id, payload, auth
    raise NotImplementedEndpoint()


@router.post("/{item_id}/dismiss", status_code=status.HTTP_204_NO_CONTENT)
def dismiss(item_id: UUID, auth: AuthDep) -> None:
    """Nút "Bỏ qua"."""
    del item_id, auth
    raise NotImplementedEndpoint()
