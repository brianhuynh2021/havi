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

#: Token output nặng gấp mấy lần token input khi tính vào quota.
#:
#: Ở mọi provider, output đắt hơn input 4–5 lần (xem `MODEL_RATES` ở
#: `pricing.py`). Cộng thẳng hai chiều thành một số thì hai workspace cùng đụng
#: trần có thể chênh nhau vài lần chi phí thật — quota lúc đó chặn *khối lượng*,
#: không chặn *chi phí*, mà chặn chi phí mới là việc nó tồn tại để làm.
#:
#: Là một **tỷ lệ**, không phải một mức giá: nó không lạc hậu khi provider đổi
#: bảng giá, chỉ cần sửa nếu tỷ lệ input/output thay đổi về bản chất. Đó là lý do
#: quota vẫn tính bằng "token" chứ không bằng tiền.
OUTPUT_WEIGHT = 4

#: Trần token mỗi tháng theo gói, tính theo **token đã trọng số**
#: (`tokens_in + tokens_out × OUTPUT_WEIGHT`).
#:
#: Con số dựng từ ước lượng vận hành, không phải từ bảng giá provider: một content
#: job (prompt + brand profile + 3 draft) tốn cỡ 3–6 nghìn token thô, trong đó
#: output chiếm phần lớn — nên sau trọng số nó vào khoảng 10–20 nghìn. 2 triệu
#: token trọng số ≈ 100–200 job/tháng cho gói Khởi Nghiệp, vượt xa nhịp một cơ sở
#: đăng 2 bài/ngày.
#:
#: Trần đã được nhân lên cùng lúc với việc áp trọng số, nên **khối lượng dùng
#: được không đổi** so với bản trước — thay đổi duy nhất là workspace tiêu nhiều
#: output giờ chạm trần sớm hơn workspace tiêu nhiều input, đúng như chi phí thật.
#:
#: Đây là số cần đo lại sau pilot (ROADMAP §9 Economics), không phải hằng số
#: vĩnh viễn — sửa ở đúng một chỗ này.
MONTHLY_TOKEN_QUOTA: dict[Plan, int] = {
    Plan.TRIAL: 400_000,
    Plan.TIEM_NHO: 2_000_000,
    Plan.TOAN_DIEN: 8_000_000,
    Plan.DOANH_NGHIEP: 20_000_000,
}

#: Token (đã trọng số) cho một bài, dùng khi workspace **chưa đủ dữ liệu** để đo.
#:
#: Tồn tại vì "hạn mức 2.000.000 token" không có nghĩa gì với một chủ cơ sở, còn
#: "còn khoảng 130 bài" thì có. Nhưng quy đổi bằng một hằng số ẩn là bịa: hai
#: workspace có prompt và brand profile khác nhau tiêu token khác nhau rõ rệt.
#:
#: Nên cách dùng đúng là: **đo từ chính workspace đó** khi đã có đủ mẫu, và chỉ
#: rơi về hằng số này khi chưa có — kèm nói rõ trên màn hình rằng đang dùng ước
#: lượng mặc định. Người dùng thấy được giả định thì họ tự hiệu chỉnh kỳ vọng.
ASSUMED_TOKENS_PER_POST = 15_000

#: Cần bao nhiêu bài đã sinh mới coi là đủ mẫu để đo. Dưới mức này thì trung bình
#: dao động quá mạnh — một job lỗi dài dòng cũng đủ làm lệch con số.
MIN_SAMPLES_FOR_MEASURED_RATE = 5

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
