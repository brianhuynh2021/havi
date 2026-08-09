"""Quota token theo workspace — chặn chi phí LLM trước khi nó xảy ra.

Quota tính theo **token**, không theo tiền: mỗi provider một đơn giá và giá LLM
đổi liên tục, nên bảng giá hardcode cho ra con số nhìn như đúng mà sai — tệ hơn
không có quota, vì nó tạo cảm giác đang kiểm soát chi phí trong khi không.

Nhóm test quan trọng nhất là `TestChanTruocKhiTonTien`: kiểm rằng job bị chặn
*trước khi* vào hàng đợi. Chặn sau khi enqueue thì tiền đã tiêu rồi mới báo hết
quota — vô nghĩa.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.persistence.event_log_repository import EventLogRepository
from core.enums import Industry, Plan
from core.events import EventLogEntry
from domain.models.user import User
from domain.models.workspace import Workspace, WorkspaceMember
from domain.policies import quota

pytestmark = pytest.mark.anyio


async def _workspace(session: AsyncSession, *, plan: Plan = Plan.TRIAL) -> Workspace:
    owner = User(email=f"{uuid.uuid4().hex[:10]}@spa.vn", name="Chị Hương")
    session.add(owner)
    await session.flush()
    ws = Workspace(
        name="Spa An Nhiên", industry=Industry.SPA, owner_user_id=owner.id, plan=plan
    )
    session.add(ws)
    await session.flush()
    session.add(WorkspaceMember(workspace_id=ws.id, user_id=owner.id, role="owner"))
    await session.flush()
    return ws


async def _burn(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    *,
    tokens: int,
    error: str | None = None,
) -> None:
    """Ghi một lượt dùng token vào event_log."""
    await EventLogRepository(session).record(
        EventLogEntry(
            workspace_id=workspace_id,
            job_kind="content.generate_drafts",
            tokens_in=tokens // 2,
            tokens_out=tokens - tokens // 2,
            provider="gemini",
            error=error,
        )
    )


class TestMocThoiGian:
    """Quota theo tháng dương lịch, giờ VN."""

    def test_moc_dau_thang_tinh_theo_gio_vn_khong_utc(self):
        """20:00 ngày 31/7 giờ VN là 13:00 UTC ngày 31/7 — vẫn thuộc tháng 7.

        Nhưng 06:00 ngày 1/8 giờ VN là 23:00 UTC ngày 31/7. Nếu tính mốc theo UTC
        thì 7 tiếng đầu mỗi tháng bị tính vào quota tháng trước.
        """
        sang_som_1_8_vn = datetime(2026, 7, 31, 23, 30, tzinfo=UTC)  # 06:30 1/8 VN
        start = quota.month_start_utc(sang_som_1_8_vn)

        vn_start = start.astimezone(quota.VN_TZ)
        assert (vn_start.month, vn_start.day) == (8, 1)
        assert (vn_start.hour, vn_start.minute) == (0, 0)

    def test_moc_mo_lai_la_dau_thang_sau(self):
        giua_thang_8 = datetime(2026, 8, 15, 12, 0, tzinfo=UTC)
        resets = quota.next_month_start_utc(giua_thang_8).astimezone(quota.VN_TZ)
        assert (resets.month, resets.day) == (9, 1)

    def test_thang_12_sang_thang_1_nam_sau(self):
        """Cộng 32 ngày rồi ép về ngày 1 — không tự cộng tháng bằng tay nên không
        có lỗi 12+1=13."""
        cuoi_nam = datetime(2026, 12, 20, 12, 0, tzinfo=UTC)
        resets = quota.next_month_start_utc(cuoi_nam).astimezone(quota.VN_TZ)
        assert (resets.year, resets.month, resets.day) == (2027, 1, 1)

    def test_thang_2_nam_nhuan(self):
        """2028 là năm nhuận (29/2). Mốc kế tiếp vẫn phải là 1/3."""
        thang_2 = datetime(2028, 2, 10, 12, 0, tzinfo=UTC)
        resets = quota.next_month_start_utc(thang_2).astimezone(quota.VN_TZ)
        assert (resets.month, resets.day) == (3, 1)


class TestTranTheoGoi:
    def test_moi_goi_mot_tran(self):
        assert quota.quota_for(Plan.TRIAL) < quota.quota_for(Plan.TIEM_NHO)
        assert quota.quota_for(Plan.TIEM_NHO) < quota.quota_for(Plan.TOAN_DIEN)

    def test_moi_gia_tri_plan_deu_co_tran(self):
        """Thêm gói mới mà quên khai trần là để nó chạy không giới hạn — mất tiền
        thật. Test này bắt ngay lúc thêm enum."""
        for plan in Plan:
            assert plan in quota.MONTHLY_TOKEN_QUOTA, f"thiếu trần cho gói {plan}"

    def test_goi_la_roi_ve_muc_trial_khong_phai_vo_han(self):
        """Nếu có gói không nằm trong bảng (dữ liệu cũ, hoặc lỗi migration), chặn
        chặt là bất tiện; không giới hạn là mất tiền."""
        assert quota.quota_for("goi_khong_ton_tai") == quota.quota_for(Plan.TRIAL)


class TestNguongCanhBao:
    def test_qua_80_phan_tram_thi_canh_bao_nhung_chua_chan(self):
        status = quota.evaluate(plan=Plan.TIEM_NHO, used=int(500_000 * 0.85))
        assert status.near_limit is True
        assert status.exceeded is False

    def test_duoi_nguong_thi_khong_canh_bao(self):
        status = quota.evaluate(plan=Plan.TIEM_NHO, used=int(500_000 * 0.5))
        assert status.near_limit is False

    def test_da_vuot_tran_thi_khong_con_la_canh_bao_ma_la_chan(self):
        """`near_limit` và `exceeded` loại trừ nhau — UI hiện một thông báo, không
        hiện cả 'gần hết' lẫn 'đã hết' cùng lúc."""
        status = quota.evaluate(plan=Plan.TIEM_NHO, used=600_000)
        assert status.exceeded is True
        assert status.near_limit is False

    def test_remaining_khong_bao_gio_am(self):
        status = quota.evaluate(plan=Plan.TRIAL, used=999_999_999)
        assert status.remaining == 0


class TestDemTokenTuEventLog:
    async def test_cong_ca_tokens_in_va_out(self, db_session: AsyncSession):
        ws = await _workspace(db_session)
        await _burn(db_session, ws.id, tokens=1000)
        await _burn(db_session, ws.id, tokens=500)

        used = await EventLogRepository(db_session).tokens_used_since(
            workspace_id=ws.id, since=datetime.now(UTC) - timedelta(hours=1)
        )
        assert used == 1500

    async def test_dem_ca_luot_bi_loi(self, db_session: AsyncSession):
        """Provider trả lỗi vẫn tốn token đã gửi. Bỏ ra là mở đường cho một
        workspace liên tục gửi prompt lỗi mà không tính vào quota."""
        ws = await _workspace(db_session)
        await _burn(db_session, ws.id, tokens=800, error="rate limit")

        used = await EventLogRepository(db_session).tokens_used_since(
            workspace_id=ws.id, since=datetime.now(UTC) - timedelta(hours=1)
        )
        assert used == 800

    async def test_khong_dem_token_cua_workspace_khac(self, db_session: AsyncSession):
        """Tenant isolation: tiệm này tiêu token không được ăn vào quota tiệm kia."""
        chi_huong = await _workspace(db_session)
        chi_lan = await _workspace(db_session)
        await _burn(db_session, chi_huong.id, tokens=50_000)

        used = await EventLogRepository(db_session).tokens_used_since(
            workspace_id=chi_lan.id, since=datetime.now(UTC) - timedelta(hours=1)
        )
        assert used == 0

    async def test_khong_dem_token_thang_truoc(self, db_session: AsyncSession):
        """Quota reset theo tháng — token tháng trước không được tính tiếp."""
        ws = await _workspace(db_session)
        await _burn(db_session, ws.id, tokens=10_000)

        # `since` ở tương lai = không tính dòng nào.
        used = await EventLogRepository(db_session).tokens_used_since(
            workspace_id=ws.id, since=datetime.now(UTC) + timedelta(hours=1)
        )
        assert used == 0

    async def test_workspace_chua_dung_gi_thi_bang_0(self, db_session: AsyncSession):
        """Không phải None — UI chia cho limit nên None sẽ nổ."""
        ws = await _workspace(db_session)
        used = await EventLogRepository(db_session).tokens_used_since(
            workspace_id=ws.id, since=quota.month_start_utc(datetime.now(UTC))
        )
        assert used == 0


async def _onboard(client: AsyncClient, *, email: str) -> dict:
    signup = await client.post(
        "/auth/sign-up",
        json={"name": "Chị Hương", "email": email, "password": "matkhau123"},
    )
    assert signup.status_code == 201, signup.text
    tokens = signup.json()
    create = await client.post(
        "/workspaces",
        json={"name": "Spa An Nhiên", "industry": "spa"},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert create.status_code == 201, create.text
    refreshed = await client.post(
        "/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert refreshed.status_code == 200, refreshed.text
    return refreshed.json()


def _headers(token_pair: dict) -> dict:
    return {"Authorization": f"Bearer {token_pair['access_token']}"}


def _workspace_id(token_pair: dict) -> uuid.UUID:
    from core.config import get_settings
    from core.security import decode_access_token

    decoded = decode_access_token(token_pair["access_token"], get_settings())
    assert decoded.active_workspace_id is not None
    return decoded.active_workspace_id


class TestChanTruocKhiTonTien:
    """Nhóm quan trọng nhất: job phải bị chặn TRƯỚC khi vào hàng đợi."""

    async def test_vuot_tran_thi_khong_enqueue_job_nao(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Chặn sau khi enqueue thì worker đã gọi LLM và tiền đã tiêu — báo 'hết
        quota' lúc đó là vô nghĩa. Test này verify hàng đợi trống."""
        from api.deps import get_job_queue
        from application.services.job_queue import RecordingJobQueue

        recorder = RecordingJobQueue()
        app = client._transport.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_job_queue] = lambda: recorder

        token = await _onboard(client, email="quota0001@havi.vn")
        # Workspace mới là gói Trial (100k). Đốt hết.
        await _burn(db_session, _workspace_id(token), tokens=150_000)

        response = await client.post(
            "/content/jobs",
            json={"raw_inputs": [{"kind": "text", "text": "Ưu đãi cuối tuần"}]},
            headers=_headers(token),
        )

        assert response.status_code == 429, response.text
        assert recorder.enqueued == [], "job đã lọt vào hàng đợi dù hết quota!"

    async def test_429_kem_retry_after_va_so_lieu_that(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Chủ tiệm cần biết đã dùng bao nhiêu và bao giờ có lại — không phải chỉ
        một chữ 'hết quota'."""
        token = await _onboard(client, email="quota0002@havi.vn")
        await _burn(db_session, _workspace_id(token), tokens=150_000)

        response = await client.post(
            "/content/jobs",
            json={"raw_inputs": [{"kind": "text", "text": "Ưu đãi"}]},
            headers=_headers(token),
        )

        assert response.status_code == 429
        assert int(response.headers["Retry-After"]) > 0
        detail = response.json()["detail"]
        assert "100,000" in detail  # trần Trial, có dấu phân cách cho dễ đọc
        assert "quota mở lại" in detail

    async def test_con_quota_thi_tao_job_binh_thuong(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        token = await _onboard(client, email="quota0003@havi.vn")
        await _burn(db_session, _workspace_id(token), tokens=1_000)

        response = await client.post(
            "/content/jobs",
            json={"raw_inputs": [{"kind": "text", "text": "Ưu đãi"}]},
            headers=_headers(token),
        )
        assert response.status_code == 202, response.text

    async def test_workspace_moi_chua_dung_gi_van_tao_duoc_job(
        self, client: AsyncClient
    ):
        """Quota 0/100k không được chặn — nếu chặn thì không ai dùng được app."""
        token = await _onboard(client, email="quota0004@havi.vn")
        response = await client.post(
            "/content/jobs",
            json={"raw_inputs": [{"kind": "text", "text": "Ưu đãi"}]},
            headers=_headers(token),
        )
        assert response.status_code == 202, response.text


class TestQuotaEndpoint:
    async def test_tra_so_lieu_that(self, client: AsyncClient, db_session: AsyncSession):
        token = await _onboard(client, email="quota0010@havi.vn")
        await _burn(db_session, _workspace_id(token), tokens=30_000)

        response = await client.get("/content/quota", headers=_headers(token))
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["used"] == 30_000
        assert body["limit"] == 100_000
        assert body["remaining"] == 70_000
        assert body["exceeded"] is False

    async def test_route_khong_bi_doc_nhu_uuid(self, client: AsyncClient):
        """`/content/quota` phải khớp route riêng, không rơi vào
        `/content/{content_id}` và trả 422 vì "quota" không phải UUID."""
        token = await _onboard(client, email="quota0011@havi.vn")
        response = await client.get("/content/quota", headers=_headers(token))
        assert response.status_code == 200, response.text

    async def test_can_dang_nhap(self, client: AsyncClient):
        assert (await client.get("/content/quota")).status_code == 401

    async def test_hai_tiem_khong_thay_quota_cua_nhau(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        chi_huong = await _onboard(client, email="quota0012@havi.vn")
        chi_lan = await _onboard(client, email="quota0013@havi.vn")
        await _burn(db_session, _workspace_id(chi_huong), tokens=40_000)

        response = await client.get("/content/quota", headers=_headers(chi_lan))
        assert response.json()["used"] == 0
