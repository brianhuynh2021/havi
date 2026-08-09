"""/analytics — đo bằng khách hỏi giá / khách đến tiệm / khách quay lại, không phải like.

Nguồn: `content_item.published_at` + engagement snapshot (polling theo lịch) + `lead`.
Không cần real-time.
"""

from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from adapters.persistence.content_repository import ContentRepository
from adapters.persistence.db import DbSessionDep
from adapters.persistence.event_log_repository import EventLogRepository
from api.deps import WorkspaceDep
from core.enums import ContentStatus
from core.schemas import (
    AnalyticsSummary,
    AnalyticsTimeseries,
    ChannelAttribution,
    DashboardContentSummary,
    EventLogRecord,
    Page,
)
from domain.policies.scheduling import VIETNAM_TZ

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _date_range(start: date, end: date) -> tuple[datetime, datetime]:
    if end < start:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "`end` phải sau `start`")
    range_start = datetime.combine(start, time.min, tzinfo=VIETNAM_TZ).astimezone(UTC)
    range_end = datetime.combine(
        end + timedelta(days=1), time.min, tzinfo=VIETNAM_TZ
    ).astimezone(UTC)
    return range_start, range_end


@router.get("/dashboard", response_model=DashboardContentSummary)
async def dashboard(
    workspace_id: WorkspaceDep, session: DbSessionDep
) -> DashboardContentSummary:
    """Số liệu thật tối thiểu cho tab Tổng quan."""
    counts = await ContentRepository(session).count_items_by_status(workspace_id=workspace_id)
    return DashboardContentSummary(
        drafts=counts.get(ContentStatus.DRAFT, 0),
        pending_approval=counts.get(ContentStatus.PENDING_APPROVAL, 0),
        scheduled=counts.get(ContentStatus.SCHEDULED, 0),
        published=counts.get(ContentStatus.PUBLISHED, 0),
        failed=counts.get(ContentStatus.FAILED, 0)
        + counts.get(ContentStatus.DEAD_LETTER, 0),
    )


@router.get("/events", response_model=Page[EventLogRecord])
async def events(
    workspace_id: WorkspaceDep,
    session: DbSessionDep,
    job_id: UUID | None = None,
    job_kind: str | None = Query(default=None, max_length=80),
    provider: str | None = Query(default=None, max_length=80),
    error_only: bool = False,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
) -> Page[EventLogRecord]:
    """Event log đã scope theo workspace để support debug.

    Chưa có `request_id`: code hiện tại chưa gắn request id vào log context hoặc
    bảng `event_log`, nên endpoint này chỉ expose các khoá thật đang được lưu.
    """
    rows, total = await EventLogRepository(session).list_for_workspace(
        workspace_id=workspace_id,
        job_id=job_id,
        job_kind=job_kind,
        provider=provider,
        error_only=error_only,
        limit=limit,
        offset=offset,
    )
    return Page(
        items=[EventLogRecord.model_validate(row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/summary", response_model=AnalyticsSummary)
async def summary(
    workspace_id: WorkspaceDep, session: DbSessionDep, start: date, end: date
) -> AnalyticsSummary:
    """3 stat card ở tab Báo cáo, kèm ▲ so kỳ trước."""
    range_start, range_end = _date_range(start, end)
    published_posts = await ContentRepository(session).count_published_posts(
        workspace_id=workspace_id, start=range_start, end=range_end
    )
    return AnalyticsSummary(
        price_inquiries=0,
        walk_ins=0,
        returning_customers=0,
        published_posts=published_posts,
        new_leads=0,
        lead_won_rate=0,
        change_vs_previous_period={},
    )


@router.get("/attribution", response_model=list[ChannelAttribution])
async def attribution(
    workspace_id: WorkspaceDep, session: DbSessionDep, start: date, end: date
) -> list[ChannelAttribution]:
    """Khối "Khách đến tiệm từ kênh nào"."""
    range_start, range_end = _date_range(start, end)
    counts = await ContentRepository(session).count_published_by_channel(
        workspace_id=workspace_id, start=range_start, end=range_end
    )
    total = sum(counts.values())
    return [
        ChannelAttribution(
            channel=channel,
            customers=count,
            share=round(count / total, 4) if total else 0,
            note="Tạm tính theo bài đã đăng; chưa có engagement snapshot.",
        )
        for channel, count in sorted(counts.items(), key=lambda item: item[0].value)
    ]


def _period_start(value: datetime, *, granularity: str) -> datetime:
    local = value.astimezone(VIETNAM_TZ)
    if granularity == "month":
        return datetime(local.year, local.month, 1, tzinfo=VIETNAM_TZ)
    monday = local.date() - timedelta(days=local.weekday())
    return datetime.combine(monday, time.min, tzinfo=VIETNAM_TZ)


def _period_label(value: datetime, *, granularity: str) -> str:
    if granularity == "month":
        return value.strftime("%Y-%m")
    year, week, _ = value.isocalendar()
    return f"{year}-W{week:02d}"


def _month_start_offset(value: datetime, offset: int) -> datetime:
    month_index = value.year * 12 + (value.month - 1) - offset
    year = month_index // 12
    month = month_index % 12 + 1
    return datetime(year, month, 1, tzinfo=VIETNAM_TZ)


@router.get("/timeseries", response_model=AnalyticsTimeseries)
async def timeseries(
    workspace_id: WorkspaceDep,
    session: DbSessionDep,
    metric: str,
    granularity: str = Query(default="week", pattern="^(week|month)$"),
) -> AnalyticsTimeseries:
    """Bar chart 4 tuần."""
    if metric != "published_posts":
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Metric hiện hỗ trợ: published_posts",
        )

    now = datetime.now(VIETNAM_TZ)
    current = _period_start(now, granularity=granularity)
    if granularity == "month":
        starts = [_month_start_offset(current, offset) for offset in reversed(range(4))]
    else:
        starts = [current - timedelta(days=7 * offset) for offset in reversed(range(4))]
    points = []
    repository = ContentRepository(session)
    for period in starts:
        if granularity == "month":
            next_month = period.month + 1
            next_year = period.year
            if next_month == 13:
                next_month = 1
                next_year += 1
            end = datetime(next_year, next_month, 1, tzinfo=VIETNAM_TZ)
        else:
            end = period + timedelta(days=7)
        count = await repository.count_published_posts(
            workspace_id=workspace_id,
            start=period.astimezone(UTC),
            end=end.astimezone(UTC),
        )
        points.append({"period": _period_label(period, granularity=granularity), "value": count})
    return AnalyticsTimeseries(metric=metric, points=points)
