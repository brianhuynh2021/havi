"""Gói cước: hạn dùng thử, đổi gói, và trạng thái suy ra từ thời gian.

Policy thuần: không I/O, không SDK, không cổng thanh toán. Vào là gói + hai mốc
thời gian, ra là kết luận. Cổng thanh toán thật (VNPay/Momo) sẽ gọi vào đây để
biết đổi gói có hợp lệ không, chứ không tự quyết.

Vì sao trạng thái được *suy ra* chứ không lưu: `status` lưu trong DB là một bản
sao của sự thật "bây giờ là mấy giờ", và bản sao đó sai ngay khi đồng hồ nhích
qua `trial_ends_at` mà không có job nào chạy. Một workspace hết hạn lúc nửa đêm
sẽ vẫn đọc là `trialing` cho tới lần cron kế tiếp — tức là dùng chùa hợp lệ theo
dữ liệu. Suy ra từ `now` thì không có khe đó.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from core.enums import Plan, SubscriptionStatus

#: Số ngày dùng thử, khớp bảng giá landing page ("0đ 7 ngày").
TRIAL_DAYS = 7

#: Giá tháng theo gói, đơn vị VND. Trial 0đ.
#:
#: Để ở domain policy chứ không ở cổng thanh toán: đây là quyết định kinh doanh,
#: và cổng thanh toán chỉ là cách thu tiền. Đổi giá thì sửa đúng một chỗ này.
MONTHLY_PRICE_VND: dict[Plan, int] = {
    Plan.TRIAL: 0,
    Plan.TIEM_NHO: 189_000,
    Plan.TOAN_DIEN: 369_000,
    Plan.DOANH_NGHIEP: 799_000,
}


class PlanChangeNotAllowed(Exception):
    """Đổi gói bị từ chối, kèm lý do đọc được cho chủ tiệm."""


def trial_end_for(started_at: datetime) -> datetime:
    """Mốc hết hạn dùng thử tính từ lúc tạo workspace."""
    return started_at + timedelta(days=TRIAL_DAYS)


def price_for(plan: Plan) -> int:
    """Giá tháng của gói. Gói lạ về 0 chứ không `KeyError` — nhưng gói lạ không
    bao giờ tới được đây vì `Plan` là enum đóng."""
    return MONTHLY_PRICE_VND.get(plan, 0)


@dataclass(frozen=True)
class SubscriptionState:
    plan: Plan
    status: SubscriptionStatus
    #: Mốc kết thúc kỳ hiện tại: hết hạn trial, hoặc hết tháng đã trả tiền.
    current_period_end: datetime | None

    @property
    def is_active(self) -> bool:
        """Còn được dùng tính năng tốn tiền hay không.

        `PAST_DUE` tính là KHÔNG còn: hết hạn dùng thử mà chưa trả tiền thì dừng,
        chứ không phục vụ tiếp rồi đi đòi sau.
        """
        return self.status in (SubscriptionStatus.TRIALING, SubscriptionStatus.ACTIVE)


def _to_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def state_for(
    *,
    plan: Plan,
    trial_ends_at: datetime | None,
    paid_until: datetime | None,
    now: datetime | None = None,
) -> SubscriptionState:
    """Trạng thái gói tại thời điểm `now`.

    Thứ tự quyết định:

    1. Gói trả tiền còn hạn -> `ACTIVE`.
    2. Gói trả tiền hết hạn -> `PAST_DUE` (đã từng trả, giờ nợ kỳ mới).
    3. Còn trong hạn dùng thử -> `TRIALING`.
    4. Hết hạn dùng thử -> `PAST_DUE`.

    `trial_ends_at is None` (dữ liệu cũ trước khi có cột này) được coi là còn
    dùng thử, không phải hết hạn: không biết thì không được khoá tài khoản của
    người đang dùng thật.
    """
    now_utc = _to_utc(now) or datetime.now(UTC)
    trial_ends = _to_utc(trial_ends_at)
    paid_until_utc = _to_utc(paid_until)

    if plan is not Plan.TRIAL:
        if paid_until_utc is None or paid_until_utc > now_utc:
            return SubscriptionState(plan, SubscriptionStatus.ACTIVE, paid_until_utc)
        return SubscriptionState(plan, SubscriptionStatus.PAST_DUE, paid_until_utc)

    if trial_ends is None or trial_ends > now_utc:
        return SubscriptionState(plan, SubscriptionStatus.TRIALING, trial_ends)
    return SubscriptionState(plan, SubscriptionStatus.PAST_DUE, trial_ends)


def check_plan_change(*, current: Plan, target: Plan) -> None:
    """Ném `PlanChangeNotAllowed` nếu đổi gói không hợp lệ.

    Không cho quay về `TRIAL`: dùng thử là thứ mỗi workspace chỉ có một lần, và
    cho hạ về trial nghĩa là ai cũng có thể tự gia hạn 14 ngày miễn phí vô hạn
    bằng cách nâng rồi hạ.
    """
    if target is current:
        raise PlanChangeNotAllowed(f"Workspace đang ở gói {current.value} rồi")
    if target is Plan.TRIAL:
        raise PlanChangeNotAllowed(
            "Không quay lại gói dùng thử được — dùng thử chỉ có một lần cho mỗi tiệm"
        )
