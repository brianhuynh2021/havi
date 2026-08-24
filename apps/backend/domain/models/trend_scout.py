"""Domain models for Trend Scout and Real-Time Trendjacking."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


class TrendCategory(StrEnum):
    TECH_EDUCATION = "tech_education"
    CAREER_GUIDANCE = "career_guidance"
    VOCATIONAL_SKILLS = "vocational_skills"
    VIRAL_MEME = "viral_meme"
    TECH_NEWS = "tech_news"
    LIFESTYLE = "lifestyle"


class HookStyle(StrEnum):
    WARNING_MISTAKE = "warning_mistake"  # Cảnh báo sai lầm
    REAL_COMPARISON = "real_comparison"  # So sánh thực tế
    BEHIND_SCENES = "behind_scenes"  # Hậu trường 1 ngày
    HERO_RESCUE = "hero_rescue"  # Cứu ca khó
    CAREER_INCOME = "career_income"  # Cơ hội việc làm & thu nhập


@dataclass
class TrendingTopic:
    id: str
    keyword: str
    category: TrendCategory
    trend_score: int  # 0 - 100 (độ nóng trên mạng)
    source: str
    hook_style: HookStyle
    sample_hook: str
    suggested_angle: str
    suggested_hashtags: list[str] = field(default_factory=list)
    discovered_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class TrendSynthesisRequest:
    trend_id: str
    target_aspect_ratio: str = "9:16"
    duration_seconds: int = 15
    custom_notes: str | None = None


@dataclass
class TrendSynthesisResult:
    trend: TrendingTopic
    title: str
    hook_caption: str
    caption_style: str
    script_outline: list[str]
    suggested_hashtags: list[str]
    edit_plan: dict
