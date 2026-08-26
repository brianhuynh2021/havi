"""Bản tin buổi sáng — và ước lượng thời gian tiết kiệm, kèm giả định hiện rõ.

Hai người, hai nhịp
-------------------
Nhân viên trực kênh mở Havi **mỗi ngày** để làm hàng đợi việc. Chủ mở **mỗi
tuần** để biết chuyện gì đã xảy ra và Havi có đáng tiền không. Đó là hai màn hình
khác nhau; nhồi chủ vào hàng đợi của nhân viên là bắt họ đọc 40 dòng để tìm 4 câu.

Bản tin này là màn của chủ: *"24 giờ qua có gì, hiện còn gì phải xử lý, tuần tới
chỗ nào trống lịch."*

Không gọi LLM
-------------
Mọi con số ở đây tính từ dữ liệu Havi đã sở hữu, bằng SQL. Ba lý do, theo thứ tự:

1. **Không bịa được.** Một bản tin do model viết có thể nói "engagement giảm 18%"
   trong khi Havi chưa từng có quyền đọc insights. Số đếm thì không nói được điều
   nó không đo.
2. **Không tốn tiền theo ngày.** Một bản tin LLM mỗi sáng cho mỗi workspace là
   một dòng chi phí chạy mãi — trên gói 189.000đ nó có thể ăn hết biên lợi nhuận.
3. **Xong trước khi bàn tầng thông minh.** 80% giá trị của bản tin là *biết cái
   gì đã đổi*, và cái đó không cần suy luận.

Điều Havi **chưa** nói được, và cố ý không nói: doanh thu từ social (Havi không
có dữ liệu đơn hàng), engagement theo nền tảng (chưa có quyền insights), động thái
đối thủ (miền dữ liệu khác hẳn). Thiếu thì để trống, không đoán.

Thời gian tiết kiệm — phiên bản trung thực
------------------------------------------
"Havi saved you 6h 42m" là con số dễ bán nhất và dễ thành lời nói dối nhất: Havi
không đo được thời gian người dùng *không* mất.

Nên ở đây nó được dựng theo cách kiểm chứng được:

- chỉ đếm việc Havi **thật sự đã làm** — phản hồi đã gửi, bài đã lên kênh;
- nhân với một giả định thời gian **hiện rõ trên màn hình**;
- không đếm những thứ nghe hay mà không đo được ("phát hiện bài lỗi", "khỏi mở
  5 tab") — chúng là giá trị thật nhưng không thành con số thật.

Khách thấy được phép tính thì con số thành một lập luận họ tự kiểm; ẩn phép tính
đi thì nó chỉ là quảng cáo.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

#: Thứ trong tuần bằng tiếng Việt. `weekday()` trả 0 = thứ Hai.
WEEKDAY_NAMES = (
    "Thứ Hai",
    "Thứ Ba",
    "Thứ Tư",
    "Thứ Năm",
    "Thứ Sáu",
    "Thứ Bảy",
    "Chủ Nhật",
)

#: Cửa sổ mặc định của bản tin. 24 giờ chứ không "từ lần xem cuối": chủ mở app
#: thất thường, và một bản tin gộp 9 ngày thì không còn là bản tin buổi sáng.
DEFAULT_WINDOW_HOURS = 24

#: Số ngày tới cần soi chỗ trống lịch. Bảy ngày vì đó là nhịp mà người ta thật sự
#: lập kế hoạch nội dung — báo trống lịch của tháng sau thì không ai làm gì cả.
GAP_LOOKAHEAD_DAYS = 7


@dataclass(frozen=True)
class SavedAction:
    """Một dòng trong phép tính thời gian tiết kiệm.

    `minutes_each` **phải** được hiện ra cùng con số tổng. Đó là điều khiến ước
    lượng này khác một lời quảng cáo.
    """

    action: str
    count: int
    minutes_each: int

    @property
    def minutes_total(self) -> int:
        return self.count * self.minutes_each


#: Giả định thời gian cho mỗi việc Havi làm thay.
#:
#: Con số nhỏ và **cố ý dè dặt**. Gửi một phản hồi qua Havi thay vì mở Messenger,
#: tìm đúng hội thoại, đọc lại ngữ cảnh rồi trả lời: 2 phút là ước lượng thấp.
#: Ước lượng thấp mà khách vẫn thấy đáng tiền thì con số đứng được; ước lượng cao
#: thì khách tự đối chiếu với cảm giác của họ và mất niềm tin vào cả bảng.
#:
#: Chỉ có hai dòng, và đó là chủ ý: đây là hai việc Havi **thật sự thực hiện** và
#: có bản ghi để đếm. "Phát hiện bài đăng lỗi" hay "khỏi mở 5 tab" là giá trị
#: thật nhưng không có mốc nào để đo, nên không được biến thành phút.
MINUTES_PER_REPLY = 2
MINUTES_PER_PUBLISH = 3


def window_start(*, now: datetime | None = None, hours: int = DEFAULT_WINDOW_HOURS) -> datetime:
    return (now or datetime.now(UTC)) - timedelta(hours=hours)


def weekday_name(day: date) -> str:
    return WEEKDAY_NAMES[day.weekday()]


def calendar_gaps(
    *,
    scheduled_dates: set[date],
    today: date,
    lookahead_days: int = GAP_LOOKAHEAD_DAYS,
) -> list[date]:
    """Những ngày tới **chưa có bài nào** xếp lịch.

    Bỏ qua hôm nay: nếu tới sáng nay mà chưa có bài thì đó không còn là chỗ trống
    để lấp, và báo nó chỉ làm người đọc thấy một việc không làm được nữa.
    """
    return [
        day
        for offset in range(1, lookahead_days + 1)
        if (day := today + timedelta(days=offset)) not in scheduled_dates
    ]


def time_saved(*, replies_sent: int, posts_published: int) -> list[SavedAction]:
    """Phép tính thời gian tiết kiệm, dạng từng dòng để hiện ra được.

    Trả cả dòng có `count == 0`: một bảng chỉ hiện dòng khác 0 sẽ đổi hình mỗi
    tuần, và người đọc mất khả năng so sánh tuần này với tuần trước.
    """
    return [
        SavedAction("Trả lời khách", replies_sent, MINUTES_PER_REPLY),
        SavedAction("Đăng bài lên kênh", posts_published, MINUTES_PER_PUBLISH),
    ]


def total_minutes_saved(actions: list[SavedAction]) -> int:
    return sum(action.minutes_total for action in actions)
