"""Chuyển trạng thái hợp lệ của một video post. Domain policy thuần.

Vì sao cần một bảng tường minh thay vì gán `post.status = X` rải rác: bug đắt
nhất của luồng video không phải upload sai, mà là **nhảy cóc trạng thái** — báo
"đã đăng" khi Facebook chưa xác nhận. Bảng này làm cho mỗi cú nhảy cóc thành một
lỗi test chứ không phải một dòng log ai đó đọc sau khi bài đã lên.

Luật quan trọng nhất nằm ở đây, không ở service: `PENDING_RECONCILIATION` không
quay lại `PUBLISHING` được. Mất dấu bài đăng thì phải đi *kiểm tra*, không phải
đăng lại; đăng lại là cách chắc chắn nhất để tạo hai Reels giống hệt nhau trên
Trang của khách.
"""

from core.enums import VideoPostStatus as S

#: Trạng thái kết thúc — không đi tiếp được nữa.
TERMINAL: frozenset[S] = frozenset({S.PUBLISHED, S.FAILED_PERMANENT, S.CANCELLED})

ALLOWED_TRANSITIONS: dict[S, frozenset[S]] = {
    # Clip vừa lên storage. Havi không dựng gì, nên đây là điểm xuất phát.
    S.READY_FOR_REVIEW: frozenset({S.APPROVED, S.CANCELLED, S.FAILED_PERMANENT}),
    S.APPROVED: frozenset({S.PUBLISHING, S.READY_FOR_REVIEW, S.CANCELLED}),
    S.PUBLISHING: frozenset({S.VERIFYING, S.PENDING_RECONCILIATION, S.FAILED}),
    S.VERIFYING: frozenset({S.PUBLISHED, S.PENDING_RECONCILIATION, S.FAILED}),
    # Mất dấu thì chỉ có hai lối ra, và không lối nào là đăng lại ngay.
    S.PENDING_RECONCILIATION: frozenset({S.PUBLISHED, S.FAILED_PERMANENT}),
    # Hỏng trước khi Facebook cấp id thì gửi lại được — quay về chờ duyệt để chủ
    # tiệm nhìn lại caption một lần nữa thay vì tự động bắn đi.
    S.FAILED: frozenset({S.READY_FOR_REVIEW, S.FAILED_PERMANENT, S.CANCELLED}),
    S.PUBLISHED: frozenset(),
    S.FAILED_PERMANENT: frozenset(),
    S.CANCELLED: frozenset(),
}


class InvalidStateTransition(Exception):
    """Cú nhảy trạng thái không được phép."""

    def __init__(self, current: S, target: S) -> None:
        self.current = current
        self.target = target
        allowed = sorted(x.value for x in ALLOWED_TRANSITIONS.get(current, frozenset()))
        super().__init__(
            f"Không được chuyển {current.value} → {target.value}. "
            f"Từ {current.value} chỉ đi được tới: {allowed or ['(kết thúc)']}"
        )


def can_transition(current: S, target: S) -> bool:
    return target in ALLOWED_TRANSITIONS.get(current, frozenset())


def assert_transition(current: S, target: S) -> None:
    """Ném `InvalidStateTransition` nếu cú nhảy không hợp lệ."""
    if not can_transition(current, target):
        raise InvalidStateTransition(current, target)


def is_terminal(status: S) -> bool:
    return status in TERMINAL


def is_publishable(status: S) -> bool:
    """Chỉ clip đã được chủ tiệm duyệt mới được gửi đi đăng."""
    return status == S.APPROVED
