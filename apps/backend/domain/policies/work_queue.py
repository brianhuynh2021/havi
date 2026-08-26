"""Thứ tự hàng đợi việc — cái gì nổi lên trước.

Havi là chỗ ngồi làm việc của người trực kênh: mọi việc từ mọi kênh về một hàng
đợi. Nhưng "một hàng đợi" chỉ có ích nếu nó **xếp đúng thứ tự**. Xếp thuần theo
thời gian thì câu hỏi giá của khách nằm dưới ba câu hỏi giờ mở cửa đến sau, và
người trực ca hết giờ trước khi tới nó.

Thứ tự ở đây xếp theo **thiệt hại khi bỏ sót**, không theo mức độ khó hay theo
loại kỹ thuật.
"""

from enum import IntEnum, StrEnum

from domain.policies.inbox_triage import TicketCategory


class WorkKind(StrEnum):
    """Loại việc trong hàng đợi. Bốn nguồn, một danh sách."""

    #: Kênh mất quyền / hết hạn token.
    CONNECTION = "connection"
    #: Tin nhắn, bình luận, đánh giá chờ trả lời.
    INBOX = "inbox"
    #: Bài đăng thất bại, chưa ai xử lý.
    PUBLISH_FAILURE = "publish_failure"
    #: Bản nháp chờ người có quyền duyệt.
    APPROVAL = "approval"


class Priority(IntEnum):
    """Số nhỏ nổi lên trước.

    Để thưa (0, 10, 20…) để chèn mức mới về sau không phải sửa lại cả thang.
    """

    #: Kênh chết thì mọi việc khác vô nghĩa — không đăng được, không nhận được
    #: tin mới, và số liệu trên màn hình đang nói dối về hiện trạng.
    BLOCKING = 0
    #: Khiếu nại. Xếp trên hỏi giá: hỏi giá bị chậm thì có thể mất một đơn, còn
    #: khiếu nại bị bỏ mặc thì thành đánh giá một sao và mất nhiều đơn.
    REPUTATION = 10
    #: Khách đang muốn mua: hỏi giá, đặt lịch. Tiền đang đứng chờ.
    REVENUE = 20
    #: Bài không lên được kênh. Mất âm thầm — không ai phàn nàn, nên nếu không
    #: đẩy lên đây thì không bao giờ có ai xử lý.
    SILENT_LOSS = 30
    #: Khách hỏi thông tin. Cần trả lời, nhưng chậm một giờ không mất gì.
    ROUTINE = 40
    #: Nháp chờ duyệt. Công việc bị chặn, nhưng **chưa mất gì** — nội dung vẫn
    #: nằm đó. Thấp hơn mọi thứ liên quan tới khách đang đợi.
    INTERNAL = 50
    #: Không phân loại được.
    UNSORTED = 60


#: Loại tin trong hộp thư → mức ưu tiên.
_INBOX_PRIORITY: dict[TicketCategory, Priority] = {
    TicketCategory.COMPLAINT: Priority.REPUTATION,
    TicketCategory.PRICE: Priority.REVENUE,
    TicketCategory.BOOKING: Priority.REVENUE,
    TicketCategory.INFO: Priority.ROUTINE,
    TicketCategory.OTHER: Priority.UNSORTED,
}


def priority_for(*, kind: WorkKind, category: str | None = None) -> int:
    """Mức ưu tiên của một việc trong hàng đợi.

    `category` chỉ có nghĩa với `WorkKind.INBOX`; các loại khác bỏ qua nó.
    Category lạ hoặc thiếu rơi về `UNSORTED` — cuối hàng đợi, nhưng **vẫn trong
    hàng đợi**. Không việc nào được biến mất chỉ vì không phân loại được.
    """
    if kind is WorkKind.CONNECTION:
        return int(Priority.BLOCKING)
    if kind is WorkKind.PUBLISH_FAILURE:
        return int(Priority.SILENT_LOSS)
    if kind is WorkKind.APPROVAL:
        return int(Priority.INTERNAL)

    if category is None:
        return int(Priority.UNSORTED)
    try:
        return int(_INBOX_PRIORITY[TicketCategory(category)])
    except (ValueError, KeyError):
        return int(Priority.UNSORTED)
