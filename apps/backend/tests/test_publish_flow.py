"""Publish job: chống đăng trùng, phân loại lỗi, retry backoff, dead-letter.

Chạy thật trên Postgres — phần quan trọng nhất ở đây (unique constraint,
`FOR UPDATE SKIP LOCKED`) là hành vi của database, không phải của Python, nên
mock đi thì test mất hết ý nghĩa.

Đăng trùng lên Fanpage của khách là lỗi không sửa được — bài đã lên tường người
ta rồi. Vì vậy nhóm test đầu tiên là nhóm quan trọng nhất của cả file.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.persistence.event_log_repository import EventLogRepository
from adapters.persistence.publish_repository import (
    MAX_ATTEMPTS,
    PublishRepository,
    build_idempotency_key,
)
from adapters.publishers.fake import FakePublisher, auth_error, validation_error
from core.alerts import Alert, AlertSink
from core.enums import Channel, ConnectionStatus, Platform, PublishFailureKind, PublishStatus
from domain.models.audit import EventLog
from domain.models.workspace import Workspace
from domain.ports.publisher import PublishRequest, TemporaryPublishError

pytestmark = pytest.mark.anyio


class RecordingAlerts(AlertSink):
    def __init__(self) -> None:
        self.sent: list[Alert] = []

    async def send(self, alert: Alert) -> None:
        self.sent.append(alert)


async def _workspace(session: AsyncSession) -> Workspace:
    from core.enums import Industry
    from domain.models.user import User

    owner = User(email=f"{uuid.uuid4().hex[:10]}@spa.vn", name="Chị Hương")
    session.add(owner)
    await session.flush()

    ws = Workspace(name="Spa An Nhiên", industry=Industry.SPA, owner_user_id=owner.id)
    session.add(ws)
    await session.flush()
    return ws


async def _item(session: AsyncSession, workspace_id: uuid.UUID) -> uuid.UUID:
    """Content item thật — publish_jobs có FK nên không dùng UUID bịa được."""
    from core.enums import ContentStatus
    from domain.models.content import ContentItem

    item = ContentItem(
        workspace_id=workspace_id,
        job_id=None,
        channel=Channel.FACEBOOK_PAGE,
        kind="Bài ảnh",
        text="Ưu đãi gội đầu thảo dược",
        # DRAFT chứ không SCHEDULED: helper này chỉ để thoả FK cho test
        # repository, không được lọt vào lượt quét của scheduler.
        status=ContentStatus.DRAFT,
    )
    session.add(item)
    await session.flush()
    return item.id


def _at(hour: int = 20) -> datetime:
    return datetime(2026, 8, 10, hour, 0, tzinfo=UTC)


class TestIdempotencyKey:
    def test_cung_bai_cung_kenh_cung_gio_ra_cung_khoa(self):
        item = uuid.uuid4()
        args = {"content_item_id": item, "channel": Channel.FACEBOOK_PAGE, "scheduled_at": _at()}
        assert build_idempotency_key(**args) == build_idempotency_key(**args)

    def test_doi_gio_dang_ra_khoa_moi(self):
        """Đổi lịch là một lần đăng khác — cố ý ra key mới."""
        item = uuid.uuid4()
        a = build_idempotency_key(
            content_item_id=item, channel=Channel.FACEBOOK_PAGE, scheduled_at=_at(20)
        )
        b = build_idempotency_key(
            content_item_id=item, channel=Channel.FACEBOOK_PAGE, scheduled_at=_at(21)
        )
        assert a != b

    def test_hai_kenh_khac_nhau_ra_khoa_khac_nhau(self):
        """Cùng bài đăng lên Facebook và Zalo là hai job, không phải một."""
        item = uuid.uuid4()
        fb = build_idempotency_key(
            content_item_id=item, channel=Channel.FACEBOOK_PAGE, scheduled_at=_at()
        )
        zalo = build_idempotency_key(
            content_item_id=item, channel=Channel.ZALO_OA, scheduled_at=_at()
        )
        assert fb != zalo

    def test_cung_moc_thoi_gian_khac_offset_ra_cung_khoa(self):
        """20:00 giờ VN và 13:00 UTC là cùng một lúc — phải ra cùng khoá.

        Không chuẩn hoá thì reschedule về đúng giờ cũ lại sinh key mới, và bài
        được đăng hai lần.
        """
        from zoneinfo import ZoneInfo

        item = uuid.uuid4()
        vn = datetime(2026, 8, 10, 20, 0, tzinfo=ZoneInfo("Asia/Ho_Chi_Minh"))
        utc = vn.astimezone(UTC)
        a = build_idempotency_key(
            content_item_id=item, channel=Channel.FACEBOOK_PAGE, scheduled_at=vn
        )
        b = build_idempotency_key(
            content_item_id=item, channel=Channel.FACEBOOK_PAGE, scheduled_at=utc
        )
        assert a == b


class TestChongDangTrung:
    async def test_enqueue_hai_lan_chi_ra_mot_job(self, db_session: AsyncSession):
        ws = await _workspace(db_session)
        repo = PublishRepository(db_session)
        args = {
            "workspace_id": ws.id,
            "content_item_id": await _item(db_session, ws.id),
            "channel": Channel.FACEBOOK_PAGE,
            "scheduled_at": _at(),
        }

        first, created_1 = await repo.enqueue(**args)
        second, created_2 = await repo.enqueue(**args)

        assert created_1 is True
        assert created_2 is False, "lần thứ hai không được tạo job mới"
        assert first.id == second.id

    async def test_unique_constraint_chan_o_tang_postgres(self, db_session: AsyncSession):
        """Chốt chặn thật nằm ở database, không phải ở check trước insert.

        Hai worker cùng quét một bài đến hạn đều thấy "chưa có job" rồi cùng
        insert — chỉ constraint mới chặn được vì nó không phụ thuộc thứ tự chạy.
        """
        from sqlalchemy.exc import IntegrityError

        from domain.models.publish import PublishJob

        ws = await _workspace(db_session)
        item = await _item(db_session, ws.id)
        key = build_idempotency_key(
            content_item_id=item, channel=Channel.FACEBOOK_PAGE, scheduled_at=_at()
        )
        for _ in range(2):
            db_session.add(
                PublishJob(
                    workspace_id=ws.id,
                    content_item_id=item,
                    channel=Channel.FACEBOOK_PAGE,
                    idempotency_key=key,
                    scheduled_at=_at(),
                )
            )

        with pytest.raises(IntegrityError) as exc:
            await db_session.flush()
        # Phải là unique constraint, không phải FK — nếu không thì test này
        # đang kiểm nhầm thứ và chốt chặn chống trùng chưa được verify.
        assert "uq_publish_jobs_idempotency_key" in str(exc.value)
        await db_session.rollback()

    async def test_doi_lich_thi_tao_job_moi(self, db_session: AsyncSession):
        ws = await _workspace(db_session)
        repo = PublishRepository(db_session)
        item = await _item(db_session, ws.id)

        _, created_1 = await repo.enqueue(
            workspace_id=ws.id,
            content_item_id=item,
            channel=Channel.FACEBOOK_PAGE,
            scheduled_at=_at(20),
        )
        _, created_2 = await repo.enqueue(
            workspace_id=ws.id,
            content_item_id=item,
            channel=Channel.FACEBOOK_PAGE,
            scheduled_at=_at(21),
        )

        assert created_1 is True
        assert created_2 is True


class TestClaimDue:
    async def test_chi_lay_job_da_den_han(self, db_session: AsyncSession):
        ws = await _workspace(db_session)
        repo = PublishRepository(db_session)
        await repo.enqueue(
            workspace_id=ws.id,
            content_item_id=await _item(db_session, ws.id),
            channel=Channel.FACEBOOK_PAGE,
            scheduled_at=_at(20),
        )
        await repo.enqueue(
            workspace_id=ws.id,
            content_item_id=await _item(db_session, ws.id),
            channel=Channel.FACEBOOK_PAGE,
            scheduled_at=_at(23),
        )

        claimed = await repo.claim_due(now=_at(21))

        assert len(claimed) == 1
        assert claimed[0].scheduled_at.replace(tzinfo=UTC) == _at(20)

    async def test_job_da_claim_chuyen_sang_in_flight(self, db_session: AsyncSession):
        """Sau khi nhận, worker khác phải thấy nó không còn ở `pending`."""
        ws = await _workspace(db_session)
        repo = PublishRepository(db_session)
        await repo.enqueue(
            workspace_id=ws.id,
            content_item_id=await _item(db_session, ws.id),
            channel=Channel.FACEBOOK_PAGE,
            scheduled_at=_at(),
        )

        claimed = await repo.claim_due(now=_at(21))
        assert claimed[0].status is PublishStatus.IN_FLIGHT
        assert claimed[0].attempt_count == 1

        assert await repo.claim_due(now=_at(21)) == []

    async def test_job_dang_cho_backoff_chua_toi_luot(self, db_session: AsyncSession):
        ws = await _workspace(db_session)
        repo = PublishRepository(db_session)
        job, _ = await repo.enqueue(
            workspace_id=ws.id,
            content_item_id=await _item(db_session, ws.id),
            channel=Channel.FACEBOOK_PAGE,
            scheduled_at=_at(),
        )
        job.next_attempt_at = datetime.now(UTC) + timedelta(minutes=5)
        await db_session.flush()

        assert await repo.claim_due(now=datetime.now(UTC)) == []


class TestPhanLoaiLoi:
    async def test_loi_tam_thoi_duoc_thu_lai_voi_backoff(self, db_session: AsyncSession):
        ws = await _workspace(db_session)
        repo = PublishRepository(db_session)
        await repo.enqueue(
            workspace_id=ws.id,
            content_item_id=await _item(db_session, ws.id),
            channel=Channel.FACEBOOK_PAGE,
            scheduled_at=_at(),
        )
        job = (await repo.claim_due(now=_at(21)))[0]

        await repo.mark_failed(job, kind=PublishFailureKind.TEMPORARY, detail="429")

        assert job.status is PublishStatus.PENDING
        assert job.next_attempt_at is not None, "phải hẹn giờ thử lại"

    async def test_loi_mat_quyen_khong_retry_di_thang_dead_letter(self, db_session: AsyncSession):
        """Retry khi token hết hạn chỉ đập vào API và vẫn hỏng — cần chủ tiệm
        nối lại kênh, không phải thử lại."""
        ws = await _workspace(db_session)
        repo = PublishRepository(db_session)
        await repo.enqueue(
            workspace_id=ws.id,
            content_item_id=await _item(db_session, ws.id),
            channel=Channel.FACEBOOK_PAGE,
            scheduled_at=_at(),
        )
        job = (await repo.claim_due(now=_at(21)))[0]

        await repo.mark_failed(job, kind=PublishFailureKind.AUTH_PERMISSION, detail="token hết hạn")

        assert job.status is PublishStatus.DEAD_LETTER
        assert job.next_attempt_at is None

    async def test_loi_noi_dung_khong_retry(self, db_session: AsyncSession):
        ws = await _workspace(db_session)
        repo = PublishRepository(db_session)
        await repo.enqueue(
            workspace_id=ws.id,
            content_item_id=await _item(db_session, ws.id),
            channel=Channel.FACEBOOK_PAGE,
            scheduled_at=_at(),
        )
        job = (await repo.claim_due(now=_at(21)))[0]

        await repo.mark_failed(
            job, kind=PublishFailureKind.VALIDATION_PERMANENT, detail="nội dung bị từ chối"
        )

        assert job.status is PublishStatus.DEAD_LETTER

    async def test_het_so_lan_thu_thi_sang_dead_letter(self, db_session: AsyncSession):
        """Một bài hỏng không được đập API nền tảng mãi."""
        ws = await _workspace(db_session)
        repo = PublishRepository(db_session)
        await repo.enqueue(
            workspace_id=ws.id,
            content_item_id=await _item(db_session, ws.id),
            channel=Channel.FACEBOOK_PAGE,
            scheduled_at=_at(),
        )

        for _ in range(MAX_ATTEMPTS):
            job = (await repo.claim_due(now=_at(21)))[0]
            await repo.mark_failed(job, kind=PublishFailureKind.TEMPORARY, detail="429")
            if job.status is PublishStatus.PENDING:
                job.next_attempt_at = None
                await db_session.flush()

        assert job.status is PublishStatus.DEAD_LETTER
        assert job.attempt_count == MAX_ATTEMPTS

    async def test_thu_lai_thu_cong_dat_lai_so_lan_thu(self, db_session: AsyncSession):
        """Người bấm thử lại sau khi đã sửa nguyên nhân — cho đủ lượt như job mới."""
        ws = await _workspace(db_session)
        repo = PublishRepository(db_session)
        await repo.enqueue(
            workspace_id=ws.id,
            content_item_id=await _item(db_session, ws.id),
            channel=Channel.FACEBOOK_PAGE,
            scheduled_at=_at(),
        )
        job = (await repo.claim_due(now=_at(21)))[0]
        await repo.mark_failed(job, kind=PublishFailureKind.AUTH_PERMISSION, detail="token hết hạn")

        await repo.reset_for_manual_retry(job)

        assert job.status is PublishStatus.PENDING
        assert job.attempt_count == 0
        assert job.failure_kind is None


class TestFakePublisher:
    async def test_dang_thanh_cong_tra_ve_external_post_id(self):
        """Không có ID này thì không đối soát được khi worker chết giữa chừng."""
        publisher = FakePublisher()
        result = await publisher.publish(
            PublishRequest(text="Ưu đãi gội đầu"), access_token="token"
        )
        assert result.external_post_id
        assert result.published_at is not None

    async def test_loi_tam_thoi_roi_thanh_cong(self):
        publisher = FakePublisher(fail_times=1)

        with pytest.raises(TemporaryPublishError):
            await publisher.publish(PublishRequest(text="x"), access_token="t")

        result = await publisher.publish(PublishRequest(text="x"), access_token="t")
        assert result.external_post_id

    async def test_moi_loi_mang_dung_failure_kind(self):
        """Worker dựa vào `kind` để quyết định retry — sai phân loại là sai hết."""
        assert auth_error().kind is PublishFailureKind.AUTH_PERMISSION
        assert validation_error().kind is PublishFailureKind.VALIDATION_PERMANENT
        assert (
            TemporaryPublishError(Channel.FACEBOOK_PAGE, "429").kind is PublishFailureKind.TEMPORARY
        )


class TestConnectionRepository:
    async def test_token_luu_xuong_db_da_ma_hoa(self, db_session: AsyncSession):
        """Dump DB không được lộ token đăng bài của chủ tiệm."""
        from adapters.persistence.connection_repository import ConnectionRepository

        ws = await _workspace(db_session)
        repo = ConnectionRepository(db_session)
        token = "EAAGm0PX4ZCpsBA-facebook-page-token"

        conn = await repo.upsert(workspace_id=ws.id, platform=Platform.FACEBOOK, access_token=token)

        assert token not in conn.access_token_encrypted
        assert repo.read_access_token(conn) == token

    async def test_get_connected_channels_returns_only_connected_platforms(
        self, db_session: AsyncSession
    ):
        from adapters.persistence.connection_repository import ConnectionRepository

        ws = await _workspace(db_session)
        repo = ConnectionRepository(db_session)

        assert await repo.get_connected_channels(ws.id) == []

        conn = await repo.upsert(
            workspace_id=ws.id, platform=Platform.FACEBOOK, access_token="token-fb"
        )
        assert await repo.get_connected_channels(ws.id) == [
            Channel.FACEBOOK_PAGE,
            Channel.REELS,
        ]

        await repo.mark_unusable(conn, status=ConnectionStatus.REVOKED, reason="revoked")
        assert await repo.get_connected_channels(ws.id) == []

    async def test_noi_lai_kenh_cap_nhat_chu_khong_tao_ban_ghi_thu_hai(
        self, db_session: AsyncSession
    ):
        """Hai bản ghi thì lúc publish không biết token nào còn hiệu lực."""
        from adapters.persistence.connection_repository import ConnectionRepository

        ws = await _workspace(db_session)
        repo = ConnectionRepository(db_session)

        first = await repo.upsert(
            workspace_id=ws.id, platform=Platform.FACEBOOK, access_token="token-cu"
        )
        second = await repo.upsert(
            workspace_id=ws.id, platform=Platform.FACEBOOK, access_token="token-moi"
        )

        assert first.id == second.id
        assert repo.read_access_token(second) == "token-moi"
        assert len(await repo.list_for_workspace(ws.id)) == 1

    async def test_noi_lai_xoa_ly_do_hong_cu(self, db_session: AsyncSession):
        """Giữ lại lý do cũ sau khi nối lại thì UI hiện cảnh báo sai."""
        from adapters.persistence.connection_repository import ConnectionRepository

        ws = await _workspace(db_session)
        repo = ConnectionRepository(db_session)
        conn = await repo.upsert(workspace_id=ws.id, platform=Platform.FACEBOOK, access_token="t")
        await repo.mark_unusable(conn, status=ConnectionStatus.EXPIRED, reason="token hết hạn")

        again = await repo.upsert(
            workspace_id=ws.id, platform=Platform.FACEBOOK, access_token="token-moi"
        )

        assert again.status is ConnectionStatus.CONNECTED
        assert again.failure_reason is None

    async def test_hai_workspace_khong_thay_ket_noi_cua_nhau(self, db_session: AsyncSession):
        from adapters.persistence.connection_repository import ConnectionRepository

        a, b = await _workspace(db_session), await _workspace(db_session)
        repo = ConnectionRepository(db_session)
        await repo.upsert(workspace_id=a.id, platform=Platform.FACEBOOK, access_token="token-cua-a")

        assert await repo.get(workspace_id=b.id, platform=Platform.FACEBOOK) is None
        assert await repo.list_for_workspace(b.id) == []


class TestPublishServiceEndToEnd:
    """Vòng đầy đủ: bài đã duyệt → scheduler → worker → đăng, với fake adapter."""

    async def _service(
        self,
        session: AsyncSession,
        publisher: FakePublisher,
        alerts: AlertSink | None = None,
    ):
        from adapters.persistence.connection_repository import ConnectionRepository
        from adapters.persistence.content_repository import ContentRepository
        from application.services.publish_service import PublishService

        return PublishService(
            content=ContentRepository(session),
            connections=ConnectionRepository(session),
            publishes=PublishRepository(session),
            events=EventLogRepository(session),
            alerts=alerts,
            publishers={Channel.FACEBOOK_PAGE: publisher},
        )

    async def _ready(self, session: AsyncSession, *, at: datetime):
        """Workspace đã nối Facebook + một bài đã duyệt tới giờ đăng."""
        from adapters.persistence.connection_repository import ConnectionRepository
        from core.enums import ContentStatus
        from domain.models.content import ContentItem

        ws = await _workspace(session)
        await ConnectionRepository(session).upsert(
            workspace_id=ws.id,
            platform=Platform.FACEBOOK,
            access_token="page-token",
            external_account_id="page_1",
        )
        item = ContentItem(
            workspace_id=ws.id,
            job_id=None,
            channel=Channel.FACEBOOK_PAGE,
            kind="Bài ảnh",
            text="Ưu đãi gội đầu thảo dược",
            status=ContentStatus.SCHEDULED,
            scheduled_at=at,
        )
        session.add(item)
        await session.flush()
        return ws, item

    async def test_bai_da_duyet_toi_gio_thi_dang_duoc(self, db_session: AsyncSession):
        from core.enums import ContentStatus

        publisher = FakePublisher()
        ws, item = await self._ready(db_session, at=_at(20))
        alerts = RecordingAlerts()
        service = await self._service(db_session, publisher, alerts=alerts)

        await service.dispatch_due(now=_at(21))
        # Đếm theo workspace của test: DB dev có thể còn bài scheduled từ lần
        # chạy tay trước, và scheduler cố ý quét mọi workspace.
        mine = await PublishRepository(db_session).list_for_workspace(workspace_id=ws.id)
        assert len(mine) == 1

        await service.run_due(now=_at(21))
        jobs = await PublishRepository(db_session).list_for_workspace(workspace_id=ws.id)
        assert jobs[0].status is PublishStatus.SUCCEEDED
        assert jobs[0].external_post_id
        assert item.status is ContentStatus.PUBLISHED
        assert len(publisher.calls) == 1

        event = (
            await db_session.execute(
                select(EventLog).where(
                    EventLog.job_id == jobs[0].id,
                    EventLog.job_kind == "publish.run_job",
                )
            )
        ).scalar_one()
        assert event.workspace_id == ws.id
        assert event.provider == "facebook"
        assert event.error is None
        assert jobs[0].external_post_id in event.output_summary

    async def test_video_chua_co_file_thi_worker_chan_khong_dung_clip_mau(
        self, db_session: AsyncSession
    ):
        from adapters.persistence.connection_repository import ConnectionRepository
        from adapters.persistence.content_repository import ContentRepository
        from application.services.publish_service import PublishService
        from core.enums import ContentStatus
        from domain.models.content import ContentItem

        publisher = FakePublisher(channel=Channel.TIKTOK)
        ws = await _workspace(db_session)
        await ConnectionRepository(db_session).upsert(
            workspace_id=ws.id,
            platform=Platform.TIKTOK,
            access_token="tiktok-token",
            external_account_id="open-id-1",
        )
        item = ContentItem(
            workspace_id=ws.id,
            job_id=None,
            channel=Channel.TIKTOK,
            kind="Video TikTok",
            text="Hook video chưa được dựng",
            media_url=None,
            status=ContentStatus.SCHEDULED,
            scheduled_at=_at(20),
        )
        db_session.add(item)
        await db_session.flush()

        service = PublishService(
            content=ContentRepository(db_session),
            connections=ConnectionRepository(db_session),
            publishes=PublishRepository(db_session),
            events=EventLogRepository(db_session),
            publishers={Channel.TIKTOK: publisher},
        )
        await service.dispatch_due(now=_at(21))
        await service.run_due(now=_at(21))

        jobs = await PublishRepository(db_session).list_for_workspace(workspace_id=ws.id)
        assert jobs[0].status is PublishStatus.DEAD_LETTER
        assert jobs[0].failure_kind is PublishFailureKind.VALIDATION_PERMANENT
        assert "chưa có file hoàn chỉnh" in (jobs[0].failure_detail or "")
        assert publisher.calls == [], "worker không được tự thay bằng clip mẫu rồi gọi TikTok"

    async def test_scheduler_chay_lai_khong_dang_hai_lan(self, db_session: AsyncSession):
        """Beat quét mỗi 5 phút — chạy lại không được sinh job trùng."""
        publisher = FakePublisher()
        ws, _ = await self._ready(db_session, at=_at(20))
        service = await self._service(db_session, publisher)

        await service.dispatch_due(now=_at(21))
        repo = PublishRepository(db_session)
        after_first = len(await repo.list_for_workspace(workspace_id=ws.id))
        await service.dispatch_due(now=_at(21))
        after_second = len(await repo.list_for_workspace(workspace_id=ws.id))

        assert after_first == 1
        assert after_second == 1, "lần quét thứ hai không được tạo job mới"

    async def test_bai_chua_duyet_khong_bao_gio_dang(self, db_session: AsyncSession):
        """Chốt chặn nguyên tắc #1 — không bài nào lên mạng khi chưa duyệt."""
        from core.enums import ContentStatus
        from domain.models.content import ContentItem

        publisher = FakePublisher()
        ws = await _workspace(db_session)
        db_session.add(
            ContentItem(
                workspace_id=ws.id,
                job_id=None,
                channel=Channel.FACEBOOK_PAGE,
                kind="Bài ảnh",
                text="Chưa duyệt",
                status=ContentStatus.PENDING_APPROVAL,
                scheduled_at=_at(20),
            )
        )
        await db_session.flush()
        service = await self._service(db_session, publisher)

        await service.dispatch_due(now=_at(21))

        mine = await PublishRepository(db_session).list_for_workspace(workspace_id=ws.id)
        assert mine == [], "bài chưa duyệt không được xếp vào hàng đợi"
        assert publisher.calls == []

    async def test_chua_noi_kenh_thi_bao_loi_noi_lai(self, db_session: AsyncSession):
        from core.enums import ContentStatus
        from domain.models.content import ContentItem

        publisher = FakePublisher()
        ws = await _workspace(db_session)
        db_session.add(
            ContentItem(
                workspace_id=ws.id,
                job_id=None,
                channel=Channel.FACEBOOK_PAGE,
                kind="Bài ảnh",
                text="x",
                status=ContentStatus.SCHEDULED,
                scheduled_at=_at(20),
            )
        )
        await db_session.flush()
        alerts = RecordingAlerts()
        service = await self._service(db_session, publisher, alerts=alerts)
        await service.dispatch_due(now=_at(21))

        repo = PublishRepository(db_session)
        job = (await repo.list_for_workspace(workspace_id=ws.id))[0]
        job.status = PublishStatus.IN_FLIGHT
        job.attempt_count = 1
        await db_session.flush()
        await service.run_job(job)

        assert job.status is PublishStatus.DEAD_LETTER
        assert job.failure_kind is PublishFailureKind.AUTH_PERMISSION
        assert "nối lại" in job.failure_detail
        assert alerts.sent[0].type == "publish.dead_letter"
        assert alerts.sent[0].job_id == str(job.id)
        assert alerts.sent[0].fields["failure_kind"] == "auth_permission"
        event = (
            await db_session.execute(
                select(EventLog).where(
                    EventLog.job_id == job.id,
                    EventLog.job_kind == "publish.run_job",
                )
            )
        ).scalar_one()
        assert event.error == job.failure_detail
        assert "auth_permission" in event.output_summary

    async def test_mat_quyen_thi_danh_dau_luon_ket_noi(self, db_session: AsyncSession):
        """Không đánh dấu thì mọi bài sau cũng hỏng mà UI vẫn hiện chấm xanh."""
        from adapters.persistence.connection_repository import ConnectionRepository

        publisher = FakePublisher(error=auth_error())
        ws, _ = await self._ready(db_session, at=_at(20))
        service = await self._service(db_session, publisher)
        await service.dispatch_due(now=_at(21))

        await service.run_due(now=_at(21))

        conn = await ConnectionRepository(db_session).get(
            workspace_id=ws.id, platform=Platform.FACEBOOK
        )
        assert conn.status is ConnectionStatus.EXPIRED
        assert conn.failure_reason

    async def test_loi_tam_thoi_thi_thu_lai_va_dang_duoc(self, db_session: AsyncSession):
        """Rate limit lần đầu, lần sau thành công — và chỉ ra đúng MỘT bài."""
        publisher = FakePublisher(fail_times=1)
        ws, _ = await self._ready(db_session, at=_at(20))
        service = await self._service(db_session, publisher)
        await service.dispatch_due(now=_at(21))
        repo = PublishRepository(db_session)
        job = (await repo.list_for_workspace(workspace_id=ws.id))[0]

        job.status, job.attempt_count = PublishStatus.IN_FLIGHT, 1
        await db_session.flush()
        await service.run_job(job)
        assert job.status is PublishStatus.PENDING, "lỗi tạm thời phải được thử lại"

        job.status, job.attempt_count = PublishStatus.IN_FLIGHT, 2
        await db_session.flush()
        await service.run_job(job)

        assert job.status is PublishStatus.SUCCEEDED
        assert len(publisher.calls) == 2, "gọi hai lần nhưng chỉ một bài lên"

    async def test_mot_job_hong_khong_lam_hong_ca_lo(self, db_session: AsyncSession):
        publisher = FakePublisher(error=validation_error())
        ws, _ = await self._ready(db_session, at=_at(20))
        # Bài thứ hai cùng workspace: một bài hỏng không được chặn bài kia.
        from core.enums import ContentStatus
        from domain.models.content import ContentItem

        db_session.add(
            ContentItem(
                workspace_id=ws.id,
                job_id=None,
                channel=Channel.FACEBOOK_PAGE,
                kind="Bài ảnh",
                text="Bài thứ hai",
                status=ContentStatus.SCHEDULED,
                scheduled_at=_at(20),
            )
        )
        await db_session.flush()
        service = await self._service(db_session, publisher)
        await service.dispatch_due(now=_at(21))

        repo = PublishRepository(db_session)
        mine = await repo.list_for_workspace(workspace_id=ws.id)
        assert len(mine) == 2
        for job in mine:
            job.status, job.attempt_count = PublishStatus.IN_FLIGHT, 1
            await db_session.flush()
            await service.run_job(job)

        assert all(j.status is PublishStatus.DEAD_LETTER for j in mine)
