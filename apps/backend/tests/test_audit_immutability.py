"""`event_log` bất biến + hash chain — kiểm ở tầng Postgres thật.

Những test này chạy trên Postgres thật (như cả suite), và đó là điều kiện bắt
buộc: cái đang kiểm là **trigger của database**, không phải logic Python. Chạy
trên SQLite thì mọi test dưới đây xanh mà không chứng minh gì.
"""

import uuid

import pytest
from sqlalchemy import delete, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.persistence.event_log_repository import EventLogRepository
from core.events import EventLogEntry
from domain.models.audit import EventLog


async def _record(session: AsyncSession, workspace_id: uuid.UUID, **kw) -> EventLog:
    return await EventLogRepository(session).record(
        EventLogEntry(
            workspace_id=workspace_id,
            job_kind=kw.pop("job_kind", "test.event"),
            input_summary=kw.pop("input_summary", "in"),
            output_summary=kw.pop("output_summary", "out"),
            **kw,
        )
    )


@pytest.mark.asyncio
async def test_update_bi_chan(db_session: AsyncSession) -> None:
    ws = uuid.uuid4()
    row = await _record(db_session, ws)
    await db_session.flush()

    with pytest.raises(IntegrityError, match="append-only"):
        await db_session.execute(
            update(EventLog).where(EventLog.id == row.id).values(input_summary="hacked")
        )


@pytest.mark.asyncio
async def test_delete_bi_chan(db_session: AsyncSession) -> None:
    ws = uuid.uuid4()
    row = await _record(db_session, ws)
    await db_session.flush()

    with pytest.raises(IntegrityError, match="append-only"):
        await db_session.execute(delete(EventLog).where(EventLog.id == row.id))


@pytest.mark.asyncio
async def test_hash_chain_noi_dung_dong_lien_tiep(db_session: AsyncSession) -> None:
    """`prev_hash` của dòng sau phải bằng `row_hash` của dòng trước."""
    ws = uuid.uuid4()
    first = await _record(db_session, ws, job_kind="test.first")
    await db_session.flush()
    second = await _record(db_session, ws, job_kind="test.second")
    await db_session.flush()

    await db_session.refresh(first)
    await db_session.refresh(second)

    assert first.row_hash is not None
    assert first.prev_hash is None, "dòng đầu của workspace không có gì trước nó"
    assert second.prev_hash == first.row_hash


@pytest.mark.asyncio
async def test_moi_workspace_mot_chuoi_rieng(db_session: AsyncSession) -> None:
    """Chuỗi tách theo tenant — chuỗi toàn cục sẽ serialize ghi log của mọi khách."""
    ws_a, ws_b = uuid.uuid4(), uuid.uuid4()
    a1 = await _record(db_session, ws_a)
    await db_session.flush()
    b1 = await _record(db_session, ws_b)
    await db_session.flush()

    await db_session.refresh(b1)
    assert b1.prev_hash is None, "dòng đầu của workspace B không được nối vào A"
    assert b1.row_hash != a1.row_hash


@pytest.mark.asyncio
async def test_verify_chain_bao_ok_khi_nguyen_ven(db_session: AsyncSession) -> None:
    ws = uuid.uuid4()
    for i in range(3):
        await _record(db_session, ws, job_kind=f"test.{i}")
    await db_session.flush()

    report = await EventLogRepository(db_session).verify_chain(workspace_id=ws)

    assert report["ok"] is True
    assert report["rows_checked"] == 3
    assert report["broken_at"] is None


@pytest.mark.asyncio
async def test_verify_chain_phat_hien_sua_du_lieu_khi_trigger_bi_tat(
    db_session: AsyncSession,
) -> None:
    """Đây là lý do hash chain tồn tại.

    Trigger chặn được người dùng bình thường, nhưng ai có quyền cao thì tắt được
    nó. Test này mô phỏng đúng kẻ tấn công đó: tắt trigger, sửa một dòng, rồi
    chứng minh việc sửa vẫn *để lại dấu* — `row_hash` lưu trong bảng không còn
    khớp với hash tính lại từ nội dung.
    """
    ws = uuid.uuid4()
    rows = [await _record(db_session, ws, job_kind=f"test.{i}") for i in range(3)]
    await db_session.flush()
    target = rows[1]

    await db_session.execute(text("ALTER TABLE event_log DISABLE TRIGGER event_log_block_update"))
    try:
        await db_session.execute(
            update(EventLog).where(EventLog.id == target.id).values(tokens_in=999_999)
        )
    finally:
        await db_session.execute(
            text("ALTER TABLE event_log ENABLE TRIGGER event_log_block_update")
        )

    report = await EventLogRepository(db_session).verify_chain(workspace_id=ws)

    assert report["ok"] is False
    assert report["broken_at"]["id"] == str(target.id)


@pytest.mark.asyncio
async def test_an_danh_hoa_theo_quyen_duoc_xoa_van_duoc_phep(
    db_session: AsyncSession,
) -> None:
    """Ngoại lệ hợp lệ: xoá dữ liệu theo GDPR. Xem migration b4c5d6e7f8a9."""
    ws = uuid.uuid4()
    await _record(db_session, ws, input_summary="tên khách", output_summary="bài viết")
    await db_session.flush()

    await db_session.execute(text("SET LOCAL havi.erasure = 'on'"))
    await db_session.execute(
        update(EventLog)
        .where(EventLog.workspace_id == ws)
        .values(workspace_id=None, input_summary="[redacted]", output_summary="[redacted]")
    )
    await db_session.flush()

    remaining = (
        await db_session.execute(select(EventLog).where(EventLog.workspace_id == ws))
    ).scalars().all()
    assert remaining == []


@pytest.mark.asyncio
async def test_co_erasure_khong_cho_sua_so_lieu_ke_toan(db_session: AsyncSession) -> None:
    """Cửa ngoại lệ chỉ mở đúng một hình dạng UPDATE.

    Nếu nó cho sửa `tokens_in` thì "chống gian lận kế toán" mất nghĩa: ai muốn
    sửa số liệu chỉ cần bật cờ erasure lên.
    """
    ws = uuid.uuid4()
    row = await _record(db_session, ws, tokens_in=100)
    await db_session.flush()

    await db_session.execute(text("SET LOCAL havi.erasure = 'on'"))
    with pytest.raises(IntegrityError, match="append-only"):
        await db_session.execute(
            update(EventLog)
            .where(EventLog.id == row.id)
            .values(
                workspace_id=None,
                input_summary="[redacted]",
                output_summary="[redacted]",
                tokens_in=0,
            )
        )


@pytest.mark.asyncio
async def test_khong_co_co_erasure_thi_van_bi_chan(db_session: AsyncSession) -> None:
    """Một UPDATE 'đúng hình dạng' nhưng không khai ý định vẫn phải bị chặn —
    nếu không thì mọi bug ghi `[redacted]` đều lặng lẽ xoá được lịch sử."""
    ws = uuid.uuid4()
    row = await _record(db_session, ws)
    await db_session.flush()

    with pytest.raises(IntegrityError, match="append-only"):
        await db_session.execute(
            update(EventLog)
            .where(EventLog.id == row.id)
            .values(
                workspace_id=None,
                input_summary="[redacted]",
                output_summary="[redacted]",
            )
        )
