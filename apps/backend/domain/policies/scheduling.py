"""Chọn giờ đăng mặc định khi chủ tiệm duyệt mà không chỉ định `scheduled_at`.

Nút "Duyệt" trên draft card không bắt chọn giờ — chủ tiệm chỉ muốn "đăng giùm chị
lúc nào đẹp đẹp". Backend phải tự chọn, và chọn theo giờ Việt Nam chứ không phải
UTC: 19h UTC là 2h sáng ở Sài Gòn, không ai đọc.

Không dùng ML tối ưu giờ đăng ở pilot (ROADMAP §4 "Không làm trong pilot" — chưa
đủ dữ liệu). Đây là heuristic cố định, thay được khi có số liệu thật.
"""

from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

VIETNAM_TZ = ZoneInfo("Asia/Ho_Chi_Minh")

#: Khung giờ vàng theo thói quen lướt mạng ở VN: sáng trước giờ làm, trưa nghỉ,
#: và tối sau bữa cơm. Giờ địa phương, không phải UTC.
GOLDEN_HOURS = (time(8, 0), time(12, 0), time(20, 0))


def next_golden_hour(*, now: datetime | None = None) -> datetime:
    """Khung giờ vàng gần nhất còn ở tương lai, trả về dạng UTC-aware.

    Trả UTC vì cột `scheduled_at` lưu UTC; frontend đổi lại sang giờ VN khi hiển thị.
    """
    current = (now or datetime.now(UTC)).astimezone(VIETNAM_TZ)
    for slot in GOLDEN_HOURS:
        candidate = current.replace(hour=slot.hour, minute=slot.minute, second=0, microsecond=0)
        if candidate > current:
            return candidate.astimezone(UTC)
    # Qua hết khung giờ hôm nay thì đẩy sang khung đầu tiên của ngày mai.
    tomorrow = current + timedelta(days=1)
    first = GOLDEN_HOURS[0]
    return tomorrow.replace(
        hour=first.hour, minute=first.minute, second=0, microsecond=0
    ).astimezone(UTC)
