"""Unit tests for YouTube Quota tracking in Pacific Time."""

from datetime import UTC, datetime

import pytest

from core.alerts import Alert, AlertSink
from domain.policies.youtube_quota import (
    check_quota_available,
    get_next_pacific_midnight_utc,
    get_pacific_date,
    get_pacific_now,
    record_quota_consumption,
)


class MockRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def incrby(self, key: str, amount: int) -> int:
        val = int(self.store.get(key, "0")) + amount
        self.store[key] = str(val)
        return val

    async def expire(self, key: str, seconds: int) -> bool:
        return True


@pytest.mark.asyncio
async def test_pacific_time_and_reset_calculation():
    """Giờ Pacific được tính đúng và mốc reset là 00:00:00 ngày hôm sau theo giờ Pacific."""
    # 2026-09-02 10:00:00 UTC = 2026-09-02 03:00:00 PDT (Pacific Daylight Time, UTC-7)
    dt_utc = datetime(2026, 9, 2, 10, 0, 0, tzinfo=UTC)
    pac_dt = get_pacific_now(dt_utc)
    assert pac_dt.hour == 3
    assert get_pacific_date(dt_utc).isoformat() == "2026-09-02"

    # Reset là 2026-09-03 00:00:00 PDT = 2026-09-03 07:00:00 UTC
    next_reset = get_next_pacific_midnight_utc(dt_utc)
    assert next_reset == datetime(2026, 9, 3, 7, 0, 0, tzinfo=UTC)


@pytest.mark.asyncio
async def test_record_quota_and_warning_alert(monkeypatch):
    """Ghi nhận quota tiêu tốn và bắn alert khi chạm ngưỡng >= 80% (8000 units)."""
    redis = MockRedis()
    sent_alerts = []

    class MockAlertSink(AlertSink):
        async def send(self, alert: Alert) -> bool:
            sent_alerts.append(alert)
            return True

    monkeypatch.setattr("domain.policies.youtube_quota.get_alert_sink", lambda: MockAlertSink())

    now = datetime(2026, 9, 2, 12, 0, 0, tzinfo=UTC)

    # Lần 1: 1600 units (16%)
    used = await record_quota_consumption(redis, units=1600, now_utc=now)
    assert used == 1600
    assert len(sent_alerts) == 0

    # Lần 2: thêm 6400 units -> tổng 8000 units (80%) -> Bắn alert cảnh báo
    used = await record_quota_consumption(redis, units=6400, now_utc=now)
    assert used == 8000
    assert len(sent_alerts) == 1
    assert sent_alerts[0].type == "youtube.quota_warning"
    assert "80%" in sent_alerts[0].summary


@pytest.mark.asyncio
async def test_check_quota_available_defers_when_exhausted():
    """Khi quota còn lại không đủ 1600 units, check_quota_available trả is_available=False."""
    redis = MockRedis()
    now = datetime(2026, 9, 2, 12, 0, 0, tzinfo=UTC)

    # Đã dùng 8800 units, còn 1200 units (< 1600 units)
    await record_quota_consumption(redis, units=8800, now_utc=now)

    is_avail, used, next_reset = await check_quota_available(redis, needed_units=1600, now_utc=now)
    assert not is_avail
    assert used == 8800
    assert next_reset == datetime(2026, 9, 3, 7, 0, 0, tzinfo=UTC)
