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
        "Chào cả nhà, {tiem} có tin vui nè! {noi_dung} "
        "Tiệm làm cẩn thận từng bước nên chị em cứ yên tâm nha. "
        "Chị nào quan tâm thì nhắn tiệm để được tư vấn thêm ạ!",
    ),
    (
        "youtube",
        "YouTube Shorts",
        "{tiem} chia sẻ kỹ thuật thực tế: {noi_dung} "
        "Theo dõi kênh để xem thêm nhiều bài học bổ ích nhé! #Shorts",
    ),
    (
        "tiktok",
        "TikTok Clip",
        "Góc thực chiến tại {tiem}! {noi_dung} "
        "Bạn thấy thế nào? Hãy bình luận bên dưới nhé! #fyp #viral",
    ),
    (
        "reels",
        "Facebook Reels",
        "{tiem} bật mí phương pháp mới: {noi_dung} "
        "Thả tim và lưu lại clip để áp dụng ngay nhé!",
    ),
    (
        "zalo_oa",
        "Tin Zalo",
        "Chào chị, {tiem} gửi chị thông tin ạ: {noi_dung} "
        "Chị nhắn lại tin này để em sắp lịch giúp chị nhé!",
    ),
    (
        "google_business",
        "Cập nhật Google",
        "{tiem} thông báo: {noi_dung} "
        "Quý khách vui lòng liên hệ trước để được phục vụ chu đáo nhất.",
    ),
]

_SHOP_FALLBACK = "Tiệm"


def _extract(pattern: str, text: str, fallback: str) -> str:
    match = re.search(pattern, text, re.MULTILINE)
    return match.group(1).strip() if match else fallback


def _join_raw_inputs(user_prompt: str) -> str:
    """Gom liệu thô từ khối "Liệu thô chủ tiệm vừa nạp:" trong user prompt.

    Bám đúng cấu trúc `build_user_prompt` dựng ra: mỗi dòng dạng
    `- <nhãn>: <text>`, và khối kết thúc ở dòng trống. Ảnh/ghi âm không có text
    nên bị bỏ qua — mock chỉ kể lại được phần chữ.
    """
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
    """Sinh nội dung chuyên sâu, văn phong sắc bén theo đặc thù từng kênh và ngành nghề."""
    clean_content = noi_dung.rstrip(".")
    
    if channel == "facebook_page":
        text = (
            f"🌟 {tiem.upper()} THÔNG BÁO QUAN TRỌNG!\n\n"
            f"👉 {clean_content}.\n\n"
            "✨ Lý do bạn không nên bỏ lỡ dịp này:\n"
            "• Dịch vụ & giải pháp được thiết kế tỉ mỉ, tối ưu trải nghiệm thực tế.\n"
            "• Đội ngũ tận tâm, đồng hành hỗ trợ chu đáo từ A đến Z.\n"
            "• Ưu đãi đặc biệt dành riêng cho khách hàng tương tác sớm hôm nay.\n\n"
            "📩 Inbox ngay cho Fanpage hoặc để lại bình luận để nhận thông tin chi tiết và voucher ưu đãi độc quyền nhé!\n\n"
            f"#{tiem.replace(' ', '')} #DichVuMoi #UuDaiDacBiet #TraiNghiemTuyetVoi"
        )
        media_note = "Ảnh chụp thực tế không gian hoặc poster nổi bật của dịch vụ mới"
    elif channel == "google_business":
        text = (
            f"📌 {tiem} trân trọng giới thiệu: {clean_content}.\n\n"
            "Chúng tôi cam kết mang đến chất lượng dịch vụ chuẩn mực, tận tâm và chuyên nghiệp hàng đầu khu vực. "
            "Quý khách có thể ghé trực tiếp cơ sở hoặc liên hệ Hotline 0984 883 750 để được tư vấn chu đáo và nhận báo giá ưu đãi tốt nhất!"
        )
        media_note = "Ảnh chụp mặt tiền cơ sở hoặc sản phẩm / dịch vụ thực tế"
    elif channel == "tiktok":
        text = (
            f"🎬 [HOOK 3S]: Bạn đã biết tin cực hot này tại {tiem} chưa?\n\n"
            f"💡 [THỰC TẾ]: {clean_content}! Trải nghiệm thực tế cực kỳ chất lượng và đáng tiền.\n\n"
            "🚀 [KÊU GỌI]: Bấm Follow kênh ngay hôm nay và thả tim để không bỏ lỡ những bí quyết hữu ích tiếp theo nhé! #fyp #xuhuong #trending #viral #khampha"
        )
        media_note = "Video dọc 9:16 quay nhanh 15s các điểm nhấn dịch vụ với nhạc nền xu hướng"
    elif channel == "youtube":
        text = (
            f"⚡ [SHORTS]: Khám phá thực tế tại {tiem}!\n\n"
            f"Hôm nay cùng xem trải nghiệm đặc biệt: {clean_content}. Từng công đoạn đều được thực hiện cẩn thận và chuyên nghiệp.\n\n"
            "👉 Đăng ký kênh (Subscribe) để cập nhật thêm nhiều video thực tế hấp dẫn nhé! #Shorts #ReviewThucTe"
        )
        media_note = "Clip ngắn 9:16 có phụ đề chữ vàng viền đen nổi bật ở 3 giây đầu"
    elif channel == "reels":
        text = (
            f"🔥 [REELS]: Bí quyết độc quyền từ {tiem}!\n\n"
            f"{clean_content}. Đừng quên lưu lại video này để áp dụng ngay cùng bạn bè nhé!\n\n"
            "#ReelsVN #XuHuong #KhamPha"
        )
        media_note = "Video ngắn 15s nhịp điệu nhanh, bắt mắt"
    else:
        text = (
            f"Chào anh/chị, {tiem} xin gửi thông tin dịch vụ: {clean_content}. "
            "Anh/chị nhắn lại tin này để nhận hỗ trợ tư vấn và ưu đãi tốt nhất nhé!"
        )
        media_note = "Ảnh tóm tắt ưu đãi"

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
