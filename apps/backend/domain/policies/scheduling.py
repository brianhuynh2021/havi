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


def spread_over_golden_hours(
    count: int,
    *,
    per_day: int = 1,
    now: datetime | None = None,
) -> list[datetime]:
    """Rải `count` bài ra các khung giờ vàng, mỗi ngày `per_day` bài.

    Vì sao cần hàm này thay vì gọi `next_golden_hour()` cho từng bài: nó trả về
    cùng một mốc cho mọi lời gọi trong cùng một giây. Chủ tiệm ngồi một buổi
    viết sáu bài rồi bấm "duyệt hết" sẽ nhận về sáu bài đăng **cùng một phút** —
    Trang trông như bị spam, và sáu ngày sau đó im lặng. Đúng ngược lại thứ họ
    muốn: mỗi ngày một câu chuyện.

    Cách rải:

    * Bài đầu tiên vào khung giờ vàng gần nhất còn ở tương lai.
    * Mỗi ngày lấy `per_day` khung đầu tiên trong `GOLDEN_HOURS` (8h, 12h, 20h),
      hết thì sang ngày kế tiếp.
    * Ngày đầu chỉ dùng những khung **chưa trôi qua** — đặt lịch vào quá khứ là
      cách để scheduler đăng dồn tất cả ngay lượt quét kế tiếp.

    Trả về UTC-aware theo đúng thứ tự truyền vào, để caller ghép 1-1 với danh
    sách bài của mình.
    """
    if count <= 0:
        return []
    per_day = max(1, min(per_day, len(GOLDEN_HOURS)))

    current = (now or datetime.now(UTC)).astimezone(VIETNAM_TZ)
    slots: list[datetime] = []
    day_offset = 0

    while len(slots) < count:
        day = current + timedelta(days=day_offset)
        for slot in GOLDEN_HOURS[:per_day]:
            candidate = day.replace(
                hour=slot.hour, minute=slot.minute, second=0, microsecond=0
            )
            # Ngày đầu tiên: bỏ qua khung đã trôi qua. Các ngày sau luôn hợp lệ.
            if day_offset == 0 and candidate <= current:
                continue
            slots.append(candidate.astimezone(UTC))
            if len(slots) == count:
                break
        day_offset += 1

    return slots
