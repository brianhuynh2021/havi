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
    """Sinh nội dung chuyên sâu theo đặc thù từng kênh và ngành nghề."""
    if is_tech:
        if channel == "facebook_page":
            text = (
                f"🔥 {tiem} chính thức khai giảng: {noi_dung}\n\n"
                "📌 Quyền lợi đặc quyền cho học viên:\n"
                "• Đào tạo thực chiến 1 kèm 1 với chuyên gia công nghệ.\n"
                "• Tự tay xây dựng và triển khai AI Agent tự động hóa doanh nghiệp.\n"
                "• Cấp source code & tài liệu độc quyền từ phòng Lab.\n\n"
                "👉 Đăng ký ngay hôm nay để nhận ưu đãi. Nhắn tin trực tiếp cho Fanpage hoặc liên hệ Hotline để được tư vấn lộ trình chi tiết!"
            )
            media_note = "Ảnh chụp phòng Lab công nghệ hoặc poster khóa học AI Agent"
        elif channel == "google_business":
            text = (
                f"{tiem} thông báo lịch khai giảng và chương trình đào tạo mới: {noi_dung}. "
                "Chương trình phù hợp cho chủ doanh nghiệp, lập trình viên và người muốn ứng dụng AI vào thực tế. "
                "Địa chỉ đào tạo và phòng Lab tại cơ sở chính thức. Liên hệ Hotline để nhận lộ trình học chi tiết."
            )
            media_note = "Ảnh thực tế không gian đào tạo tại cơ sở"
        elif channel == "tiktok":
            text = (
                f"🎬 [HOOK 3S]: Bạn có muốn tự tay xây AI Agent chốt khách tự động 24/7 chỉ sau 1 khóa học?\n\n"
                f"💡 [THỰC CHIẾN]: Tại {tiem}, {noi_dung}. Học viên không học lý thuyết suông mà được cầm tay chỉ việc trực tiếp trên máy trạm!\n\n"
                "🚀 [CTA]: Follow kênh và để lại comment hoặc nhắn tin để nhận ngay voucher giảm 20% học phí nhé! #AIAgent #NhatMinhTech #TuDongHoa #HocLapTrinh #viral"
            )
            media_note = "Quay video dọc 9:16 cận cảnh thao tác lập trình bot trên màn hình và tương tác 1 kèm 1"
        elif channel == "youtube":
            text = (
                f"⚡ [SHORTS]: Hướng dẫn xây dựng AI Agent thực chiến cùng {tiem}!\n\n"
                f"Hôm nay mình chia sẻ thông tin: {noi_dung}. Đào tạo 1 kèm 1 giúp bạn làm chủ công nghệ tự động hóa ngay từ buổi học đầu tiên.\n\n"
                "👉 Đăng ký kênh để xem thêm nhiều bài học AI bổ ích! #Shorts #AIAgent #NhatMinhTech"
            )
            media_note = "Video demo chạy thử bot AI Agent tự động trả lời khách hàng"
        else:
            text = f"Chào anh/chị, {tiem} xin gửi thông tin khóa học: {noi_dung}. Anh/chị nhắn lại tin này để nhận tư vấn lộ trình và giữ suất ưu đãi nhé!"
            media_note = "Ảnh tóm tắt lộ trình đào tạo"
    else:
        if channel == "facebook_page":
            text = (
                f"Chào cả nhà, {tiem} có thông báo mới nè! {noi_dung}\n\n"
                "Tiệm luôn chăm chút tỉ mỉ từng chi tiết để mang lại trải nghiệm tốt nhất cho quý khách. "
                "Mọi người nhanh tay nhắn tin cho tiệm để nhận ưu đãi sớm nhất nhé!"
            )
            media_note = "Ảnh chụp sản phẩm / dịch vụ thực tế tại tiệm"
        elif channel == "google_business":
            text = (
                f"{tiem} thông báo: {noi_dung}. "
                "Quý khách vui lòng liên hệ trước để được phục vụ chu đáo nhất."
            )
            media_note = "Ảnh cơ sở kinh doanh"
        elif channel == "tiktok":
            text = (
                f"Góc thực chiến tại {tiem}! {noi_dung} "
                "Bạn thấy thế nào? Hãy thả tim và bình luận bên dưới nhé! #fyp #viral"
            )
            media_note = "Video ngắn 15-30s quay không gian và trải nghiệm khách hàng"
        elif channel == "youtube":
            text = (
                f"{tiem} chia sẻ trải nghiệm thực tế: {noi_dung}. "
                "Theo dõi kênh để đón xem nhiều nội dung thú vị nhé! #Shorts"
            )
            media_note = "Video ngắn giới thiệu dịch vụ"
        else:
            text = f"Chào anh/chị, {tiem} gửi anh/chị thông tin ưu đãi: {noi_dung}. Anh/chị nhắn lại tin này để em hỗ trợ đặt lịch nhanh nhất nhé!"
            media_note = "Ảnh ưu đãi"

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
                ("zalo_oa", "Tin Zalo"),
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
