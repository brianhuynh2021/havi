"""Khi nào nhắc gia hạn, và nhắc bao nhiêu lần.

Vì sao tồn tại
--------------
Thanh toán VietQR không có card-on-file: **mỗi tháng khách phải chủ động quyết
định trả tiếp**. Trong SaaS, chuyển từ auto-renew sang thanh toán chủ động làm
churn tăng nhiều lần.

Havi đã có banner nhắc trong app khi còn ≤7 ngày, nhưng nó có một lỗ hổng logic:
**người sắp rời đi chính là người đã ngừng mở app**, nên họ không thấy banner đó.
Nhắc ra ngoài app là cách duy nhất tới được đúng ca churn thật.

Nhắc ở mốc, không nhắc mỗi ngày
-------------------------------
Task chạy một lần mỗi ngày và chỉ gửi khi số ngày còn lại **khớp đúng một mốc**.
Nhờ vậy không cần bảng lưu "đã nhắc chưa": mỗi workspace nhận tối đa bốn lần
trước khi hết hạn và hai lần sau đó.

Nhắc mỗi ngày thì người ta thôi đọc — và một kênh thông báo bị bỏ qua thì tệ hơn
không có, vì lần thật sự cần đọc cũng bị bỏ qua cùng.

Mốc âm là sau khi đã hết hạn: `-1` để bắt ca "quên mất", `-7` là lần cuối trước
khi coi như khách đã rời.
"""

from datetime import UTC, datetime

from core.enums import Plan, SubscriptionStatus

#: Số ngày còn lại mà tại đó gửi nhắc. Âm = đã quá hạn.
#:
#: 7 để kịp chuẩn bị, 3 và 1 để nhắc lại, 0 là ngày cuối. Không có mốc 14: nhắc
#: hai tuần trước thì khách gạt đi và lần nhắc sau bị coi là trùng lặp.
REMINDER_DAYS = (7, 3, 1, 0, -1, -7)


def days_until(paid_until: datetime | None, *, now: datetime | None = None) -> int | None:
    """Số ngày còn lại của kỳ. `None` khi workspace không có mốc hết hạn.

    Làm tròn **xuống**: còn 1,9 ngày thì trả 1. Nhắc sớm hơn thực tế thì vô hại,
    nhắc muộn hơn thì khách mất quyền giữa lúc đang trực khách.
    """
    if paid_until is None:
        return None
    reference = now or datetime.now(UTC)
    if paid_until.tzinfo is None:
        paid_until = paid_until.replace(tzinfo=UTC)
    return (paid_until - reference).days


def should_remind(
    *,
    plan: Plan,
    status: SubscriptionStatus,
    paid_until: datetime | None,
    now: datetime | None = None,
) -> bool:
    """`True` khi hôm nay đúng là ngày gửi nhắc cho workspace này.

    Bỏ qua workspace đang dùng thử: hết hạn trial không phải một lần gia hạn bị
    quên, nó là một quyết định mua chưa từng xảy ra. Nhắc gia hạn ở đó là đòi tiền
    một người chưa từng trả — việc của bán hàng, không phải của cảnh báo vận hành.

    Bỏ qua workspace đã huỷ: họ đã nói không.
    """
    if plan is Plan.TRIAL:
        return False
    if status is SubscriptionStatus.CANCELED:
        return False

    remaining = days_until(paid_until, now=now)
    if remaining is None:
        return False
    return remaining in REMINDER_DAYS


def reminder_summary(*, workspace_name: str, days_left: int) -> str:
    """Câu gửi cho đội vận hành.

    Viết cho **người sẽ gọi khách**, không viết cho log: có tên thương hiệu và
    việc cần làm, không có id hay mã trạng thái. Người đọc câu này đang mở
    danh bạ, không mở terminal.
    """
    if days_left < 0:
        return (
            f"{workspace_name} đã hết hạn {abs(days_left)} ngày — "
            f"gọi hỏi xem còn dùng tiếp không."
        )
    if days_left == 0:
        return f"{workspace_name} hết hạn hôm nay — nhắc khách quét VietQR."
    return f"{workspace_name} còn {days_left} ngày là hết hạn — nhắc khách trước."
