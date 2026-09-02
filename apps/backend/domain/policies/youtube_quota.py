"""Quản lý hạn mức YouTube Data API v3 (Shared Quota).

Theo COMMERCIAL_READINESS_PROMPT §3.3:
- YouTube Data API v3 cấp hạn mức theo ngày (mặc định 10.000 units/ngày).
- Hạn mức được reset vào 00:00:00 giờ Pacific (America/Los_Angeles).
- Mỗi lần gọi `videos.insert` tiêu tốn ~1.600 units.
- Đếm unit đã dùng trong Redis với khoá theo ngày giờ Pacific (`youtube_quota:YYYY-MM-DD`).
- Khi còn dưới 1.600 units: job chờ sang ngày (reschedule về 00:00 giờ Pacific kế tiếp),
  hiện lý do "hết hạn mức YouTube hôm nay", không fail vĩnh viễn.
- Cảnh báo qua alert khi đã dùng >= 80% (8.000 units).
"""

from datetime import UTC, date, datetime, time, timedelta
import logging
from zoneinfo import ZoneInfo

from core.alerts import Alert, get_alert_sink

logger = logging.getLogger(__name__)

PACIFIC_TZ = ZoneInfo("America/Los_Angeles")
DEFAULT_DAILY_QUOTA_UNITS = 10000
VIDEO_INSERT_COST_UNITS = 1600
QUOTA_WARNING_THRESHOLD_RATIO = 0.80  # 80%


def get_pacific_now(now_utc: datetime | None = None) -> datetime:
    """Thời điểm hiện tại theo múi giờ Pacific (America/Los_Angeles)."""
    if now_utc is None:
        now_utc = datetime.now(UTC)
    elif now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=UTC)
    return now_utc.astimezone(PACIFIC_TZ)


def get_pacific_date(now_utc: datetime | None = None) -> date:
    """Ngày hiện tại theo lịch Pacific."""
    return get_pacific_now(now_utc).date()


def get_next_pacific_midnight_utc(now_utc: datetime | None = None) -> datetime:
    """Mốc 00:00:00 ngày hôm sau theo giờ Pacific, đổi về UTC."""
    pac_now = get_pacific_now(now_utc)
    next_day = pac_now.date() + timedelta(days=1)
    next_midnight_pac = datetime.combine(next_day, time(0, 0, 0), tzinfo=PACIFIC_TZ)
    return next_midnight_pac.astimezone(UTC)


def _redis_quota_key(pac_date: date) -> str:
    return f"youtube_quota:{pac_date.isoformat()}"


async def get_used_quota(
    redis_client,
    *,
    now_utc: datetime | None = None,
) -> int:
    """Đọc số unit YouTube đã sử dụng trong ngày Pacific hiện tại."""
    if redis_client is None:
        return 0
    pac_date = get_pacific_date(now_utc)
    key = _redis_quota_key(pac_date)
    try:
        val = await redis_client.get(key)
        return int(val) if val else 0
    except Exception as exc:
        logger.warning("Không thể đọc YouTube quota từ Redis: %s", exc)
        return 0


async def record_quota_consumption(
    redis_client,
    *,
    units: int = VIDEO_INSERT_COST_UNITS,
    daily_limit: int = DEFAULT_DAILY_QUOTA_UNITS,
    now_utc: datetime | None = None,
) -> int:
    """Ghi nhận số unit đã tiêu tốn vào Redis và phát alert nếu vượt 80%."""
    if redis_client is None:
        return units
    pac_date = get_pacific_date(now_utc)
    key = _redis_quota_key(pac_date)
    try:
        new_val = await redis_client.incrby(key, units)
        # Đặt TTL 48 giờ để tự động dọn dẹp
        await redis_client.expire(key, 172800)

        # Kiểm tra ngưỡng cảnh báo 80%
        if new_val >= int(daily_limit * QUOTA_WARNING_THRESHOLD_RATIO):
            alerts = get_alert_sink()
            await alerts.send(
                Alert(
                    type="youtube.quota_warning",
                    severity="warning",
                    summary=(
                        f"Hạn mức YouTube Data API ngày {pac_date} đã dùng "
                        f"{new_val}/{daily_limit} units ({new_val * 100 // daily_limit}% >= 80%)"
                    ),
                    fields={
                        "used_units": new_val,
                        "daily_limit": daily_limit,
                        "pacific_date": str(pac_date),
                    },
                )
            )
        return int(new_val)
    except Exception as exc:
        logger.warning("Không thể ghi nhận YouTube quota vào Redis: %s", exc)
        return units


async def check_quota_available(
    redis_client,
    *,
    needed_units: int = VIDEO_INSERT_COST_UNITS,
    daily_limit: int = DEFAULT_DAILY_QUOTA_UNITS,
    now_utc: datetime | None = None,
) -> tuple[bool, int, datetime]:
    """Kiểm tra xem còn đủ quota cho lần đăng YouTube tiếp theo không.

    Trả về: `(is_available, used_units, next_reset_at_utc)`
    """
    used = await get_used_quota(redis_client, now_utc=now_utc)
    next_reset = get_next_pacific_midnight_utc(now_utc)
    is_available = (used + needed_units) <= daily_limit
    return is_available, used, next_reset
