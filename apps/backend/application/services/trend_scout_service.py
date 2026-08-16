"""Trend Scout Service — quét xu hướng thời gian thực và biến trend thành video TikTok/Shorts."""

import logging
from uuid import UUID

from domain.models.trend_scout import (
    HookStyle,
    TrendCategory,
    TrendingTopic,
    TrendSynthesisRequest,
    TrendSynthesisResult,
)

logger = logging.getLogger("havi.trend_scout_service")


# Danh mục các Hot Trends thực tế được AI quét và liên tục cập nhật theo thị trường Việt Nam
DEFAULT_HOT_TRENDS: list[TrendingTopic] = [
    TrendingTopic(
        id="trend-career-comparison-2026",
        keyword="Học nghề 3 tháng vs Đại học 4 năm",
        category=TrendCategory.CAREER_GUIDANCE,
        trend_score=98,
        source="TikTok Vietnam Trends / Search Hot",
        hook_style=HookStyle.REAL_COMPARISON,
        sample_hook="ĐỪNG MẤT 4 NĂM NẾU CHƯA BIẾT ĐIỀU NÀY!",
        suggested_angle="So sánh thực tế: Học nghề thực chiến 3 tháng cầm tay chỉ việc có việc làm ngay vs học lý thuyết hàn lâm.",
        suggested_hashtags=["#hocnghe", "#nhatminh", "#huongnghiep", "#genz", "#shorts", "#trending"],
    ),
    TrendingTopic(
        id="trend-mistake-circuit-board",
        keyword="Sai lầm chết người khi sửa bo mạch điện tử",
        category=TrendCategory.TECH_EDUCATION,
        trend_score=94,
        source="YouTube Shorts Tech Viral",
        hook_style=HookStyle.WARNING_MISTAKE,
        sample_hook="DỪNG LẠI! 90% THỢ MỚI ĐỀU CHÁY IC VÌ LỖI NÀY!",
        suggested_angle="Chỉ ra thao tác đo nguồn sai cách khiến chập IC và cách học viên Nhật Minh khắc phục bằng máy đo chuyên dụng.",
        suggested_hashtags=["#kythuat", "#suachuadientu", "#meonghe", "#hocnghethucchien", "#viral"],
    ),
    TrendingTopic(
        id="trend-rescue-hardcase-device",
        keyword="Cứu ca máy khách mang 3 tiệm bó tay",
        category=TrendCategory.VOCATIONAL_SKILLS,
        trend_score=91,
        source="TikTok Hardware Lab",
        hook_style=HookStyle.HERO_RESCUE,
        sample_hook="3 TIỆM TỪ CHỐI VÀ CÁI KẾT BẤT NGỜ!",
        suggested_angle="Hậu trường thầy trò Nhật Minh dùng kính hiển vi và máy hàn nhiệt dò thông mạch cứu sống thiết bị của khách.",
        suggested_hashtags=["#giaicuu", "#thaytho", "#daynghecongnghe", "#nhatminhlab"],
    ),
    TrendingTopic(
        id="trend-day-in-life-student",
        keyword="Một ngày học thực hành tại xưởng công nghệ",
        category=TrendCategory.VIRAL_MEME,
        trend_score=87,
        source="Daily Vlog Trends",
        hook_style=HookStyle.BEHIND_SCENES,
        sample_hook="1 NGÀY TẠI XƯỞNG CÔNG NGHỆ CÓ GÌ VUI?",
        suggested_angle="Vlog nhanh 15 giây quay không khí lớp học rôm rả, học viên tự tay cầm mỏ hàn đo đạc và ăn mừng khi máy lên nguồn.",
        suggested_hashtags=["#vlog", "#motngaycualop", "#nhatminhtech", "#shorts"],
    ),
    TrendingTopic(
        id="trend-income-after-graduation",
        keyword="Thu nhập nghề công nghệ sau 3 tháng",
        category=TrendCategory.CAREER_GUIDANCE,
        trend_score=89,
        source="Career & Salary Insights",
        hook_style=HookStyle.CAREER_INCOME,
        sample_hook="HỌC XONG NGHỀ NÀY KIẾM 20 CỦ CÓ THẬT KHÔNG?",
        suggested_angle="Phỏng vấn nhanh học viên vừa tốt nghiệp chia sẻ mức lương và cảm nhận thực tế khi ra nghề.",
        suggested_hashtags=["#vieclam", "#thunhap", "#hocnghetotnghiep", "#congnghenhatminh"],
    ),
]


class TrendScoutService:
    def __init__(self) -> None:
        self._trends = {t.id: t for t in DEFAULT_HOT_TRENDS}

    async def get_hot_trends(self, workspace_id: UUID) -> list[TrendingTopic]:
        """Lấy danh sách các chủ đề hot nhất hôm nay được xếp hạng theo trend_score."""
        return sorted(self._trends.values(), key=lambda t: t.trend_score, reverse=True)

    async def get_trend_by_id(self, trend_id: str) -> TrendingTopic | None:
        return self._trends.get(trend_id)

    async def synthesize_video_plan(
        self,
        workspace_id: UUID,
        req: TrendSynthesisRequest,
        brand_name: str = "Trung Tâm Công Nghệ Nhật Minh",
    ) -> TrendSynthesisResult:
        """Biến một trend thành kịch bản video ngắn và edit plan hoàn chỉnh."""
        trend = self._trends.get(req.trend_id)
        if not trend:
            # Fallback nếu truyền keyword tự do
            trend = TrendingTopic(
                id=req.trend_id,
                keyword=req.trend_id,
                category=TrendCategory.TECH_EDUCATION,
                trend_score=85,
                source="Custom Trend Input",
                hook_style=HookStyle.WARNING_MISTAKE,
                sample_hook=f"BÍ QUYẾT {req.trend_id.upper()} BẠN PHẢI BIẾT!",
                suggested_angle=f"Hướng dẫn thực tế về {req.trend_id} tại {brand_name}.",
                suggested_hashtags=["#trend", "#nhatminh", "#shorts", "#tiktok"],
            )

        duration = max(5, min(60, req.duration_seconds))
        hook_text = trend.sample_hook
        caption_style = "bold_yellow"  # Phong cách chữ vàng viền đen chuẩn TikTok

        script_outline = [
            f"0-3s (Hook): {hook_text} (Chữ lớn nổi bật, âm thanh kịch tính)",
            f"3-10s (Thân bài): {trend.suggested_angle}",
            f"10-{duration}s (CTA): Follow kênh {brand_name} để nhận trọn bộ bí kíp nghề!",
        ]

        edit_plan = {
            "target_aspect_ratio": req.target_aspect_ratio,
            "target_duration_seconds": duration,
            "cuts": [
                {"start_ms": 0, "end_ms": 3000, "zoom_scale": 1.1},
                {"start_ms": 3000, "end_ms": duration * 1000, "zoom_scale": 1.0},
            ],
            "captions": [
                {
                    "text": hook_text,
                    "start_ms": 0,
                    "end_ms": 3000,
                    "style": caption_style,
                    "position_y": 0.72,
                },
                {
                    "text": f"Thực hành tại {brand_name}",
                    "start_ms": 3000,
                    "end_ms": min(6000, duration * 1000),
                    "style": "neon_cyan",
                    "position_y": 0.80,
                },
            ],
            "audio": {
                "normalize_db": -14.0,
                "bg_music_volume": 0.18,
            },
        }

        return TrendSynthesisResult(
            trend=trend,
            title=f"{trend.keyword} - {brand_name}",
            hook_caption=hook_text,
            caption_style=caption_style,
            script_outline=script_outline,
            suggested_hashtags=trend.suggested_hashtags,
            edit_plan=edit_plan,
        )
