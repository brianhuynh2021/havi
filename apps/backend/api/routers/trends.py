"""REST API Router cho AI Trend Scout & Trendjacking (Milestone #8)."""

from typing import Any

from fastapi import APIRouter, status
from pydantic import BaseModel, Field

from api.deps import WorkspaceDep
from application.services.trend_scout_service import TrendScoutService
from domain.models.trend_scout import (
    HookStyle,
    TrendCategory,
    TrendSynthesisRequest,
)

router = APIRouter(prefix="/workspaces/{workspace_id}/trends", tags=["trends"])
trend_scout_service = TrendScoutService()


class TrendingTopicResponse(BaseModel):
    id: str
    keyword: str
    category: TrendCategory
    trend_score: int
    source: str
    hook_style: HookStyle
    sample_hook: str
    suggested_angle: str
    suggested_hashtags: list[str]


class SynthesizeTrendRequest(BaseModel):
    trend_id: str
    target_aspect_ratio: str = Field(default="9:16", pattern="^(9:16|1:1|16:9)$")
    duration_seconds: int = Field(default=15, ge=5, le=60)
    custom_notes: str | None = None


class SynthesizeTrendResponse(BaseModel):
    trend_id: str
    keyword: str
    title: str
    hook_caption: str
    caption_style: str
    script_outline: list[str]
    suggested_hashtags: list[str]
    edit_plan: dict[str, Any]


@router.get(
    "/hot",
    response_model=list[TrendingTopicResponse],
    status_code=status.HTTP_200_OK,
    summary="Lấy danh sách các Hot Trends thời gian thực được AI đề xuất cho tiệm",
)
async def get_hot_trends(
    workspace_id: WorkspaceDep,
) -> list[TrendingTopicResponse]:
    trends = await trend_scout_service.get_hot_trends(workspace_id)
    return [
        TrendingTopicResponse(
            id=t.id,
            keyword=t.keyword,
            category=t.category,
            trend_score=t.trend_score,
            source=t.source,
            hook_style=t.hook_style,
            sample_hook=t.sample_hook,
            suggested_angle=t.suggested_angle,
            suggested_hashtags=t.suggested_hashtags,
        )
        for t in trends
    ]


@router.post(
    "/synthesize",
    response_model=SynthesizeTrendResponse,
    status_code=status.HTTP_200_OK,
    summary="Biến một trend thành kịch bản video ngắn và edit plan 9:16 hoàn chỉnh",
)
async def synthesize_trend(
    workspace_id: WorkspaceDep,
    payload: SynthesizeTrendRequest,
) -> SynthesizeTrendResponse:
    brand_name = "Trung Tâm Công Nghệ Nhật Minh"
    res = await trend_scout_service.synthesize_video_plan(
        workspace_id=workspace_id,
        req=TrendSynthesisRequest(
            trend_id=payload.trend_id,
            target_aspect_ratio=payload.target_aspect_ratio,
            duration_seconds=payload.duration_seconds,
            custom_notes=payload.custom_notes,
        ),
        brand_name=brand_name,
    )
    return SynthesizeTrendResponse(
        trend_id=res.trend.id,
        keyword=res.trend.keyword,
        title=res.title,
        hook_caption=res.hook_caption,
        caption_style=res.caption_style,
        script_outline=res.script_outline,
        suggested_hashtags=res.suggested_hashtags,
        edit_plan=res.edit_plan,
    )
