"""Test suite cho CRM Nudge Domain Policy."""

from datetime import UTC, datetime, timedelta

from core.enums import CrmNudgeType, Industry
from domain.policies.nudge_policy import generate_nudge_message, is_eligible_for_nudge


def test_generate_nudge_message_spa():
    msg = generate_nudge_message(
        lead_name="Mai",
        industry=Industry.SPA,
        nudge_type=CrmNudgeType.INACTIVE_30_DAYS,
        brand_name="Spa Havi",
        discount_percent=20,
    )
    assert "Mai" in msg
    assert "Spa Havi" in msg
    assert "1 tháng" in msg
    assert "20%" in msg


def test_generate_nudge_message_fnb_14_days():
    msg = generate_nudge_message(
        lead_name="Dũng",
        industry=Industry.FOOD_BEVERAGE,
        nudge_type=CrmNudgeType.FOLLOWUP_14_DAYS,
        brand_name="Quán Cà Phê Havi",
        discount_percent=15,
    )
    assert "Dũng" in msg
    assert "Quán Cà Phê Havi" in msg
    assert "2 tuần" in msg or "món mới" in msg


def test_is_eligible_for_nudge():
    now = datetime.now(UTC)

    # Lead tạo 10 ngày trước -> Không đủ điều kiện (chưa đủ 30 ngày)
    assert not is_eligible_for_nudge(
        lead_created_at=now - timedelta(days=10),
        last_nudged_at=None,
        now=now,
        min_days=30,
    )

    # Lead tạo 35 ngày trước, chưa từng nudge -> Đủ điều kiện
    assert is_eligible_for_nudge(
        lead_created_at=now - timedelta(days=35),
        last_nudged_at=None,
        now=now,
        min_days=30,
    )

    # Lead tạo 40 ngày trước, nhưng vừa được nudge 5 ngày trước -> Không đủ điều kiện (Anti-spam)
    assert not is_eligible_for_nudge(
        lead_created_at=now - timedelta(days=40),
        last_nudged_at=now - timedelta(days=5),
        now=now,
        min_days=30,
    )

    # Lead tạo 70 ngày trước, nudge lần cuối 35 ngày trước -> Đủ điều kiện
    assert is_eligible_for_nudge(
        lead_created_at=now - timedelta(days=70),
        last_nudged_at=now - timedelta(days=35),
        now=now,
        min_days=30,
    )
