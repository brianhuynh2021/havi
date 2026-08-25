"""Trend Scout Service — quét xu hướng thời gian thực và biến trend thành video TikTok/Shorts."""

import json
import logging
import random
import re
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from uuid import UUID

import httpx

from core.config import get_settings
from domain.models.trend_scout import (
    HookStyle,
    TrendCategory,
    TrendingTopic,
    TrendSynthesisRequest,
    TrendSynthesisResult,
)

logger = logging.getLogger("havi.trend_scout_service")


# Kho dữ liệu xu hướng phong phú đa ngành cho Radar AI thời gian thực (Fallback Pool)
ALL_DYNAMIC_TREND_POOLS: list[TrendingTopic] = [
    TrendingTopic(
        id="trend-drama-vs-ai-income",
        keyword="Thiên hạ hóng drama vs Dân công nghệ kiếm tiền bằng AI",
        category=TrendCategory.VIRAL_MEME,
        trend_score=99,
        source="TikTok Vietnam Trends / Hot Drama Newsjacking",
        hook_style=HookStyle.REAL_COMPARISON,
        sample_hook="KHI THIÊN HẠ MÃI HÓNG DRAMA THÌ DÂN AI ĐANG LÀM GÌ?",
        suggested_angle="Bẻ lái cực đỉnh: Trong khi người ta thức đêm hóng livestream thì học viên Nhật Minh đã cài AI Agent tự động trả lời 5.000 tin nhắn và chốt đơn 24/7.",
        suggested_hashtags=[
            "#drama",
            "#xuhuong",
            "#aiagent",
            "#nhatminhtech",
            "#tudonghoa",
            "#kiemtienthongminh",
        ],
    ),
    TrendingTopic(
        id="trend-ai-takeover-myth",
        keyword="AI không cướp việc của bạn — Người biết dùng AI mới cướp",
        category=TrendCategory.TECH_NEWS,
        trend_score=98,
        source="Google Trends VN / Tech Hot Topic",
        hook_style=HookStyle.WARNING_MISTAKE,
        sample_hook="AI KHÔNG CƯỚP VIỆC CỦA BẠN — NGƯỜI DÙNG AI MỚI CƯỚP!",
        suggested_angle="Chỉ ra thực tế: Ai biết ứng dụng AI Agent tại Nhật Minh sẽ hoàn thành công việc cả tuần chỉ trong 2 giờ và nhân bản thu nhập.",
        suggested_hashtags=["#aiagent", "#khoahocai", "#nhatminh", "#genai", "#xuhuong"],
    ),
    TrendingTopic(
        id="trend-career-comparison-2026",
        keyword="Học nghề thực chiến 3 tháng vs Học lý thuyết 4 năm",
        category=TrendCategory.CAREER_GUIDANCE,
        trend_score=96,
        source="TikTok Career Trends",
        hook_style=HookStyle.REAL_COMPARISON,
        sample_hook="ĐỪNG MẤT 4 NĂM NẾU CHƯA BIẾT ĐIỀU NÀY!",
        suggested_angle="So sánh thực tế: Học nghề thực chiến 3 tháng cầm tay chỉ việc có việc làm ngay vs học lý thuyết hàn lâm.",
        suggested_hashtags=[
            "#hocnghe",
            "#nhatminh",
            "#huongnghiep",
            "#genz",
            "#shorts",
            "#trending",
        ],
    ),
    TrendingTopic(
        id="trend-ai-agent-automation",
        keyword="Ứng dụng AI Agent tự động hóa doanh nghiệp",
        category=TrendCategory.TECH_NEWS,
        trend_score=97,
        source="Google Trends VN / AI Tech Spotlight",
        hook_style=HookStyle.WARNING_MISTAKE,
        sample_hook="DOANH NGHIỆP CỦA BẠN ĐANG MẤT TIỀN NẾU CHƯA DÙNG AI NÀY!",
        suggested_angle="Trình diễn thực tế cách cài đặt AI Agent trực page chốt đơn 24/7 không cần nhân viên tăng ca.",
        suggested_hashtags=["#aiagent", "#tudonghoa", "#nhatminhtech", "#genai", "#viraltech"],
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
        suggested_hashtags=[
            "#kythuat",
            "#suachuadientu",
            "#meonghe",
            "#hocnghethucchien",
            "#viral",
        ],
    ),
    TrendingTopic(
        id="trend-rescue-hardcase-device",
        keyword="Cứu ca máy khách mang 3 tiệm bó tay",
        category=TrendCategory.VOCATIONAL_SKILLS,
        trend_score=93,
        source="TikTok Hardware Lab",
        hook_style=HookStyle.HERO_RESCUE,
        sample_hook="3 TIỆM TỪ CHỐI VÀ CÁI KẾT BẤT NGỜ!",
        suggested_angle="Hậu trường thầy trò Nhật Minh dùng kính hiển vi và máy hàn nhiệt dò thông mạch cứu sống thiết bị của khách.",
        suggested_hashtags=["#giaicuu", "#thaytho", "#daynghecongnghe", "#nhatminhlab"],
    ),
    TrendingTopic(
        id="trend-income-after-graduation",
        keyword="Thu nhập nghề công nghệ sau 3 tháng",
        category=TrendCategory.CAREER_GUIDANCE,
        trend_score=91,
        source="Career & Salary Insights",
        hook_style=HookStyle.CAREER_INCOME,
        sample_hook="HỌC XONG NGHỀ NÀY KIẾM 20 CỦ CÓ THẬT KHÔNG?",
        suggested_angle="Phỏng vấn nhanh học viên vừa tốt nghiệp chia sẻ mức lương và cảm nhận thực tế khi ra nghề.",
        suggested_hashtags=["#vieclam", "#thunhap", "#hocnghetotnghiep", "#congnghenhatminh"],
    ),
    TrendingTopic(
        id="trend-day-in-life-student",
        keyword="Một ngày học thực hành tại xưởng công nghệ",
        category=TrendCategory.VIRAL_MEME,
        trend_score=89,
        source="Daily Vlog Trends",
        hook_style=HookStyle.BEHIND_SCENES,
        sample_hook="1 NGÀY TẠI XƯỞNG CÔNG NGHỆ CÓ GÌ VUI?",
        suggested_angle="Vlog nhanh 15 giây quay không khí lớp học rôm rả, học viên tự tay cầm mỏ hàn đo đạc và ăn mừng khi máy lên nguồn.",
        suggested_hashtags=["#vlog", "#motngaycualop", "#nhatminhtech", "#shorts"],
    ),
    TrendingTopic(
        id="trend-prompt-engineering-tips",
        keyword="3 Mẹo viết Prompt khiến AI làm việc như chuyên gia",
        category=TrendCategory.TECH_EDUCATION,
        trend_score=96,
        source="TikTok AI Masterclass",
        hook_style=HookStyle.REAL_COMPARISON,
        sample_hook="ĐỪNG DÙNG PROMPT CŨ NỮA! HÃY DÙNG CÁCH NÀY!",
        suggested_angle="Bật mí công thức viết prompt 3 bước giúp sinh nội dung chuẩn xác và logic gấp 5 lần bình thường.",
        suggested_hashtags=["#prompting", "#gemini", "#chatgpt", "#hocai", "#nhatminh"],
    ),
    TrendingTopic(
        id="trend-behind-the-scenes-workshop",
        keyword="Hậu trường chuẩn bị phòng Lab thực hành đỉnh cao",
        category=TrendCategory.LIFESTYLE,
        trend_score=88,
        source="YouTube Shorts Behind The Scenes",
        hook_style=HookStyle.BEHIND_SCENES,
        sample_hook="PHÒNG THỰC HÀNH CÔNG NGHỆ BÊN TRONG CÓ GÌ?",
        suggested_angle="Trải nghiệm cận cảnh dàn máy móc hiện đại và đồ nghề chuyên nghiệp phục vụ học viên 1 kèm 1.",
        suggested_hashtags=["#phonglab", "#thietbi", "#daynghe", "#nhatminhcenter"],
    ),
]

DEFAULT_HOT_TRENDS: list[TrendingTopic] = ALL_DYNAMIC_TREND_POOLS[:5]


#: Ngưỡng lưu lượng → điểm trần, xét từ cao xuống.
#:
#: Thang này hiệu chỉnh theo **thị trường Việt Nam**, không theo Mỹ: RSS của
#: Google Trends VN trả về `100+`, `1000+`, `20K+` — một trend "nóng toàn quốc"
#: ở đây thường chỉ vài nghìn lượt. Lấy thang cỡ Mỹ áp vào thì mọi trend VN đều
#: rơi xuống đáy bảng và bảng xếp hạng mất hết sức phân biệt.
_TRAFFIC_TIERS: tuple[tuple[int, int], ...] = (
    (200_000, 99),
    (100_000, 97),
    (50_000, 95),
    (20_000, 93),
    (10_000, 91),
    (5_000, 89),
    (2_000, 87),
    (1_000, 85),
    (500, 81),
    (200, 76),
    (0, 70),
)

#: Trần cho trend Havi tự tổng hợp — đặt dưới mọi trend có từ 1.000 lượt tìm thật
#: trở lên. Khi hai nguồn đứng cạnh nhau, thứ đo được luôn nổi lên trước. Chênh
#: lệch nằm ở điểm chứ không ở một cái nhãn trên UI: nhãn thì người đọc bỏ qua,
#: còn thứ tự sắp xếp thì không.
_SYNTHESIZED_CEILING = 80

#: Google trả `approx_traffic` theo locale: "50K+", "50.000+", "50,000+". Bốc số
#: ra thay vì tra bảng chuỗi — bảng chuỗi trượt hết khi Google đổi cách viết, và
#: trượt *âm thầm* thành điểm mặc định, tức là mọi trend trông giống nhau.
_TRAFFIC_NUMBER_RE = re.compile(r"([\d][\d.,\s]*)\s*([KMkm])?")


def _parse_traffic(traffic: str) -> int:
    """Số lượt tìm kiếm xấp xỉ. `0` khi không đọc được chuỗi."""
    match = _TRAFFIC_NUMBER_RE.search(traffic or "")
    if not match:
        return 0
    digits = re.sub(r"[.,\s]", "", match.group(1))
    if not digits:
        return 0
    value = int(digits)
    suffix = (match.group(2) or "").upper()
    if suffix == "K":
        value *= 1_000
    elif suffix == "M":
        value *= 1_000_000
    return value


def calculate_deterministic_trend_score(
    traffic: str, rank: int, *, is_live_google_trends: bool
) -> int:
    """Điểm nóng của một trend — **tất định**, không có random.

    Vì sao không dùng `random`: trước đây điểm được bốc ngẫu nhiên, nên cùng một
    từ khoá tải lại trang hai lần cho hai thứ tự khác nhau. Chủ tiệm thấy trend
    nhảy chỗ giữa hai lần nhìn thì không còn tin bảng xếp hạng nữa — và một bảng
    xếp hạng không ai tin thì không đáng tồn tại.

    Điểm = trần − thứ hạng. Trần lấy theo lưu lượng thật nếu là trend đo được từ
    Google, còn trend Havi tự tổng hợp dùng một trần thấp hơn. Trừ theo thứ hạng
    để giữ đúng thứ tự nguồn trả về khi nhiều từ khoá cùng rơi vào một mức.
    """
    if is_live_google_trends:
        volume = _parse_traffic(traffic)
        ceiling = next(score for threshold, score in _TRAFFIC_TIERS if volume >= threshold)
    else:
        ceiling = _SYNTHESIZED_CEILING

    # Kẹp lại: điểm âm hoặc trên 100 là vô nghĩa với người đọc.
    return max(1, min(100, ceiling - min(rank, 20)))


class TrendScoutService:
    def __init__(self) -> None:
        self._trends: dict[str, TrendingTopic] = {t.id: t for t in ALL_DYNAMIC_TREND_POOLS}
        self._last_fetched_at: datetime | None = None

    async def _fetch_google_trends_live_vn(self, count: int = 5) -> list[dict[str, str]]:
        """Quét luồng dữ liệu tìm kiếm xu hướng thời gian thực từ Google Trends Việt Nam."""
        url = "https://trends.google.com/trending/rss?geo=VN"
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        try:
            async with httpx.AsyncClient(timeout=6.0, headers=headers) as client:
                res = await client.get(url)
                if res.status_code == 200:
                    root = ET.fromstring(res.text)
                    items = root.findall(".//item")
                    results = []
                    for it in items[:count]:
                        title = it.find("title").text if it.find("title") is not None else ""
                        approx_traffic = it.find(
                            "{https://trends.google.com/trending/rss}approx_traffic"
                        )
                        traffic = approx_traffic.text if approx_traffic is not None else "10K+"
                        if title:
                            results.append({"keyword": title.strip(), "traffic": traffic.strip()})
                    return results
        except Exception as exc:
            logger.warning("Google Trends live RSS fetch error: %s", exc)
        return []

    async def get_hot_trends(self, workspace_id: UUID) -> list[TrendingTopic]:
        """Lấy danh sách các chủ đề hot nhất hôm nay được xếp hạng theo trend_score."""
        # Nếu chưa từng quét hoặc dữ liệu cũ, kích hoạt quét ngầm thời gian thực
        if not self._last_fetched_at:
            try:
                await self.refresh_trends(workspace_id)
            except Exception as e:
                logger.warning("Auto refresh hot trends failed: %s", e)
        return sorted(self._trends.values(), key=lambda t: t.trend_score, reverse=True)[:5]

    async def _scout_trends_with_gemini(
        self,
        live_keywords: list[dict[str, str]],
        industry: str = "Đào tạo nghề & Công nghệ",
        brand_name: str = "Trung Tâm Công Nghệ Nhật Minh",
        count: int = 5,
    ) -> list[TrendingTopic] | None:
        settings = get_settings()
        if not settings.gemini_api_key or settings.gemini_api_key in (
            "mock",
            "mock-gemini-key",
            "change-me",
        ):
            return None

        live_kw_context = (
            "\n".join([f"- {k['keyword']} (Lượt tìm kiếm: {k['traffic']})" for k in live_keywords])
            if live_keywords
            else "Các xu hướng công nghệ, AI Agent, việc làm đang hot."
        )

        prompt = f"""
Bạn là Giám đốc Sáng tạo & Radar Trinh Sát Xu Hướng Short-form Video (TikTok, YouTube Shorts, Facebook Reels) tại Việt Nam hôm nay.
Dưới đây là các từ khóa đang tìm kiếm trực tiếp trên Google Trends Việt Nam hôm nay:
{live_kw_context}

Hãy biến các trend này thành {count} kịch bản Newsjacking (Bắt trend xã hội giật gân $\\rightarrow$ Bẻ lái sang giải pháp & khóa học của "{brand_name}" - Ngành: {industry}).

Quy tắc bắt buộc:
- Keyword ngắn gọn, trực diện, kích thích tò mò.
- `sample_hook`: Câu Hook 3s đầu tiên cực kỳ giật gân, in hoa, giữ chân người xem ngay lập tức (Ví dụ: "KHI THIÊN HẠ MÃI HÓNG BIẾN THÌ DÂN AI ĐANG LÀM GÌ?").
- `trend_score`: Độ nóng từ 90 đến 99.
- `source`: Nguồn phát hiện (ví dụ "Google Trends VN Live", "TikTok Trending VN").
- `suggested_angle`: Cú bẻ lái (Plot Twist) từ trend nóng sang dịch vụ/giá trị của {brand_name}.
- `suggested_hashtags`: 4-6 hashtag viral tiếng Việt.
- Trả về danh sách JSON đúng cấu trúc.
"""
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "systemInstruction": {
                "parts": [
                    {"text": "Bạn là chuyên gia trinh sát xu hướng video ngắn viral tại Việt Nam."}
                ]
            },
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "keyword": {"type": "string"},
                            "category": {"type": "string"},
                            "trend_score": {"type": "integer"},
                            "source": {"type": "string"},
                            "hook_style": {"type": "string"},
                            "sample_hook": {"type": "string"},
                            "suggested_angle": {"type": "string"},
                            "suggested_hashtags": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                        "required": [
                            "id",
                            "keyword",
                            "category",
                            "trend_score",
                            "source",
                            "hook_style",
                            "sample_hook",
                            "suggested_angle",
                            "suggested_hashtags",
                        ],
                    },
                },
            },
        }
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent"
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post(url, params={"key": settings.gemini_api_key}, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    text = data["candidates"][0]["content"]["parts"][0]["text"]
                    items = json.loads(text)
                    results = []
                    for idx, it in enumerate(items):
                        traffic_hint = live_keywords[idx]["traffic"] if idx < len(live_keywords) else "10K+"
                        score = calculate_deterministic_trend_score(traffic_hint, idx, is_live_google_trends=True)
                        t = TrendingTopic(
                            id=it.get("id") or f"gemini-trend-{random.randint(1000, 9999)}",
                            keyword=it["keyword"],
                            category=TrendCategory.TECH_EDUCATION,
                            trend_score=score,
                            source="Google Trends VN (Xác thực 15 phút trước)",
                            hook_style=HookStyle.WARNING_MISTAKE,
                            sample_hook=it["sample_hook"],
                            suggested_angle=it["suggested_angle"],
                            suggested_hashtags=it.get(
                                "suggested_hashtags", ["#viral", "#shorts", "#xuhuong"]
                            ),
                            discovered_at=datetime.now(UTC),
                        )
                        results.append(t)
                        self._trends[t.id] = t
                    return sorted(results, key=lambda x: x.trend_score, reverse=True)
        except Exception as exc:
            logger.warning("Gemini live trend scouting error, falling back: %s", exc)
        return None

    async def refresh_trends(
        self,
        workspace_id: UUID,
        industry: str = "Đào tạo nghề & Công nghệ",
        brand_name: str = "Trung Tâm Công Nghệ Nhật Minh",
        count: int = 5,
    ) -> list[TrendingTopic]:
        """Quét và làm mới danh sách xu hướng thời gian thực từ Google Trends Live VN + Gemini AI Radar."""
        self._last_fetched_at = datetime.now(UTC)

        # 1. Quét dữ liệu thời gian thực từ Google Trends VN
        live_kw = await self._fetch_google_trends_live_vn(count=count)

        # 2. Gọi Gemini kết hợp Live Trends để bẻ lái sang Nhật Minh
        gemini_trends = await self._scout_trends_with_gemini(live_kw, industry, brand_name, count)
        if gemini_trends:
            return gemini_trends

        # 3. Nếu live_kw có dữ liệu mà chưa có Gemini key, tự động tạo newsjacking từ live Google Trends
        if live_kw:
            live_synthesized: list[TrendingTopic] = []
            for idx, kw_item in enumerate(live_kw):
                kw = kw_item["keyword"]
                traffic = kw_item["traffic"]
                trend_id = f"google-live-{abs(hash(kw)) % 10000}"
                score = calculate_deterministic_trend_score(traffic, idx, is_live_google_trends=True)
                t = TrendingTopic(
                    id=trend_id,
                    keyword=f"Trend nóng: {kw.upper()} ({traffic} tìm kiếm)",
                    category=TrendCategory.TECH_EDUCATION
                    if idx % 2 == 0
                    else TrendCategory.VIRAL_MEME,
                    trend_score=score,
                    source="Google Trends VN (Xác thực 15 phút trước)",
                    hook_style=HookStyle.REAL_COMPARISON,
                    sample_hook=f"TẠI SAO CẢ NƯỚC ĐANG TÌM KIẾM '{kw.upper()}'?",
                    suggested_angle=f"Bẻ lái từ độ nóng của '{kw}' sang cách dân công nghệ tại {brand_name} tự động hóa công việc bằng AI Agent để tăng thu nhập.",
                    suggested_hashtags=[
                        "#googletrends",
                        "#xuhuong",
                        "#aiagent",
                        "#nhatminhtech",
                        "#shorts",
                    ],
                    discovered_at=datetime.now(UTC),
                )
                self._trends[t.id] = t
                live_synthesized.append(t)
            return sorted(live_synthesized, key=lambda x: x.trend_score, reverse=True)

        # 4. Fallback pool
        shuffled = list(ALL_DYNAMIC_TREND_POOLS)
        random.shuffle(shuffled)
        selected = shuffled[:count]

        for idx, t in enumerate(selected):
            t.trend_score = calculate_deterministic_trend_score("5K+", idx, is_live_google_trends=False)
            t.source = "Ý tưởng Havi — Phân tích ngành"
            t.discovered_at = datetime.now(UTC)
            self._trends[t.id] = t

        return sorted(selected, key=lambda t: t.trend_score, reverse=True)

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
