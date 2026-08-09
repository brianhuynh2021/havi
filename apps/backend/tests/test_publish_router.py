"""`/content/publish-jobs*` qua HTTP thật — thử lại thủ công và tenant scope.

Khác `test_publish_flow.py` (test service/repository trực tiếp), file này kiểm
đúng phần chỉ tầng HTTP mới lộ ra: route `publish-jobs` không bị đọc như UUID,
job của tiệm khác trả 404 chứ không 403 (không tiết lộ UUID đó tồn tại), và bấm
"Thử lại" trên bài chưa dead-letter bị chặn thay vì đăng trùng.
"""

import uuid
from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.persistence.connection_repository import ConnectionRepository
from adapters.persistence.content_repository import ContentRepository
from adapters.persistence.event_log_repository import EventLogRepository
from adapters.persistence.publish_repository import PublishRepository
from adapters.publishers.fake import FakePublisher, validation_error
from api.deps import get_publish_service
from application.services.publish_service import PublishService
from core.enums import (
    Channel,
    ContentStatus,
    Platform,
    PublishFailureKind,
    PublishStatus,
)
from domain.models.content import ContentItem


async def _onboard(client: AsyncClient, *, email: str) -> dict:
    """Đăng ký → tạo workspace → refresh để JWT mang active_workspace_id."""
    signup = await client.post(
        "/auth/sign-up",
        json={"name": "Chị Hương", "email": email, "password": "matkhau123"},
    )
    assert signup.status_code == 201, signup.text
    token_pair = signup.json()

    create = await client.post(
        "/workspaces",
        json={"name": "Spa An Nhiên", "industry": "spa"},
        headers={"Authorization": f"Bearer {token_pair['access_token']}"},
    )
    assert create.status_code == 201, create.text

    refreshed = await client.post(
        "/auth/refresh", json={"refresh_token": token_pair["refresh_token"]}
    )
    assert refreshed.status_code == 200, refreshed.text
    return refreshed.json()


def _headers(token_pair: dict) -> dict:
    return {"Authorization": f"Bearer {token_pair['access_token']}"}


def _override(
    client: AsyncClient, db_session: AsyncSession, publisher: FakePublisher
) -> None:
    """Thay adapter Facebook thật bằng fake, giữ nguyên repository và DB session."""
    app = client._transport.app  # type: ignore[attr-defined]

    def _factory() -> PublishService:
        return PublishService(
            content=ContentRepository(db_session),
            connections=ConnectionRepository(db_session),
            publishes=PublishRepository(db_session),
            events=EventLogRepository(db_session),
            publishers={Channel.FACEBOOK_PAGE: publisher},
        )

    app.dependency_overrides[get_publish_service] = _factory


def _workspace_id(token_pair: dict) -> uuid.UUID:
    from core.config import get_settings
    from core.security import decode_access_token

    decoded = decode_access_token(token_pair["access_token"], get_settings())
    assert decoded.active_workspace_id is not None
    return decoded.active_workspace_id


async def _dead_letter_job(
    db_session: AsyncSession, workspace_id: uuid.UUID, *, at: datetime
):
    """Một bài đã duyệt + kênh đã nối + một job đã dừng hẳn sau nhiều lần lỗi.

    Đi qua `mark_failed` thật thay vì set `status` bằng tay: nếu luật retry đổi
    (ví dụ AUTH_PERMISSION được retry), test này phải đổi theo chứ không âm thầm
    kiểm một trạng thái mà code thật không còn tạo ra nữa.
    """
    await ConnectionRepository(db_session).upsert(
        workspace_id=workspace_id,
        platform=Platform.FACEBOOK,
        access_token="page-token",
        external_account_id="page_1",
    )
    item = ContentItem(
        workspace_id=workspace_id,
        job_id=None,
        channel=Channel.FACEBOOK_PAGE,
        kind="Bài ảnh",
        text="Ưu đãi gội đầu thảo dược",
        status=ContentStatus.SCHEDULED,
        scheduled_at=at,
    )
    db_session.add(item)
    await db_session.flush()

    publishes = PublishRepository(db_session)
    job, _ = await publishes.enqueue(
        workspace_id=workspace_id,
        content_item_id=item.id,
        channel=Channel.FACEBOOK_PAGE,
        scheduled_at=at,
    )
    await publishes.mark_failed(
        job,
        kind=PublishFailureKind.VALIDATION_PERMANENT,
        detail="Facebook từ chối nội dung",
    )
    assert job.status is PublishStatus.DEAD_LETTER
    return item, job


def _at(hours_ago: int = 1) -> datetime:
    return datetime.now(UTC) - timedelta(hours=hours_ago)


class TestListPublishJobs:
    async def test_route_khong_bi_doc_nhu_uuid(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """`/content/publish-jobs` phải khớp route riêng, không rơi vào
        `/content/{content_id}` và trả 422 vì "publish-jobs" không phải UUID."""
        token = await _onboard(client, email="pub0001@havi.vn")
        _override(client, db_session, FakePublisher())

        response = await client.get("/content/publish-jobs", headers=_headers(token))
        assert response.status_code == 200, response.text
        assert response.json() == []

    async def test_loc_theo_dead_letter(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        token = await _onboard(client, email="pub0002@havi.vn")
        _override(client, db_session, FakePublisher())
        await _dead_letter_job(db_session, _workspace_id(token), at=_at())

        response = await client.get(
            "/content/publish-jobs",
            params={"status": "dead_letter"},
            headers=_headers(token),
        )
        assert response.status_code == 200, response.text
        jobs = response.json()
        assert len(jobs) == 1
        assert jobs[0]["failure_kind"] == "validation_permanent"

    async def test_khong_bao_gio_lo_idempotency_key(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Khoá chống đăng trùng là chi tiết nội bộ — lộ ra là mở đường cho
        người ngoài đoán khoá và tự tạo job trùng."""
        token = await _onboard(client, email="pub0003@havi.vn")
        _override(client, db_session, FakePublisher())
        await _dead_letter_job(db_session, _workspace_id(token), at=_at())

        response = await client.get("/content/publish-jobs", headers=_headers(token))
        assert "idempotency_key" not in response.text

    async def test_can_dang_nhap(self, client: AsyncClient):
        assert (await client.get("/content/publish-jobs")).status_code == 401

    async def test_hai_tiem_khong_thay_luot_dang_cua_nhau(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        chi_huong = await _onboard(client, email="pub0004@havi.vn")
        chi_lan = await _onboard(client, email="pub0005@havi.vn")
        _override(client, db_session, FakePublisher())
        await _dead_letter_job(db_session, _workspace_id(chi_huong), at=_at())

        response = await client.get(
            "/content/publish-jobs", headers=_headers(chi_lan)
        )
        assert response.status_code == 200
        assert response.json() == []


class TestRetryPublishJob:
    async def test_thu_lai_dead_letter_thi_dang_duoc(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Người bấm nút phải thấy kết quả thật ngay, không phải 202 rồi tự tra."""
        token = await _onboard(client, email="pub0010@havi.vn")
        publisher = FakePublisher()
        _override(client, db_session, publisher)
        item, job = await _dead_letter_job(db_session, _workspace_id(token), at=_at())

        response = await client.post(
            f"/content/publish-jobs/{job.id}/retry", headers=_headers(token)
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["status"] == "succeeded"
        assert body["external_post_id"]
        assert body["failure_kind"] is None
        assert item.status is ContentStatus.PUBLISHED
        assert len(publisher.calls) == 1

    async def test_thu_lai_dat_lai_so_lan_thu(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Người đã sửa nguyên nhân thì cho đủ lượt thử như job mới — nhưng lượt
        này cũng tính một lần, nên `attempt_count` là 1 chứ không 0."""
        token = await _onboard(client, email="pub0011@havi.vn")
        _override(client, db_session, FakePublisher())
        _, job = await _dead_letter_job(db_session, _workspace_id(token), at=_at())

        response = await client.post(
            f"/content/publish-jobs/{job.id}/retry", headers=_headers(token)
        )
        assert response.json()["attempt_count"] == 1

    async def test_thu_lai_van_hong_thi_ve_dead_letter(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Nguyên nhân chưa sửa thì job phải dừng lại chỗ cũ, kèm lý do mới."""
        token = await _onboard(client, email="pub0012@havi.vn")
        publisher = FakePublisher(error=validation_error())
        _override(client, db_session, publisher)
        _, job = await _dead_letter_job(db_session, _workspace_id(token), at=_at())

        response = await client.post(
            f"/content/publish-jobs/{job.id}/retry", headers=_headers(token)
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["status"] == "dead_letter"
        assert body["failure_kind"] == "validation_permanent"
        assert "từ chối" in body["failure_detail"]

    async def test_job_dang_cho_scheduler_thi_tu_choi(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """`pending` nghĩa là scheduler sẽ tự chạy. Cho bấm thêm là mở đường cho
        hai lượt chạy song song trên cùng một bài."""
        token = await _onboard(client, email="pub0013@havi.vn")
        _override(client, db_session, FakePublisher())
        workspace_id = _workspace_id(token)
        _, job = await _dead_letter_job(db_session, workspace_id, at=_at())
        await PublishRepository(db_session).reset_for_manual_retry(job)
        assert job.status is PublishStatus.PENDING

        response = await client.post(
            f"/content/publish-jobs/{job.id}/retry", headers=_headers(token)
        )
        assert response.status_code == 409, response.text

    async def test_job_da_dang_thanh_cong_khong_dang_lai(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Bài đã lên Trang rồi — chạy lại là đăng trùng, đúng thứ cả tầng
        idempotency dựng ra để chặn."""
        token = await _onboard(client, email="pub0014@havi.vn")
        publisher = FakePublisher()
        _override(client, db_session, publisher)
        _, job = await _dead_letter_job(db_session, _workspace_id(token), at=_at())
        await PublishRepository(db_session).mark_succeeded(
            job, external_post_id="page_1_999", published_at=datetime.now(UTC)
        )

        response = await client.post(
            f"/content/publish-jobs/{job.id}/retry", headers=_headers(token)
        )
        assert response.status_code == 409, response.text
        assert publisher.calls == []

    async def test_job_khong_ton_tai_tra_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        token = await _onboard(client, email="pub0015@havi.vn")
        _override(client, db_session, FakePublisher())

        response = await client.post(
            f"/content/publish-jobs/{uuid.uuid4()}/retry", headers=_headers(token)
        )
        assert response.status_code == 404, response.text

    async def test_job_cua_tiem_khac_tra_404_chu_khong_403(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """404 chứ không 403: 403 xác nhận UUID đó có tồn tại ở đâu đó, và một
        job id lộ ra là biết tiệm khác đang đăng bài."""
        chi_huong = await _onboard(client, email="pub0016@havi.vn")
        chi_lan = await _onboard(client, email="pub0017@havi.vn")
        publisher = FakePublisher()
        _override(client, db_session, publisher)
        _, job = await _dead_letter_job(db_session, _workspace_id(chi_huong), at=_at())

        response = await client.post(
            f"/content/publish-jobs/{job.id}/retry", headers=_headers(chi_lan)
        )
        assert response.status_code == 404, response.text
        assert publisher.calls == []
        assert job.status is PublishStatus.DEAD_LETTER

    async def test_can_dang_nhap(self, client: AsyncClient):
        response = await client.post(f"/content/publish-jobs/{uuid.uuid4()}/retry")
        assert response.status_code == 401
