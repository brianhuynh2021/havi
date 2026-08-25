"""Unit tests for TrendScoutService (Milestone #8)."""

from uuid import uuid4

import pytest

from application.services.trend_scout_service import TrendScoutService
from domain.models.trend_scout import TrendCategory, TrendSynthesisRequest


@pytest.mark.asyncio
async def test_get_hot_trends_returns_sorted_list(monkeypatch):
    """Chặn mạng thật: kết quả phải tất định.

    Bản trước gọi thẳng Google Trends RSS. Nội dung đó đổi theo giờ, và
    `category` được gán luân phiên theo chỉ số, nên cùng một commit lúc xanh lúc
    đỏ tuỳ thời điểm chạy. Một test đỏ ngẫu nhiên tệ hơn không có test: đội ngũ
    học cách chạy lại cho tới khi xanh, và bỏ qua cả những lần đỏ thật.
    """
    service = TrendScoutService()

    async def fake_live(self, count: int = 5):  # noqa: ANN001, ANN202
        return [
            {"keyword": f"tu khoa {i}", "traffic": traffic}
            for i, traffic in enumerate(["50K+", "20K+", "10K+", "5K+", "2K+"][:count])
        ]

    monkeypatch.setattr(TrendScoutService, "_fetch_google_trends_live_vn", fake_live)

    trends = await service.get_hot_trends(uuid4())

    assert len(trends) >= 5
    scores = [t.trend_score for t in trends]
    assert scores == sorted(scores, reverse=True), "phải sắp xếp giảm dần theo điểm"
    # 50K+ ở hạng 0 → trần 95. Xem `_TRAFFIC_TIERS`.
    assert trends[0].trend_score >= 90
    assert {t.category for t in trends} <= set(TrendCategory)


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
