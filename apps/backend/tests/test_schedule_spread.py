"""Duyệt cả loạt phải rải ra nhiều ngày, không dồn vào một phút.

Đây là use case thật: chủ tiệm ngồi một buổi tối viết nội dung cho cả tuần, rồi
bấm duyệt hết. Nếu sáu bài cùng đăng lúc 20:00 thứ Ba thì Trang trông như bị
spam, và sáu ngày sau đó im lặng — ngược hẳn thứ họ muốn là *mỗi ngày một câu
chuyện*.

Bug này không làm request đỏ và không làm test cũ đỏ: `approve_many` gọi
`next_golden_hour()` cho từng bài, và hàm đó trả cùng một mốc cho mọi lời gọi
trong cùng một giây. Nó chỉ lộ ra khi nhìn Trang thật.
"""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.persistence.content_repository import ContentRepository
from adapters.persistence.event_log_repository import EventLogRepository
from adapters.persistence.user_repository import UserRepository
from adapters.persistence.workspace_repository import WorkspaceRepository
from application.services.approval_service import ApprovalService
from core.enums import Channel, ContentStatus, Industry
from domain.policies.scheduling import (
    GOLDEN_HOURS,
    VIETNAM_TZ,
    spread_over_golden_hours,
)

pytestmark = pytest.mark.anyio

# 14:00 giờ VN — đã qua khung 8h và 12h, còn khung 20h trong ngày.
AFTERNOON = datetime(2026, 8, 25, 14, 0, tzinfo=VIETNAM_TZ)


class TestRaiLich:
    """`spread_over_golden_hours` — policy thuần, không chạm DB."""

    def test_moi_ngay_mot_bai_thi_moi_bai_mot_ngay_khac_nhau(self):
        slots = spread_over_golden_hours(5, per_day=1, now=AFTERNOON)
        days = [slot.astimezone(VIETNAM_TZ).date() for slot in slots]
        assert len(set(days)) == 5, "năm bài phải rơi vào năm ngày khác nhau"

    def test_khong_bai_nao_trung_gio_voi_bai_nao(self):
        slots = spread_over_golden_hours(9, per_day=3, now=AFTERNOON)
        assert len(set(slots)) == 9

    def test_thu_tu_tang_dan_dung_thu_tu_bai_truyen_vao(self):
        """Bài đầu danh sách lên trước — đó là cách chủ tiệm xếp câu chuyện."""
        slots = spread_over_golden_hours(6, per_day=2, now=AFTERNOON)
        assert slots == sorted(slots)

    def test_khong_bao_gio_dat_lich_vao_qua_khu(self):
        """Lịch quá khứ = scheduler đăng dồn tất cả ngay lượt quét kế tiếp."""
        slots = spread_over_golden_hours(4, per_day=3, now=AFTERNOON)
        assert all(slot > AFTERNOON for slot in slots)

    def test_ngay_dau_bo_qua_khung_da_troi_qua(self):
        """14h chiều thì khung 8h và 12h hôm nay không dùng được nữa."""
        slots = spread_over_golden_hours(1, per_day=3, now=AFTERNOON)
        first = slots[0].astimezone(VIETNAM_TZ)
        assert first.date() == AFTERNOON.date()
        assert first.hour == 20

    def test_gio_som_thi_dung_duoc_ca_ba_khung_trong_ngay(self):
        morning = AFTERNOON.replace(hour=6, minute=0)
        slots = spread_over_golden_hours(3, per_day=3, now=morning)
        hours = [slot.astimezone(VIETNAM_TZ).hour for slot in slots]
        assert hours == [slot.hour for slot in GOLDEN_HOURS]

    def test_per_day_vuot_so_khung_gio_van_khong_tao_lich_trung(self):
        """Chỉ có 3 khung vàng — xin 10 bài/ngày cũng không đẻ thêm khung."""
        slots = spread_over_golden_hours(12, per_day=10, now=AFTERNOON)
        assert len(set(slots)) == 12
        per_day_counts: dict[object, int] = {}
        for slot in slots:
            day = slot.astimezone(VIETNAM_TZ).date()
            per_day_counts[day] = per_day_counts.get(day, 0) + 1
        assert max(per_day_counts.values()) <= len(GOLDEN_HOURS)

    def test_khong_co_bai_nao_thi_khong_co_lich_nao(self):
        assert spread_over_golden_hours(0) == []


async def _workspace_with_drafts(db_session: AsyncSession, count: int):
    user = await UserRepository(db_session).create(
        email=f"spread_{uuid4().hex[:6]}@havi.vn", name="Chủ Tiệm", password_hash="h"
    )
    ws = await WorkspaceRepository(db_session).create(
        name="Tiệm Rải Lịch", industry=Industry.SPA, owner_user_id=user.id
    )
    content = ContentRepository(db_session)
    job, _ = await content.create_job(
        workspace_id=ws.id, raw_inputs=[], idempotency_key=uuid4().hex
    )
    items = []
    for index in range(count):
        item = await content.create_item(
            job_id=job.id,
            workspace_id=ws.id,
            channel=Channel.FACEBOOK_PAGE,
            kind="post",
            text=f"Câu chuyện ngày {index + 1}",
            media_note=None,
            status=ContentStatus.PENDING_APPROVAL,
        )
        items.append(item)
    await db_session.flush()
    return ws, user, items


def _service(db_session: AsyncSession) -> ApprovalService:
    return ApprovalService(
        content=ContentRepository(db_session), events=EventLogRepository(db_session)
    )


async def test_duyet_sau_bai_mot_luot_thi_ra_sau_ngay_khac_nhau(db_session: AsyncSession):
    """Bug gốc: sáu bài cùng đăng một phút rồi im lặng sáu ngày."""
    ws, user, items = await _workspace_with_drafts(db_session, 6)

    outcome = await _service(db_session).approve_many(
        workspace_id=ws.id,
        item_ids=[item.id for item in items],
        user_id=user.id,
        publish_now=False,
        posts_per_day=1,
    )

    assert len(outcome.approved) == 6
    scheduled = [item.scheduled_at for item in items]
    assert len(set(scheduled)) == 6, "sáu bài phải có sáu mốc giờ khác nhau"
    days = {stamp.astimezone(VIETNAM_TZ).date() for stamp in scheduled}
    assert len(days) == 6, "mỗi ngày đúng một câu chuyện"


async def test_hai_bai_mot_ngay_thi_gap_doi_mat_do(db_session: AsyncSession):
    ws, user, items = await _workspace_with_drafts(db_session, 6)

    await _service(db_session).approve_many(
        workspace_id=ws.id,
        item_ids=[item.id for item in items],
        user_id=user.id,
        publish_now=False,
        posts_per_day=2,
    )

    days = {item.scheduled_at.astimezone(VIETNAM_TZ).date() for item in items}
    assert len(days) == 3


async def test_dang_ngay_thi_khong_rai_lich(db_session: AsyncSession):
    """`publish_now=True` giữ nguyên hành vi cũ: tất cả đi luôn."""
    ws, user, items = await _workspace_with_drafts(db_session, 3)

    await _service(db_session).approve_many(
        workspace_id=ws.id,
        item_ids=[item.id for item in items],
        user_id=user.id,
        publish_now=True,
    )

    now = datetime.now(VIETNAM_TZ)
    for item in items:
        assert item.scheduled_at <= now + timedelta(seconds=5)


async def test_thu_tu_bai_giu_nguyen_theo_danh_sach_truyen_vao(db_session: AsyncSession):
    """Chủ tiệm sắp thứ tự câu chuyện; tầng duyệt không được xáo lại."""
    ws, user, items = await _workspace_with_drafts(db_session, 4)
    ordered_ids = [item.id for item in items]

    await _service(db_session).approve_many(
        workspace_id=ws.id, item_ids=ordered_ids, user_id=user.id, publish_now=False
    )

    by_id = {item.id: item.scheduled_at for item in items}
    stamps = [by_id[item_id] for item_id in ordered_ids]
    assert stamps == sorted(stamps)


async def test_mot_bai_hong_khong_lam_thung_mot_ngay_trong_lich(db_session: AsyncSession):
    """Khung giờ cấp theo số bài duyệt thành công, không theo chỉ số vòng lặp."""
    ws, user, items = await _workspace_with_drafts(db_session, 3)
    ghost = uuid4()  # id không tồn tại → thất bại ở giữa danh sách

    outcome = await _service(db_session).approve_many(
        workspace_id=ws.id,
        item_ids=[items[0].id, ghost, items[1].id, items[2].id],
        user_id=user.id,
        publish_now=False,
        posts_per_day=1,
    )

    assert len(outcome.approved) == 3
    assert len(outcome.failures) == 1

    days = sorted(item.scheduled_at.astimezone(VIETNAM_TZ).date() for item in items)
    # Ba ngày liên tiếp, không có ngày nào bị bỏ trống.
    assert (days[1] - days[0]).days == 1
    assert (days[2] - days[1]).days == 1
