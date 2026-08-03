"""/analytics — đo bằng khách hỏi giá / khách đến tiệm / khách quay lại, không phải like.

Nguồn: `content_item.published_at` + engagement snapshot (polling theo lịch) + `lead`.
Không cần real-time.
"""

from datetime import date

from fastapi import APIRouter, Query

from api.deps import WorkspaceDep
from api.errors import NotImplementedEndpoint
from core.schemas import AnalyticsSummary, AnalyticsTimeseries, ChannelAttribution

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary", response_model=AnalyticsSummary)
def summary(workspace_id: WorkspaceDep, start: date, end: date) -> AnalyticsSummary:
    """3 stat card ở tab Báo cáo, kèm ▲ so kỳ trước."""
    del workspace_id, start, end
    raise NotImplementedEndpoint()


@router.get("/attribution", response_model=list[ChannelAttribution])
def attribution(workspace_id: WorkspaceDep, start: date, end: date) -> list[ChannelAttribution]:
    """Khối "Khách đến tiệm từ kênh nào"."""
    del workspace_id, start, end
    raise NotImplementedEndpoint()


@router.get("/timeseries", response_model=AnalyticsTimeseries)
def timeseries(
    workspace_id: WorkspaceDep,
    metric: str,
    granularity: str = Query(default="week", pattern="^(week|month)$"),
) -> AnalyticsTimeseries:
    """Bar chart 4 tuần."""
    del workspace_id, metric, granularity
    raise NotImplementedEndpoint()
