"""Unit tests for TrendScoutService (Milestone #8)."""

from uuid import uuid4

import pytest

from application.services.trend_scout_service import TrendScoutService
from domain.models.trend_scout import TrendCategory, TrendSynthesisRequest


@pytest.mark.asyncio
async def test_get_hot_trends_returns_sorted_list():
    service = TrendScoutService()
    ws_id = uuid4()
    trends = await service.get_hot_trends(ws_id)

    assert len(trends) >= 5
    # Kiểm tra sắp xếp theo trend_score giảm dần
    scores = [t.trend_score for t in trends]
    assert scores == sorted(scores, reverse=True)
    assert trends[0].trend_score >= 90
    assert any(t.category == TrendCategory.TECH_EDUCATION for t in trends)


@pytest.mark.asyncio
async def test_synthesize_video_plan_creates_complete_edit_plan():
    service = TrendScoutService()
    ws_id = uuid4()
    req = TrendSynthesisRequest(
        trend_id="trend-career-comparison-2026",
        target_aspect_ratio="9:16",
        duration_seconds=15,
    )
    result = await service.synthesize_video_plan(
        ws_id, req, brand_name="Trung Tâm Công Nghệ Nhật Minh"
    )

    assert result.trend.id == "trend-career-comparison-2026"
    assert "Trung Tâm Công Nghệ Nhật Minh" in result.title
    assert result.caption_style == "bold_yellow"
    assert len(result.script_outline) == 3
    assert result.edit_plan["target_aspect_ratio"] == "9:16"
    assert result.edit_plan["target_duration_seconds"] == 15
    assert len(result.edit_plan["captions"]) == 2
    assert result.edit_plan["audio"]["normalize_db"] == -14.0
