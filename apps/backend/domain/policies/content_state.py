"""State machine của content item — backend sở hữu, frontend chỉ render trạng thái.

    draft → pending_approval → approved → scheduled → publishing → published | failed
    failed → publishing (retry có backoff, max N lần) → dead_letter

`full_auto` chỉ bỏ qua cặp pending_approval → approved; mọi trạng thái sau giữ nguyên.
Reply cho khách KHÔNG dùng state machine này và KHÔNG BAO GIỜ có full_auto.
"""

from core.enums import ContentStatus, PublishMode

MAX_PUBLISH_RETRIES = 3

_TRANSITIONS: dict[ContentStatus, frozenset[ContentStatus]] = {
    ContentStatus.DRAFT: frozenset({ContentStatus.PENDING_APPROVAL, ContentStatus.SCHEDULED}),
    ContentStatus.PENDING_APPROVAL: frozenset({ContentStatus.APPROVED, ContentStatus.DRAFT}),
    ContentStatus.APPROVED: frozenset({ContentStatus.SCHEDULED}),
    ContentStatus.SCHEDULED: frozenset({ContentStatus.PUBLISHING, ContentStatus.DRAFT}),
    ContentStatus.PUBLISHING: frozenset({ContentStatus.PUBLISHED, ContentStatus.FAILED}),
    ContentStatus.PUBLISHED: frozenset(),
    ContentStatus.FAILED: frozenset({ContentStatus.PUBLISHING, ContentStatus.DEAD_LETTER}),
    ContentStatus.DEAD_LETTER: frozenset(),
}

TERMINAL_STATUSES = frozenset({ContentStatus.PUBLISHED, ContentStatus.DEAD_LETTER})

#: Đã lên mạng rồi thì không cho sửa giờ đăng (kéo-thả trên Lịch đăng).
RESCHEDULABLE_STATUSES = frozenset({ContentStatus.APPROVED, ContentStatus.SCHEDULED})


class InvalidTransitionError(ValueError):
    """Chuyển trạng thái không hợp lệ — trả về HTTP 409 ở tầng API."""

    def __init__(self, current: ContentStatus, target: ContentStatus) -> None:
        super().__init__(f"Không thể chuyển content item từ {current} sang {target}")
        self.current = current
        self.target = target


def can_transition(current: ContentStatus, target: ContentStatus) -> bool:
    return target in _TRANSITIONS[current]


def assert_transition(current: ContentStatus, target: ContentStatus) -> None:
    if not can_transition(current, target):
        raise InvalidTransitionError(current, target)


def allowed_transitions(current: ContentStatus) -> frozenset[ContentStatus]:
    return _TRANSITIONS[current]


def initial_status(publish_mode: PublishMode) -> ContentStatus:
    """Trạng thái của draft ngay khi Content Engine sinh xong.

    `review_first` (mặc định): dừng ở PENDING_APPROVAL, chờ chủ tiệm duyệt.
    `full_auto` (opt-in): vào thẳng SCHEDULED.
    """
    if publish_mode is PublishMode.FULL_AUTO:
        return ContentStatus.SCHEDULED
    return ContentStatus.PENDING_APPROVAL


def next_after_failure(retry_count: int) -> ContentStatus:
    """Sau khi publish lỗi tạm thời: còn lượt thì retry, hết lượt thì vào dead letter."""
    if retry_count >= MAX_PUBLISH_RETRIES:
        return ContentStatus.DEAD_LETTER
    return ContentStatus.PUBLISHING
