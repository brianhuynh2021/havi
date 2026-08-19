"""Quota token theo workspace — chặn chi phí LLM trước khi nó xảy ra.

**Tính theo token, không theo tiền.** Lý do: mỗi provider một đơn giá, giá LLM
đổi liên tục, và một bảng giá hardcode lạc hậu cho ra con số *nhìn như đúng* —
tệ hơn không có quota, vì nó tạo cảm giác đang kiểm soát chi phí trong khi
không. Số token là sự thật tuyệt đối trong `event_log`, không phụ thuộc bảng giá
nào cả. Muốn ra tiền thì nhân ngoài, ở chỗ định giá gói.

Trần đặt theo gói (`core.enums.Plan`), quy về mốc dương lịch đầu tháng theo giờ
VN — chủ tiệm hiểu "hết quota tháng này, mùng 1 có lại", không phải "30 ngày kể
từ lần đăng ký".
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from core.enums import Plan

VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")

#: Trần token mỗi tháng theo gói.
#:
#: Con số dựng từ ước lượng vận hành, không phải từ bảng giá provider: một content
#: job (prompt + brand profile + 3 draft) tốn cỡ 3–6 nghìn token, nên 500k token
#: ≈ 80–150 job/tháng cho gói Tiệm Nhỏ — vượt xa nhịp một tiệm đăng 2 bài/ngày.
#: Trial thấp hơn nhiều để một tài khoản dùng thử không đốt hết ngân sách tháng.
#:
#: Đây là số cần đo lại sau pilot (ROADMAP §9 Economics), không phải hằng số
#: vĩnh viễn — sửa ở đúng một chỗ này.
MONTHLY_TOKEN_QUOTA: dict[Plan, int] = {
    Plan.TRIAL: 100_000,
    Plan.TIEM_NHO: 500_000,
    Plan.TOAN_DIEN: 2_000_000,
    Plan.DOANH_NGHIEP: 5_000_000,
}

#: Ngưỡng cảnh báo — vượt mức này thì UI nên nói trước, đừng để chủ tiệm chỉ
#: biết khi đã bị chặn giữa lúc đang cần đăng bài.
WARNING_THRESHOLD = 0.8


class QuotaExceeded(Exception):
    """Workspace đã dùng hết token tháng này.

    Mang theo số liệu để router dựng được câu thông báo có ích ("đã dùng
    480k/500k") thay vì chỉ một chữ "hết quota".
    """

    def __init__(self, *, used: int, limit: int, resets_at: datetime) -> None:
        super().__init__(
            f"Đã dùng {used:,}/{limit:,} token trong tháng này — "
            f"quota mở lại vào {resets_at.astimezone(VN_TZ):%d/%m/%Y}"
        )
        self.used = used
        self.limit = limit
        self.resets_at = resets_at


@dataclass(frozen=True)
class QuotaStatus:
    used: int
    limit: int
    #: Mốc quota mở lại (đầu tháng sau, giờ VN quy về UTC).
    resets_at: datetime

    @property
    def remaining(self) -> int:
        return max(0, self.limit - self.used)

    @property
    def exceeded(self) -> bool:
        return self.used >= self.limit

    @property
    def near_limit(self) -> bool:
        """Đã qua ngưỡng cảnh báo nhưng chưa bị chặn."""
        if self.limit <= 0:
            return False
        return not self.exceeded and self.used / self.limit >= WARNING_THRESHOLD


def quota_for(plan: Plan) -> int:
    """Trần của gói. Gói lạ (thêm sau mà quên khai) rơi về mức Trial thay vì
    `KeyError` hay vô hạn — chặn sai hướng an toàn thì chỉ là bất tiện, còn để
    không giới hạn là mất tiền thật."""
    return MONTHLY_TOKEN_QUOTA.get(plan, MONTHLY_TOKEN_QUOTA[Plan.TRIAL])


def month_start_utc(now: datetime) -> datetime:
    """Mốc 00:00 ngày 1 tháng này theo giờ VN, trả về UTC.

    Tính theo giờ VN chứ không UTC: quota "tháng 8" phải bắt đầu lúc nửa đêm ở
    Việt Nam. Dùng UTC thì mốc rơi vào 07:00 ngày 1, và 7 tiếng đầu tháng bị tính
    vào quota tháng trước.
    """
    vn_now = now.astimezone(VN_TZ)
    vn_start = vn_now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return vn_start.astimezone(UTC)


def next_month_start_utc(now: datetime) -> datetime:
    """Mốc quota mở lại. Cộng 32 ngày rồi ép về ngày 1 — khỏi phải xử tay số ngày
    của từng tháng và năm nhuận."""
    vn_start = now.astimezone(VN_TZ).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return (vn_start + timedelta(days=32)).replace(day=1).astimezone(UTC)


def evaluate(*, plan: Plan, used: int, now: datetime | None = None) -> QuotaStatus:
    now = now or datetime.now(UTC)
    return QuotaStatus(used=used, limit=quota_for(plan), resets_at=next_month_start_utc(now))
