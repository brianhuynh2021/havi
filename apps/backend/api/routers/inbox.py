"""/inbox — 1 luồng gộp comment / review / message từ mọi nền tảng.

Reply KHÔNG có full_auto: luôn phải bấm gửi. Ngoại lệ duy nhất là FAQ chủ đã duyệt
sẵn từng câu trong brand profile.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from api.deps import AuthDep, InboxServiceDep, WorkspaceDep
from application.services.inbox_service import InboxItemNotFound
from core.enums import InboxItemStatus, Platform
from core.schemas import InboxItem, InboxReplyRequest, Page
from domain.ports.reply_publisher import ReplyError

router = APIRouter(prefix="/inbox", tags=["inbox"])


@router.get("", response_model=Page[InboxItem])
async def list_inbox(
    workspace_id: WorkspaceDep,
    inbox_service: InboxServiceDep,
    status: InboxItemStatus | None = None,
    platform: Platform | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
) -> Page[InboxItem]:
    items, total = await inbox_service.list_items(
        workspace_id=workspace_id,
        status=status,
        platform=platform,
        limit=limit,
        offset=offset,
    )
    return Page[InboxItem](items=items, total=total, limit=limit, offset=offset)


@router.post("/{item_id}/reply", response_model=InboxItem)
async def send_reply(
    item_id: UUID,
    payload: InboxReplyRequest,
    workspace_id: WorkspaceDep,
    inbox_service: InboxServiceDep,
    auth: AuthDep,
) -> InboxItem:
    """Nút "Gửi" / "Sửa rồi gửi" — chỉ chạy khi có action của người thật."""
    del auth
    try:
        return await inbox_service.send_reply(
            workspace_id=workspace_id,
            item_id=item_id,
            text=payload.text,
        )
    except InboxItemNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy tin nhắn/bình luận này",
        ) from exc
    except ReplyError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Không thể gửi tin nhắn qua nền tảng: {exc}",
        ) from exc


@router.post("/{item_id}/dismiss", status_code=status.HTTP_204_NO_CONTENT)
async def dismiss(
    item_id: UUID,
    workspace_id: WorkspaceDep,
    inbox_service: InboxServiceDep,
    auth: AuthDep,
) -> None:
    """Nút "Bỏ qua"."""
    del auth
    try:
        await inbox_service.dismiss_item(workspace_id=workspace_id, item_id=item_id)
    except InboxItemNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy tin nhắn/bình luận này",
        ) from exc
