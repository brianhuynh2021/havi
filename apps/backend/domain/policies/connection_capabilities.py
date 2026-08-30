"""Một kết nối **đã nối** thực sự làm được gì — suy từ quyền nền tảng đã cấp.

Khác `channel_capabilities`, file cạnh bên: ở đó là luật của nền tảng (TikTok
không nhận bài chữ, vì TikTok là thế). Ở đây là chuyện của **một kết nối cụ
thể**: cùng Facebook, kết nối của tiệm A trả lời được Messenger còn tiệm B thì
không, vì hai người cấp quyền khác nhau.

Vấn đề file này giải
--------------------
Havi từng đòi đủ mọi quyền mới cho nối kênh. Chủ tiệm bấm cấp quyền, chờ qua màn
hình Facebook, rồi bị đá về tay trắng chỉ vì thiếu một quyền họ có thể không cần
— tiệm chưa dùng Messenger vẫn bị chặn vì thiếu `pages_messaging`. Đó là
all-or-nothing: đánh đổi cả kết nối để lấy sự chắc chắn về một tính năng phụ.

Giờ kênh nối được với những gì có, còn tính năng thiếu quyền thì **tắt và nói rõ
là tắt**. Điều kiện để nới lỏng như vậy mà vẫn an toàn: mọi nơi sắp gọi API phải
hỏi trước `has_capability`. Bật/tắt mà không ai kiểm thì lại rơi đúng cái bẫy cũ
— UI báo xanh trong khi Inbox im lặng.

`granted_scopes = None` nghĩa là **không rõ** (kết nối tạo trước khi có cột
này), khác hẳn `[]` là đã hỏi và biết chắc không có quyền nào. Kết nối cũ được
coi là đủ năng lực: chúng đã qua vòng kiểm đủ-mọi-quyền của phiên bản trước, nên
suy ra "không có gì" sẽ tắt oan tính năng đang chạy tốt.
"""

from collections.abc import Sequence
from enum import StrEnum

from core.enums import Platform


class Capability(StrEnum):
    """Việc Havi làm được trên một kênh đã nối."""

    #: Đăng bài đã duyệt lên kênh.
    PUBLISH_POST = "publish_post"
    #: Trả lời bình luận công khai.
    REPLY_COMMENT = "reply_comment"
    #: Nhận và trả lời tin nhắn riêng.
    REPLY_MESSAGE = "reply_message"
    #: Nhận webhook bình luận/tin nhắn về Inbox.
    RECEIVE_INBOX = "receive_inbox"


#: Quyền tối thiểu cho mỗi khả năng, theo từng nền tảng. Thiếu **bất kỳ** quyền
#: nào trong tập là khả năng đó tắt.
_REQUIREMENTS: dict[Platform, dict[Capability, frozenset[str]]] = {
    Platform.FACEBOOK: {
        Capability.PUBLISH_POST: frozenset({"pages_manage_posts"}),
        Capability.REPLY_COMMENT: frozenset({"pages_manage_engagement"}),
        Capability.REPLY_MESSAGE: frozenset({"pages_messaging"}),
        Capability.RECEIVE_INBOX: frozenset({"pages_manage_metadata"}),
    },
}


def capabilities_for(
    platform: Platform, granted_scopes: Sequence[str] | None
) -> frozenset[Capability]:
    """Khả năng của một kết nối.

    `None` = kết nối cũ, chưa ghi quyền → trả về **mọi** khả năng của nền tảng
    (xem docstring module). `[]` = biết chắc không có quyền nào → không khả năng
    nào bật.
    """
    requirements = _REQUIREMENTS.get(platform)
    if requirements is None:
        # Nền tảng chưa khai bảng quyền: không có cơ sở để tắt cái gì, nên coi
        # như đủ. Tắt theo mặc định sẽ làm kênh mới thêm bị vô hiệu âm thầm.
        return frozenset(Capability)
    if granted_scopes is None:
        return frozenset(requirements)

    granted = set(granted_scopes)
    return frozenset(
        capability
        for capability, needed in requirements.items()
        if needed.issubset(granted)
    )


def has_capability(
    platform: Platform, granted_scopes: Sequence[str] | None, capability: Capability
) -> bool:
    """Một khả năng cụ thể có dùng được không — dùng ngay trước khi gọi API."""
    return capability in capabilities_for(platform, granted_scopes)


__all__ = ["Capability", "capabilities_for", "has_capability"]
