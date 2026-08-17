"""/inbox — 1 luồng gộp comment / review / message từ mọi nền tảng.

Reply KHÔNG có full_auto: luôn phải bấm gửi. Ngoại lệ duy nhất là FAQ chủ đã duyệt
sẵn từng câu trong brand profile.
"""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from api.deps import AuthDep, InboxServiceDep, WorkspaceDep, get_ai_lead_agent_service
from application.services.inbox_service import InboxItemNotFound
from core.enums import InboxItemStatus, LeadSource, Platform
from core.schemas import InboxItem, InboxReplyRequest, Page

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


class AICareInquiryRequest(BaseModel):
    author_name: str = "Khách hàng"
    content: str
    platform: Platform = Platform.FACEBOOK


class AICareInquiryResponse(BaseModel):
    intent: str
    confidence: float
    extracted_phone: str | None = None
    extracted_name: str | None = None
    suggested_tags: list[str]
    suggested_reply: str
    lead_id: UUID | None = None


@router.post("/ai-care", response_model=AICareInquiryResponse)
async def analyze_and_care_lead(
    payload: AICareInquiryRequest,
    workspace_id: WorkspaceDep,
    ai_lead_service: Annotated[Any, Depends(get_ai_lead_agent_service)],
) -> AICareInquiryResponse:
    """AI Lead Care: Phân loại ý định, trích xuất SĐT và tự động đồng bộ Lead vào CRM."""
    lead, analysis = await ai_lead_service.process_incoming_lead_message(
        workspace_id=workspace_id,
        author_name=payload.author_name,
        message=payload.content,
        source=LeadSource.FANPAGE,
    )
    return AICareInquiryResponse(
        intent=analysis.intent.value,
        confidence=analysis.confidence,
        extracted_phone=analysis.extracted_phone,
        extracted_name=analysis.extracted_name,
        suggested_tags=analysis.suggested_tags,
        suggested_reply=analysis.suggested_reply,
        lead_id=lead.id,
    )

