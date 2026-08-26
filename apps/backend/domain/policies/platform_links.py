"""Link mở đúng chỗ trên nền tảng — hoặc `None` khi không dựng được link đúng.

Vì sao tính năng này tồn tại
----------------------------
Cái tốn thời gian của người trực kênh không phải lúc trả lời, mà là lúc **đi tìm
xem có gì cần trả lời**: mở Facebook, mở TikTok, mở YouTube, cuộn từng nơi, và
vẫn sót. Havi gom mọi việc về một hàng đợi; từ đó xử lý trong Havi cũng được, mà
bấm một cái sang thẳng nền tảng cũng được. **Cả hai đều là kết quả tốt.**

Đây cùng một khuôn với ranh giới quảng cáo ở `ROADMAP §1c`: Havi kiểm tra, chuẩn
bị, rồi mở đúng trang trên nền tảng để người dùng tự làm phần còn lại.

Nguyên tắc: thà không có nút hơn là nút dẫn sai
-----------------------------------------------
Hàm ở đây trả `None` bất cứ khi nào không chắc link mở ra đúng thứ đó. Một nút
"Mở trên Facebook" dẫn tới trang chủ Facebook tệ hơn không có nút: người dùng bấm
vài lần rồi học được rằng bấm cũng chẳng để làm gì, và sau đó bỏ qua cả lúc nó
thật sự dẫn đúng — cùng một lý do vì sao dải "đang bình thường" ở Tổng quan không
có link.

Vì thế **tin nhắn Messenger trả `None` một cách cố ý**: hội thoại Messenger của
một Trang không có URL công khai dựng được từ PSID. Muốn có link tới đúng hội
thoại thì cần đọc thêm thread id qua Graph API — chưa làm, và đoán một URL là
đúng loại sai mà module này tồn tại để tránh.
"""

from core.enums import InboxItemType, Platform

_FACEBOOK = "https://www.facebook.com"


def inbox_item_url(
    *,
    platform: Platform | str,
    item_type: InboxItemType | str,
    external_message_id: str | None,
) -> str | None:
    """Link tới đúng bình luận / đánh giá trên nền tảng, hoặc `None`.

    Bình luận Facebook có id dạng `{post_id}_{comment_id}`, và
    `facebook.com/{id}` chuyển hướng tới đúng bình luận đó khi người xem có
    quyền. Đó là link duy nhất trong nhóm này mà dựng được từ dữ liệu Havi đang
    lưu.
    """
    if not external_message_id:
        return None

    platform_value = platform.value if isinstance(platform, Platform) else platform
    type_value = item_type.value if isinstance(item_type, InboxItemType) else item_type

    if platform_value != Platform.FACEBOOK.value:
        # TikTok và YouTube chưa bật; Zalo OA hoãn. Thêm khi kênh đó chạy thật,
        # kèm một id đã kiểm là mở đúng chỗ.
        return None

    if type_value == InboxItemType.MESSAGE.value:
        # Xem docstring module: cố ý không đoán URL hội thoại Messenger.
        return None

    if type_value in (InboxItemType.COMMENT.value, InboxItemType.REVIEW.value):
        return f"{_FACEBOOK}/{external_message_id}"

    return None


def published_post_url(*, platform: Platform | str, external_post_id: str | None) -> str | None:
    """Link tới bài đã đăng, hoặc `None`.

    `external_post_id` của Facebook có dạng `{page_id}_{post_id}`; đó chính là
    thứ `facebook.com/{id}` phân giải được. Nó cũng là bằng chứng bài đã lên
    thật — Havi chỉ ghi `published` khi nền tảng trả về id này.
    """
    if not external_post_id:
        return None
    platform_value = platform.value if isinstance(platform, Platform) else platform
    if platform_value != Platform.FACEBOOK.value:
        return None
    return f"{_FACEBOOK}/{external_post_id}"
