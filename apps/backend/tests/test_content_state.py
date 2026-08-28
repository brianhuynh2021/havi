"""State machine là hợp đồng nghiệp vụ, không phải chi tiết implementation — test luôn."""

import pytest

from core.content_state import (
    MAX_PUBLISH_RETRIES,
    InvalidTransitionError,
    assert_transition,
    can_transition,
    initial_status,
    next_after_failure,
)
from core.enums import ContentStatus, PublishMode


def test_review_first_dung_o_pending_approval():
    assert initial_status(PublishMode.REVIEW_FIRST) is ContentStatus.PENDING_APPROVAL
    assert initial_status() is ContentStatus.PENDING_APPROVAL


def test_luong_duyet_day_du():
    flow = [
        ContentStatus.DRAFT,
        ContentStatus.PENDING_APPROVAL,
        ContentStatus.APPROVED,
        ContentStatus.SCHEDULED,
        ContentStatus.PUBLISHING,
        ContentStatus.PUBLISHED,
    ]
    for current, target in zip(flow, flow[1:], strict=False):
        assert_transition(current, target)


def test_khong_the_dang_thang_khi_chua_duyet():
    assert not can_transition(ContentStatus.PENDING_APPROVAL, ContentStatus.PUBLISHING)
    assert not can_transition(ContentStatus.DRAFT, ContentStatus.PUBLISHED)


def test_published_la_trang_thai_cuoi():
    with pytest.raises(InvalidTransitionError):
        assert_transition(ContentStatus.PUBLISHED, ContentStatus.SCHEDULED)


def test_tu_choi_dua_bai_ve_draft():
    assert can_transition(ContentStatus.PENDING_APPROVAL, ContentStatus.DRAFT)


def test_het_luot_retry_thi_vao_dead_letter():
    assert next_after_failure(0) is ContentStatus.PUBLISHING
    assert next_after_failure(MAX_PUBLISH_RETRIES) is ContentStatus.DEAD_LETTER
