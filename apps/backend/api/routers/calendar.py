"""/calendar — view trên `content_item.scheduled_at`, không phải bảng riêng."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter

from api.deps import AuthDep, WorkspaceDep
from api.errors import NotImplementedEndpoint
from core.schemas import CalendarView, ContentItem, RescheduleRequest

router = APIRouter(prefix="/calendar", tags=["calendar"])


@router.get("", response_model=CalendarView)
def get_calendar(workspace_id: WorkspaceDep, start: date, end: date) -> CalendarView:
    del workspace_id, start, end
    raise NotImplementedEndpoint()


@router.post("/{content_id}/reschedule", response_model=ContentItem)
def reschedule(content_id: UUID, payload: RescheduleRequest, auth: AuthDep) -> ContentItem:
    """Kéo-thả đổi giờ đăng. Chỉ cho `approved` / `scheduled`; `published` trả 409."""
    del content_id, payload, auth
    raise NotImplementedEndpoint()
