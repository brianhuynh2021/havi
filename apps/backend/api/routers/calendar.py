"""/calendar — view trên `content_item.scheduled_at`, không phải bảng riêng."""

from collections import defaultdict
from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from api.deps import ApprovalServiceDep, AuthDep, WorkspaceDep
from application.services.approval_service import ContentItemNotFound, NotReschedulable
from core.schemas import CalendarDay, CalendarView, ContentItem, RescheduleRequest
from domain.policies.scheduling import VIETNAM_TZ

router = APIRouter(prefix="/calendar", tags=["calendar"])

MAX_CALENDAR_DAYS = 92


@router.get("", response_model=CalendarView)
async def get_calendar(
    workspace_id: WorkspaceDep, approvals: ApprovalServiceDep, start: date, end: date
) -> CalendarView:
    """`start`/`end` là ngày theo giờ Việt Nam, cả hai đầu inclusive.

    Gom nhóm theo ngày VN chứ không theo ngày UTC: bài hẹn 8h sáng thứ Ba giờ VN
    là 1h sáng thứ Ba UTC — cùng ngày ở đây, nhưng bài 6h sáng thứ Ba VN lại là
    23h thứ Hai UTC, và chủ tiệm sẽ thấy nó nhảy sang ô sai trên lịch tuần.
    """
    if end < start:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "`end` phải sau `start`")
    if (end - start).days + 1 > MAX_CALENDAR_DAYS:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"Khoảng lịch tối đa {MAX_CALENDAR_DAYS} ngày",
        )

    range_start = datetime.combine(start, time.min, tzinfo=VIETNAM_TZ).astimezone(UTC)
    # end exclusive ở tầng query = 00:00 ngày kế tiếp, để bài lúc 23:59 vẫn lọt.
    range_end = datetime.combine(
        end + timedelta(days=1), time.min, tzinfo=VIETNAM_TZ
    ).astimezone(UTC)

    items = await approvals.calendar(
        workspace_id=workspace_id, start=range_start, end=range_end
    )
    by_day: dict[str, list[ContentItem]] = defaultdict(list)
    for item in items:
        # scheduled_at đọc từ Postgres là naive UTC (cột TIMESTAMP WITHOUT TIME ZONE).
        scheduled = item.scheduled_at
        assert scheduled is not None  # query đã lọc IS NOT NULL
        if scheduled.tzinfo is None:
            scheduled = scheduled.replace(tzinfo=UTC)
        local_day = scheduled.astimezone(VIETNAM_TZ).date().isoformat()
        by_day[local_day].append(ContentItem.model_validate(item))

    # Trả đủ mọi ngày trong khoảng, kể cả ngày rỗng — frontend dựng lưới tuần cố
    # định, không phải chỉ list ngày có bài.
    days = [
        CalendarDay(
            date=(start + timedelta(days=offset)).isoformat(),
            items=by_day.get((start + timedelta(days=offset)).isoformat(), []),
        )
        for offset in range((end - start).days + 1)
    ]
    return CalendarView(days=days)


@router.post("/{content_id}/reschedule", response_model=ContentItem)
async def reschedule(
    content_id: UUID,
    payload: RescheduleRequest,
    auth: AuthDep,
    workspace_id: WorkspaceDep,
    approvals: ApprovalServiceDep,
) -> ContentItem:
    """Kéo-thả đổi giờ đăng. Chỉ cho `approved` / `scheduled`; `published` trả 409."""
    try:
        item = await approvals.reschedule(
            workspace_id=workspace_id,
            item_id=content_id,
            user_id=auth.user_id,
            scheduled_at=payload.scheduled_at,
        )
    except ContentItemNotFound as exc:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Không tìm thấy content item"
        ) from exc
    except NotReschedulable as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    return ContentItem.model_validate(item)
