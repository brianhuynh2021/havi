"""Transactional Outbox — điều nó bảo đảm và điều nó cố ý không bảo đảm."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.persistence.outbox_repository import MAX_ATTEMPTS, OutboxRepository
from application.services.job_queue import OutboxJobQueue
from application.services.outbox_dispatcher import OutboxDispatcher
from core.enums import OutboxStatus
from domain.models.outbox import OutboxEntry


class TestGhiCungTransaction:
    @pytest.mark.asyncio
    async def test_enqueue_khong_tu_commit(self, db_session: AsyncSession) -> None:
        """Đây là *toàn bộ* giá trị của Outbox.

        `enqueue` chỉ được `add` vào session đang mở. Nếu nó tự commit thì bản
        ghi outbox tồn tại độc lập với dữ liệu nghiệp vụ, và ta lại có đúng bài
        toán dual-write vừa đi vá.
        """
        queue = OutboxJobQueue(OutboxRepository(db_session))
        ws, job = uuid.uuid4(), uuid.uuid4()

        queue.enqueue_generate_drafts(workspace_id=ws, job_id=job, request_id="req_1")

        # Chưa flush: chưa có gì trong DB.
        assert len(db_session.new) == 1

        await db_session.flush()
        rows = (
            await db_session.execute(select(OutboxEntry).where(OutboxEntry.workspace_id == ws))
        ).scalars().all()
        assert len(rows) == 1
        assert rows[0].topic == "generate_drafts"
        assert rows[0].status == OutboxStatus.PENDING

    @pytest.mark.asyncio
    async def test_uuid_duoc_chuoi_hoa_cho_jsonb(self, db_session: AsyncSession) -> None:
        """`json.dumps` không xử lý được UUID; lỗi đó phải hiện ở đây, không phải
        trong worker nền xa chỗ gây ra."""
        queue = OutboxJobQueue(OutboxRepository(db_session))
        ws, job = uuid.uuid4(), uuid.uuid4()

        queue.enqueue_generate_drafts(workspace_id=ws, job_id=job)
        await db_session.flush()

        row = (
            await db_session.execute(select(OutboxEntry).where(OutboxEntry.workspace_id == ws))
        ).scalars().one()
        assert row.payload["job_id"] == str(job)
        assert isinstance(row.payload["workspace_id"], str)


class TestClaimBatch:
    @pytest.mark.asyncio
    async def test_chi_lay_dong_da_den_han(self, db_session: AsyncSession) -> None:
        repo = OutboxRepository(db_session)
        ready = OutboxEntry(
            topic="generate_drafts",
            payload={},
            status=OutboxStatus.PENDING,
            available_at=datetime.now(UTC) - timedelta(seconds=1),
        )
        later = OutboxEntry(
            topic="generate_drafts",
            payload={},
            status=OutboxStatus.PENDING,
            available_at=datetime.now(UTC) + timedelta(minutes=5),
        )
        db_session.add_all([ready, later])
        await db_session.flush()

        claimed = await repo.claim_batch()

        ids = {e.id for e in claimed}
        assert ready.id in ids
        assert later.id not in ids, "dòng đang chờ backoff không được lấy"

    @pytest.mark.asyncio
    async def test_bo_qua_dong_da_dispatched(self, db_session: AsyncSession) -> None:
        repo = OutboxRepository(db_session)
        done = OutboxEntry(
            topic="generate_drafts",
            payload={},
            status=OutboxStatus.DISPATCHED,
            available_at=datetime.now(UTC) - timedelta(seconds=1),
        )
        db_session.add(done)
        await db_session.flush()

        claimed = await repo.claim_batch()

        assert done.id not in {e.id for e in claimed}


class TestBackoffVaFailed:
    @pytest.mark.asyncio
    async def test_mark_retry_giãn_available_at(self, db_session: AsyncSession) -> None:
        repo = OutboxRepository(db_session)
        entry = OutboxEntry(
            topic="generate_drafts", payload={}, available_at=datetime.now(UTC)
        )
        db_session.add(entry)
        await db_session.flush()

        await repo.mark_retry(entry, error="redis down")

        assert entry.attempts == 1
        assert entry.status == OutboxStatus.PENDING
        assert entry.available_at > datetime.now(UTC)

    @pytest.mark.asyncio
    async def test_het_luot_thi_vao_failed(self, db_session: AsyncSession) -> None:
        repo = OutboxRepository(db_session)
        entry = OutboxEntry(
            topic="generate_drafts",
            payload={},
            available_at=datetime.now(UTC),
            attempts=MAX_ATTEMPTS - 1,
        )
        db_session.add(entry)
        await db_session.flush()

        await repo.mark_retry(entry, error="vẫn lỗi")

        assert entry.status == OutboxStatus.FAILED

    @pytest.mark.asyncio
    async def test_last_error_bi_cat_ngan(self, db_session: AsyncSession) -> None:
        """Traceback đầy đủ nhân vài nghìn dòng làm phình bảng vô ích."""
        repo = OutboxRepository(db_session)
        entry = OutboxEntry(
            topic="generate_drafts", payload={}, available_at=datetime.now(UTC)
        )
        db_session.add(entry)
        await db_session.flush()

        await repo.mark_retry(entry, error="x" * 5000)

        assert len(entry.last_error) == 500


class TestDispatcher:
    @pytest.mark.asyncio
    async def test_topic_ngoai_allow_list_khong_duoc_goi(
        self, db_session: AsyncSession
    ) -> None:
        """`topic` đi từ DB. Không có allow-list thì nó thành đường gọi hàm tuỳ ý
        trong process worker."""
        repo = OutboxRepository(db_session)
        entry = OutboxEntry(
            topic="os.system", payload={}, available_at=datetime.now(UTC)
        )
        db_session.add(entry)
        await db_session.flush()

        result = await OutboxDispatcher(repo).run_once()

        assert result["dispatched"] == 0
        assert result["failed"] == 1
        # Lỗi vĩnh viễn → vào `failed` ngay, không thử lại 8 lần vô ích.
        assert entry.status == OutboxStatus.FAILED

    @pytest.mark.asyncio
    async def test_redis_loi_thi_giu_lai_de_thu_lai(
        self, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Redis chết không được làm mất việc — đó là cả lý do Outbox tồn tại."""
        import application.services.outbox_dispatcher as module

        def _boom(topic: str, payload: dict) -> None:
            raise ConnectionError("redis unreachable")

        monkeypatch.setattr(module, "_send_to_celery", _boom)

        repo = OutboxRepository(db_session)
        entry = OutboxEntry(
            topic="generate_drafts", payload={}, available_at=datetime.now(UTC)
        )
        db_session.add(entry)
        await db_session.flush()

        result = await module.OutboxDispatcher(repo).run_once()

        assert result["failed"] == 1
        assert entry.status == OutboxStatus.PENDING, "việc phải còn đó để thử lại"
        assert entry.attempts == 1

    @pytest.mark.asyncio
    async def test_thanh_cong_thi_danh_dau_dispatched(
        self, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import application.services.outbox_dispatcher as module

        sent: list[tuple[str, dict]] = []
        monkeypatch.setattr(
            module, "_send_to_celery", lambda topic, payload: sent.append((topic, payload))
        )

        repo = OutboxRepository(db_session)
        entry = OutboxEntry(
            topic="generate_drafts",
            payload={"job_id": "abc"},
            available_at=datetime.now(UTC),
        )
        db_session.add(entry)
        await db_session.flush()

        result = await module.OutboxDispatcher(repo).run_once()

        assert result["dispatched"] == 1
        assert entry.status == OutboxStatus.DISPATCHED
        assert entry.dispatched_at is not None
        assert sent == [("generate_drafts", {"job_id": "abc"})]

    @pytest.mark.asyncio
    async def test_mot_dong_loi_khong_chan_dong_khac(
        self, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import application.services.outbox_dispatcher as module

        def _selective(topic: str, payload: dict) -> None:
            if payload.get("bad"):
                raise ConnectionError("nope")

        monkeypatch.setattr(module, "_send_to_celery", _selective)

        repo = OutboxRepository(db_session)
        bad = OutboxEntry(
            topic="generate_drafts", payload={"bad": True}, available_at=datetime.now(UTC)
        )
        good = OutboxEntry(
            topic="generate_drafts", payload={"bad": False}, available_at=datetime.now(UTC)
        )
        db_session.add_all([bad, good])
        await db_session.flush()

        result = await module.OutboxDispatcher(repo).run_once()

        assert result["dispatched"] == 1
        assert result["failed"] == 1
        assert good.status == OutboxStatus.DISPATCHED


class TestVanHanh:
    @pytest.mark.asyncio
    async def test_requeue_failed_dua_ve_pending(self, db_session: AsyncSession) -> None:
        repo = OutboxRepository(db_session)
        entry = OutboxEntry(
            topic="generate_drafts",
            payload={},
            status=OutboxStatus.FAILED,
            attempts=MAX_ATTEMPTS,
            last_error="cũ",
        )
        db_session.add(entry)
        await db_session.flush()

        count = await repo.requeue_failed()
        await db_session.refresh(entry)

        assert count == 1
        assert entry.status == OutboxStatus.PENDING
        assert entry.attempts == 0
        assert entry.last_error is None

    @pytest.mark.asyncio
    async def test_purge_chi_don_dong_da_dispatched(self, db_session: AsyncSession) -> None:
        """Không được dọn dòng còn `pending` — đó là mất việc."""
        repo = OutboxRepository(db_session)
        old_done = OutboxEntry(
            topic="generate_drafts",
            payload={},
            status=OutboxStatus.DISPATCHED,
            dispatched_at=datetime.now(UTC) - timedelta(days=30),
        )
        old_pending = OutboxEntry(
            topic="generate_drafts",
            payload={},
            status=OutboxStatus.PENDING,
            available_at=datetime.now(UTC) - timedelta(days=30),
        )
        db_session.add_all([old_done, old_pending])
        await db_session.flush()

        purged = await repo.purge_dispatched_before(cutoff=datetime.now(UTC) - timedelta(days=7))

        assert purged == 1
        still_there = (
            await db_session.execute(select(OutboxEntry).where(OutboxEntry.id == old_pending.id))
        ).scalars().all()
        assert len(still_there) == 1
