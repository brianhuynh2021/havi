"""Mock provider cho local dev — sinh draft hợp lệ mà không gọi API tính tiền.

Khác `FakeProvider` ở `fake.py`: cái đó là test double, mỗi test tự nhét sẵn
chuỗi output nó muốn. Cái này tự chế bài từ chính prompt nhận được, để chạy tay
ở local ra nội dung đọc được như thật — bấm "Để Havi viết cho chị" mười lần
cũng không tốn đồng nào.

Không dùng ở staging/production: ở đó phải gọi model thật mới biết prompt và
schema có thực sự ổn không (xem `build_provider_router`).
"""

import json
import re

from domain.ports.llm import (
    LLMProvider,
    LLMProviderPort,
    LLMRequest,
    LLMResponse,
)

# Ba kênh pilot, khớp `DEFAULT_CHANNELS` mà prompt yêu cầu. Mỗi kênh một giọng
# riêng — Facebook kể chuyện, Zalo nhắn trực tiếp, Google Business trang trọng —
# để lúc xem trên UI còn phân biệt được kênh nào ra kênh nào.
_TEMPLATES: list[tuple[str, str, str]] = [
    (
        "facebook_page",
        "Bài ảnh",
        "🚀 ĐỘT PHÁ NĂNG SUẤT CÙNG {tiem}!\n\n"
        "💡 {noi_dung}\n\n"
        "✨ Điểm khác biệt tại Nhật Minh:\n"
        "• Đào tạo thực chiến 100% trên dự án thật.\n"
        "• Giảng viên cầm tay chỉ việc 1:1.\n"
        "• Ứng dụng AI Agent tự động hóa vận hành hiệu quả ngay sau khóa học.\n\n"
        "📞 Hotline / Zalo tư vấn: 0984 883 750\n"
        "#{tiem_tag} #AIAgent #KhoaHocAI #CongNgheThucChien",
    ),
    (
        "youtube",
        "YouTube Shorts",
        "⚡ KHÁM PHÁ THỰC TẾ TẠI {tiem}!\n\n"
        "{noi_dung}\n\n"
        "👉 Đăng ký kênh (Subscribe) để cập nhật những kiến thức AI Agent mới nhất! #Shorts #AIAgent #NhatMinhTech",
    ),
    (
        "tiktok",
        "TikTok Clip",
        "🎬 3 BƯỚC TỰ TẠO AI AGENT CHO RIÊNG BẠN — KHÔNG CẦN BIẾT CODE!\n\n"
        "💡 {noi_dung}\n\n"
        "🚀 Học thực hành 1:1 tại {tiem}. Nhấn Follow kênh để nhận trọn bộ tài liệu AI Agent miễn phí! #AIAgent #TechTrend #xuhuong #HocAI",
    ),
    (
        "reels",
        "Facebook Reels",
        "🔥 BÍ QUYẾT TỰ ĐỘNG HÓA x5 LẦN NĂNG SUẤT VỚI AI AGENT!\n\n"
        "{noi_dung}\n\n"
        "📞 Hotline tư vấn: 0984 883 750 • {tiem}\n"
        "#ReelsVN #AIAgent #NhatMinhTech #XuHuong",
    ),
    (
        "zalo_oa",
        "Tin Zalo",
        "Chào Quý anh/chị, {tiem} xin gửi thông tin chi tiết: {noi_dung}\n\n"
        "Quý anh/chị vui lòng liên hệ Hotline 0984 883 750 để được hỗ trợ tư vấn và nhận ưu đãi học phí tốt nhất!",
    ),
    (
        "google_business",
        "Cập nhật Google",
        "📍 {tiem} — ĐÀO TẠO & GIẢI PHÁP AI AGENT THỰC CHIẾN TẠI TP.HCM\n\n"
        "📌 {noi_dung}\n\n"
        "⭐ Đào tạo thực hành 1:1 trên máy thật • Giảng viên hướng dẫn trực tiếp • Cam kết làm được việc ngay.\n"
        "📞 Hotline: 0984 883 750 | Địa chỉ: TP. Hồ Chí Minh.",
    ),
]

_SHOP_FALLBACK = "Trung Tâm Công Nghệ Nhật Minh"


def _extract(pattern: str, text: str, fallback: str) -> str:
    match = re.search(pattern, text, re.MULTILINE)
    return match.group(1).strip() if match else fallback


def _join_raw_inputs(user_prompt: str) -> str:
    lines = user_prompt.splitlines()
    try:
        start = next(i for i, line in enumerate(lines) if line.startswith("Liệu thô"))
    except StopIteration:
        return ""

    parts: list[str] = []
    for line in lines[start + 1 :]:
        if not line.strip():
            break
        if ":" in line:
            text = line.split(":", 1)[1].strip()
            if text:
                parts.append(text)

    joined = " ".join(parts).strip()
    if joined and not joined.endswith((".", "!", "?")):
        joined += "."
    return joined


def _generate_smart_draft(channel: str, kind: str, tiem: str, noi_dung: str, is_tech: bool) -> tuple[str, str]:
    """Sinh nội dung chuyên sâu, văn phong công nghệ sắc bén, chuẩn mực cho từng kênh."""
    clean_content = noi_dung.rstrip(".")
    tiem_tag = tiem.replace(" ", "")
    
    if channel == "facebook_page":
        text = (
            f"🚀 ĐỘT PHÁ NĂNG SUẤT CÙNG {tiem.upper()}!\n\n"
            f"💡 {clean_content}.\n\n"
            "✨ 3 giá trị thực chiến vượt trội tại Nhật Minh:\n"
            "1️⃣ Cầm tay chỉ việc 1:1, học trên máy tính và dự án thật.\n"
            "2️⃣ Tự xây dựng hệ thống AI Agent tự động hóa vận hành, nhân bản năng suất x5 lần.\n"
            "3️⃣ Đội ngũ chuyên gia đồng hành hỗ trợ kỹ thuật lâu dài.\n\n"
            "📞 Hotline / Zalo tư vấn: 0984 883 750\n\n"
            f"#{tiem_tag} #AIAgent #TuDongHoa #KhoaHocAI #CongNgheThucChien"
        )
        media_note = "Ảnh chụp thực tế không gian phòng học công nghệ hoặc infographic giải pháp AI"
    elif channel == "google_business":
        text = (
            f"📍 {tiem.upper()} — ĐÀO TẠO & GIẢI PHÁP AI AGENT THỰC CHIẾN\n\n"
            f"📌 {clean_content}.\n\n"
            "⭐ Chương trình đào tạo chuyên sâu từ cơ bản đến thực tế, giảng viên hướng dẫn trực tiếp 1:1, thực hành trên máy thật và dự án thực tế.\n"
            "📞 Hotline tư vấn: 0984 883 750 | Địa chỉ: TP. Hồ Chí Minh."
        )
        media_note = "Ảnh chụp mặt tiền trung tâm công nghệ hoặc phòng thực hành hiện đại"
    elif channel == "tiktok":
        text = (
            f"🎬 3 BƯỚC TỰ TẠO AI AGENT CHO RIÊNG BẠN — KHÔNG CẦN BIẾT CODE!\n\n"
            f"💡 {clean_content}!\n\n"
            f"🚀 Đào tạo thực hành 1:1 tại {tiem}. Nhấn Follow kênh để nhận trọn bộ tài liệu và Prompt AI Agent độc quyền! #AIAgent #TechTrend #xuhuong #HocAI #{tiem_tag}"
        )
        media_note = "Video dọc 9:16 có chuyển động zoom và phụ đề vàng neon nổi bật ở 3 giây đầu"
    elif channel == "youtube":
        text = (
            f"⚡ KHÁM PHÁ CÔNG NGHỆ AI AGENT THỰC CHIẾN TẠI {tiem.upper()}!\n\n"
            f"{clean_content}.\n\n"
            "👉 Đăng ký kênh (Subscribe) để cập nhật những video chia sẻ giải pháp tự động hóa AI mới nhất! #Shorts #AIAgent #NhatMinhTech"
        )
        media_note = "Clip ngắn 9:16 có phụ đề chữ vàng viền đen nổi bật ở 3 giây đầu"
    elif channel == "reels":
        text = (
            f"🔥 BÍ QUYẾT TỰ ĐỘNG HÓA x5 LẦN NĂNG SUẤT VỚI AI AGENT!\n\n"
            f"{clean_content}.\n\n"
            f"📞 Hotline tư vấn: 0984 883 750 • {tiem}\n"
            f"#ReelsVN #AIAgent #{tiem_tag} #XuHuong"
        )
        media_note = "Video ngắn 15s nhịp điệu nhanh, bắt mắt"
    else:
        text = (
            f"Chào Quý anh/chị, {tiem} xin gửi thông tin chi tiết: {clean_content}.\n\n"
            "Quý anh/chị vui lòng liên hệ Hotline 0984 883 750 để nhận hỗ trợ tư vấn và ưu đãi học phí tốt nhất!"
        )
        media_note = "Ảnh tóm tắt ưu đãi khóa học"

    return text, media_note


class MockProvider(LLMProviderPort):
    """Trả draft thông minh dựng từ prompt cho local dev."""

    @property
    def provider(self) -> LLMProvider:
        return LLMProvider.GEMINI

    @property
    def is_configured(self) -> bool:
        return True

    async def generate(self, request: LLMRequest) -> LLMResponse:
        tiem = _extract(r"^Tên tiệm:\s*(.+)$", request.user_prompt, _SHOP_FALLBACK)
        noi_dung = _join_raw_inputs(request.user_prompt) or "khai giảng khóa học công nghệ mới và ưu đãi dịch vụ."

        combined_check = f"{tiem} {noi_dung} {request.user_prompt}".lower()
        is_tech = any(k in combined_check for k in ["công nghệ", "tech", "ai", "agent", "lập trình", "đào tạo", "khóa học", "nhật minh"])

        target_channels = []
        for ch, name in [
            ("facebook_page", "Bài ảnh"),
            ("google_business", "Cập nhật Google"),
            ("tiktok", "Video TikTok"),
            ("youtube", "YouTube Shorts"),
            ("reels", "Facebook Reels"),
            ("zalo_oa", "Tin Zalo"),
        ]:
            if ch in request.user_prompt or ch.replace("_", " ") in request.user_prompt.lower():
                target_channels.append((ch, name))

        if not target_channels:
            target_channels = [
                ("facebook_page", "Bài ảnh"),
                ("google_business", "Cập nhật Google"),
                ("tiktok", "Video TikTok"),
                ("youtube", "YouTube Shorts"),
                ("reels", "Facebook Reels"),
            ]

        drafts = []
        for ch, kind in target_channels:
            text, media_note = _generate_smart_draft(ch, kind, tiem, noi_dung, is_tech)
            drafts.append({
                "channel": ch,
                "kind": kind,
                "text": text,
                "media_note": media_note,
            })

        output_json = json.dumps({"drafts": drafts}, ensure_ascii=False)

        return LLMResponse(
            text=output_json,
            provider=self.provider,
            model="mock-local",
            tokens_in=len(request.system_prompt + request.user_prompt) // 4,
            tokens_out=len(output_json) // 4,
            latency_ms=1,
        )
