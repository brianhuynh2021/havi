"""State machine của content item — backend sở hữu, frontend chỉ render trạng thái.

    draft → pending_approval → approved → scheduled → publishing → published | failed
    failed → publishing (retry có backoff, max N lần) → dead_letter

Mọi nội dung đều bắt buộc qua bước duyệt (pending_approval → approved).
Reply cho khách KHÔNG dùng state machine này và KHÔNG BAO GIỜ tự động gửi.
"""

from core.enums import ContentStatus, PublishMode

MAX_PUBLISH_RETRIES = 3

_TRANSITIONS: dict[ContentStatus, frozenset[ContentStatus]] = {
    ContentStatus.DRAFT: frozenset(
        {ContentStatus.PENDING_APPROVAL, ContentStatus.SCHEDULED, ContentStatus.DISMISSED}
    ),
    ContentStatus.PENDING_APPROVAL: frozenset(
        {ContentStatus.APPROVED, ContentStatus.DRAFT, ContentStatus.DISMISSED}
    ),
    ContentStatus.APPROVED: frozenset({ContentStatus.SCHEDULED, ContentStatus.DISMISSED}),
    ContentStatus.SCHEDULED: frozenset(
        {ContentStatus.PUBLISHING, ContentStatus.DRAFT, ContentStatus.DISMISSED}
    ),
    ContentStatus.PUBLISHING: frozenset({ContentStatus.PUBLISHED, ContentStatus.FAILED}),
    ContentStatus.PUBLISHED: frozenset(),
    ContentStatus.FAILED: frozenset(
        {ContentStatus.PUBLISHING, ContentStatus.DEAD_LETTER, ContentStatus.DISMISSED}
    ),
    ContentStatus.DEAD_LETTER: frozenset({ContentStatus.DISMISSED}),
    ContentStatus.DISMISSED: frozenset(),
}

TERMINAL_STATUSES = frozenset(
    {ContentStatus.PUBLISHED, ContentStatus.DEAD_LETTER, ContentStatus.DISMISSED}
)

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


def initial_status(publish_mode: PublishMode | None = None) -> ContentStatus:
    """Trạng thái của draft ngay khi Content Engine sinh xong.

    Luôn dừng ở PENDING_APPROVAL, chờ chủ tiệm hoặc người duyệt duyệt trước khi lên lịch đăng.
    """
    return ContentStatus.PENDING_APPROVAL


def next_after_failure(retry_count: int) -> ContentStatus:
    """Sau khi publish lỗi tạm thời: còn lượt thì retry, hết lượt thì vào dead letter."""
    if retry_count >= MAX_PUBLISH_RETRIES:
        return ContentStatus.DEAD_LETTER
    return ContentStatus.PUBLISHING
