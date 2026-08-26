"""Kênh nào nhận được loại nội dung nào — và kênh nào đã thật sự chạy.

Vấn đề file này giải
--------------------
Bộ chọn kênh ở màn Đăng bài trước đây là một mảng viết cứng trong JSX, liệt kê ba
kênh cố định cho **mọi** loại nội dung. Hai chỗ sai:

1. **Liệt kê kênh chưa chạy.** Google Business và Zalo OA nằm trong danh sách dù
   chưa nối được. Người dùng tick vào rồi nhận lỗi lúc đăng — hoặc tệ hơn, tin là
   bài đã lên ba kênh.
2. **Không biết loại nội dung.** TikTok và YouTube **không nhận bài chữ**; chúng
   chỉ nhận video dọc. Một danh sách phẳng cho phép chọn "Bài viết + TikTok", và
   lỗi chỉ lộ ra ở bước đăng.

Bộ chọn kênh phải là **hàm của loại nội dung**, không phải một danh sách tĩnh.

Vì sao đặt ở domain
-------------------
Đây là luật của nền tảng, không phải chuyện hiển thị: TikTok không nhận text vì
TikTok là thế, không vì Havi chọn vậy. Để ở frontend thì backend vẫn nhận được
`kind=post, channel=tiktok` từ một client cũ hoặc một lần gọi API trực tiếp.

`LIVE_CHANNELS` là chỗ duy nhất cần sửa khi một kênh được nền tảng duyệt xong —
xem thứ tự bật kênh ở `docs/product/ROADMAP.md` §Phase C.
"""

from core.enums import Channel, ContentKind

#: Loại nội dung mà mỗi kênh nhận được.
#:
#: `FACEBOOK_PAGE` nhận cả hai vì một bài Trang có thể là chữ, ảnh, hoặc video
#: đính kèm. `REELS` chỉ video: đó là định dạng, không phải một tuỳ chọn.
CHANNEL_ACCEPTS: dict[Channel, frozenset[ContentKind]] = {
    Channel.FACEBOOK_PAGE: frozenset({ContentKind.POST, ContentKind.VIDEO}),
    Channel.REELS: frozenset({ContentKind.VIDEO}),
    Channel.TIKTOK: frozenset({ContentKind.VIDEO}),
    Channel.YOUTUBE: frozenset({ContentKind.VIDEO}),
    Channel.GOOGLE_BUSINESS: frozenset({ContentKind.POST}),
    Channel.ZALO_OA: frozenset({ContentKind.POST}),
    # Email không phải kênh social và không đi qua luồng này — xem ROADMAP §Phase C.
    Channel.EMAIL: frozenset(),
}

#: Kênh **đã chạy thật**: có adapter hoạt động và đã được nền tảng cho phép đăng.
#:
#: Chỉ Facebook. TikTok là kênh kế tiếp nhưng app chưa qua audit nên chỉ đăng được
#: ở chế độ riêng tư — tức là chưa dùng được cho khách hàng thật. Bật một kênh ở
#: đây trước khi nó đăng được thật là hứa một thứ chưa tồn tại.
LIVE_CHANNELS: frozenset[Channel] = frozenset(
    {Channel.FACEBOOK_PAGE, Channel.REELS}
)

#: Nhãn hiện cho người dùng. Tách khỏi `channelLabels` ở frontend vì đây là nhãn
#: của **lựa chọn khi soạn bài**, không phải nhãn của một bài đã đăng: người dùng
#: chọn "Facebook — bài trên Trang", không chọn "facebook_page".
CHANNEL_LABELS: dict[Channel, str] = {
    Channel.FACEBOOK_PAGE: "Facebook — bài trên Trang",
    Channel.REELS: "Facebook Reels",
    Channel.TIKTOK: "TikTok",
    Channel.YOUTUBE: "YouTube Shorts",
    Channel.GOOGLE_BUSINESS: "Google Business Profile",
    Channel.ZALO_OA: "Zalo OA",
    Channel.EMAIL: "Email",
}


def accepts(*, channel: Channel, kind: ContentKind) -> bool:
    """Kênh này có nhận loại nội dung đó không."""
    return kind in CHANNEL_ACCEPTS.get(channel, frozenset())


def channels_for(kind: ContentKind) -> list[Channel]:
    """Kênh đang chạy và nhận được loại nội dung này, thứ tự ổn định.

    Thứ tự theo `Channel` enum chứ không theo dict: danh sách đổi thứ tự giữa hai
    lần tải sẽ làm ô tick nhảy chỗ, và người dùng tick nhầm kênh.
    """
    return [
        channel
        for channel in Channel
        if channel in LIVE_CHANNELS and accepts(channel=channel, kind=kind)
    ]


def reject_reason(*, channel: Channel, kind: ContentKind) -> str | None:
    """Câu giải thích vì sao không đăng được, hoặc `None` nếu hợp lệ.

    Trả chuỗi tiếng Việt đọc được vì nó đi thẳng ra API: người vận hành đọc câu
    này, không phải lập trình viên tra mã lỗi.
    """
    if channel not in LIVE_CHANNELS:
        return (
            f"{CHANNEL_LABELS.get(channel, channel.value)} chưa mở — "
            "kênh chỉ được bật sau khi nền tảng duyệt"
        )
    if not accepts(channel=channel, kind=kind):
        accepted = CHANNEL_ACCEPTS.get(channel, frozenset())
        if not accepted:
            return f"{CHANNEL_LABELS.get(channel, channel.value)} không nhận nội dung từ đây"
        needs = " hoặc ".join(sorted(item.value for item in accepted))
        return (
            f"{CHANNEL_LABELS.get(channel, channel.value)} chỉ nhận {needs} — "
            f"không nhận {kind.value}"
        )
    return None
