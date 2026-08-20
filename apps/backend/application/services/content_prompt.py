"""Dựng prompt cho Content Engine từ brand profile + liệu thô.

Prompt production nằm ở backend, không bao giờ lộ ra frontend bundle (ROADMAP.md
§1 nguyên tắc #6).
"""

from core.enums import Channel, Industry, RawInputKind
from domain.models.workspace import BrandProfile, Workspace

#: Kênh mà pilot thật sự sinh nội dung cho. Không sinh cho kênh chưa có adapter
#: publish — draft không đăng được chỉ làm chủ tiệm thất vọng (ROADMAP.md §2:
#: không hứa capability chưa có).
PILOT_CHANNELS: tuple[Channel, ...] = (
    Channel.FACEBOOK_PAGE,
    Channel.GOOGLE_BUSINESS,
    Channel.TIKTOK,
    Channel.YOUTUBE,
    Channel.REELS,
)

_INDUSTRY_LABELS: dict[Industry, str] = {
    Industry.SPA: "spa / thẩm mỹ viện / tiệm chăm sóc sắc đẹp",
    Industry.FOOD_BEVERAGE: "quán ăn / tiệm cà phê / tiệm bánh",
    Industry.RETAIL_SHOP: "cửa hàng bán lẻ / shop thời trang / tạp hóa",
    Industry.ONLINE_SHOP: "cửa hàng bán lẻ / shop bán hàng online",
    Industry.EDUCATION: "trung tâm giáo dục / ngoại ngữ / đào tạo nghề & công nghệ",
    Industry.LOCAL_SERVICE: "chi nhánh dịch vụ / phòng khám y tế / điểm giao dịch",
    Industry.REAL_ESTATE: "môi giới bất động sản / văn phòng nhà đất",
    Industry.PROFESSIONAL: "dịch vụ chuyên môn / văn phòng tư vấn",
    Industry.OTHER: "cơ sở kinh doanh & dịch vụ",
}

_SYSTEM_PROMPT = """\
Bạn là Havi — nhân viên marketing của một {industry} ở Việt Nam.

Viết nội dung tiếng Việt tự nhiên như người chủ tiệm tự viết, KHÔNG như quảng cáo \
công ty lớn. Ngắn, cụ thể, dễ đọc trên điện thoại.

Giọng văn của tiệm: {tone}

Quy tắc bắt buộc:
- Chỉ viết tiếng Việt. Không dùng thuật ngữ marketing kiểu "khách hàng mục tiêu", \
"chiến dịch", "engagement".
- Không hứa hẹn quá mức, không cam kết kết quả tuyệt đối.
- KHÔNG được dùng những cách nói sau, kể cả viết khác dấu hay khác cách: {banned}
- Mỗi kênh một bản riêng, viết đúng đặc thù kênh, KHÔNG copy y nguyên giữa các kênh.
- `media_note` là gợi ý cho chủ tiệm về ảnh/video cần chuẩn bị (với video thì \
ghi rõ gợi ý góc quay/hành động), viết ngắn.

Trả về JSON đúng schema đã cho, gồm chính xác {num_channels} bản nháp cho đúng {num_channels} kênh được yêu cầu — mỗi kênh trong danh sách một bản, tuyệt đối không bỏ sót kênh nào.\
"""

_CHANNEL_GUIDANCE: dict[Channel, str] = {
    Channel.FACEBOOK_PAGE: (
        "Facebook Page: bài viết dài kể chuyện cảm xúc (3-6 câu), có emoji vừa phải, kết bằng lời mời ghé tiệm "
        'hoặc nhắn tin tư vấn. `kind` đặt là "Bài ảnh".'
    ),
    Channel.GOOGLE_BUSINESS: (
        "Google Business: bài cập nhật chuẩn SEO địa điểm Google Maps, mô tả dịch vụ rõ ràng, chuyên nghiệp, "
        'kéo khách ghé cơ sở hoặc liên hệ Hotline. `kind` đặt là "Cập nhật Google".'
    ),
    Channel.TIKTOK: (
        "TikTok: kịch bản video ngắn (Hook 3s đầu kích thích tò mò giật tít, nội dung cô đọng 15-30s, "
        'lời kêu gọi follow/ghé tiệm, 3-5 hashtag ngành #fyp #xuhuong). `kind` đặt là "Video TikTok".'
    ),
    Channel.YOUTUBE: (
        "YouTube Shorts: kịch bản video dọc dưới 60s (Hook mở đầu, hướng dẫn/chia sẻ mẹo kỹ thuật hữu ích, "
        'kết bằng tag #Shorts). `kind` đặt là "YouTube Shorts".'
    ),
    Channel.REELS: (
        "Facebook Reels: kịch bản video ngắn 15-30s bắt trend tương tác cao, có Hook 3s đầu ấn tượng "
        'và lời bình tự nhiên. `kind` đặt là "Facebook Reels".'
    ),
    Channel.ZALO_OA: (
        "Zalo OA: nhắn như nói với khách quen, xưng hô đúng (chị/anh), rất ngắn "
        '(2-3 câu), có lời mời cụ thể. `kind` đặt là "Tin Zalo".'
    ),
}

_RAW_INPUT_LABELS: dict[RawInputKind, str] = {
    RawInputKind.PHOTO: "Ảnh chủ tiệm vừa gửi",
    RawInputKind.VOICE: "Ghi âm chủ tiệm vừa gửi",
    RawInputKind.TEXT: "Ghi chú chủ tiệm gõ",
    RawInputKind.SALES_WEBHOOK: "Dữ liệu từ phần mềm bán hàng",
}


def build_system_prompt(
    workspace: Workspace,
    profile: BrandProfile,
    target_channels: list[Channel] | None = None,
) -> str:
    channels = target_channels if target_channels is not None else list(PILOT_CHANNELS)
    tone = profile.tone.strip() or "thân thiện, gần gũi, gọi khách là chị/anh"
    banned = ", ".join(profile.banned_claims) if profile.banned_claims else "(chưa có)"
    return _SYSTEM_PROMPT.format(
        industry=_INDUSTRY_LABELS.get(workspace.industry, "kinh doanh nhỏ"),
        tone=tone,
        banned=banned,
        num_channels=len(channels),
    )


def build_user_prompt(
    *,
    workspace: Workspace,
    raw_inputs: list[dict],
    media_descriptions: list[str],
    target_channels: list[Channel] | None = None,
) -> str:
    channels = target_channels if target_channels is not None else list(PILOT_CHANNELS)
    lines = [f"Tên tiệm: {workspace.name}", "", "Liệu thô chủ tiệm vừa nạp:"]

    for item in raw_inputs:
        kind = item.get("kind", "")
        label = _RAW_INPUT_LABELS.get(kind, "Liệu thô")  # type: ignore[arg-type]
        text = (item.get("text") or "").strip()
        lines.append(f"- {label}" + (f": {text}" if text else ""))

    if media_descriptions:
        lines += ["", "File đã nạp:"] + [f"- {d}" for d in media_descriptions]

    lines += ["", "Viết nội dung cho các kênh sau:"]
    lines += [
        f"- {_CHANNEL_GUIDANCE[channel]}" for channel in channels if channel in _CHANNEL_GUIDANCE
    ]
    return "\n".join(lines)
