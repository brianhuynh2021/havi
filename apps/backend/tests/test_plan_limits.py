"""Trần theo gói — thứ khách hàng thật sự mua khi trả thêm tiền.

Trước đó quota token là gate duy nhất theo gói: phân quyền, báo cáo, nhiều thương
hiệu đều có ở mọi gói kể cả gói dùng thử, trong khi bảng giá bán chúng như tính
năng của gói cao hơn. Thang giá thực chất là một thang token — tức Havi vẫn được
định giá như một công cụ viết nội dung bằng AI.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from core.enums import Plan
from domain.policies import plan_limits
from domain.policies.plan_limits import PlanLimitExceeded


class TestPolicy:
    def test_moi_goi_deu_co_tran(self):
        """Thiếu trần cho một gói là gói đó rơi về trần thấp nhất — đúng hướng an
        toàn, nhưng người mua gói cao sẽ bị chặn oan."""
        for plan in Plan:
            assert plan in plan_limits.LIMITS, f"thiếu trần cho gói {plan}"

    def test_goi_cao_hon_khong_bao_gio_it_ghe_hon(self):
        ladder = [Plan.TRIAL, Plan.TIEM_NHO, Plan.TOAN_DIEN, Plan.DOANH_NGHIEP]
        seats = [plan_limits.limits_for(plan).max_seats for plan in ladder]
        channels = [plan_limits.limits_for(plan).max_channels for plan in ladder]
        assert seats == sorted(seats)
        assert channels == sorted(channels)

    def test_goi_dung_thu_khong_du_cho_mot_doi_dung_mien_phi_mai(self):
        """Đủ để chạy hết một vòng vận hành thật (chủ + một người trực), không đủ
        để một đội bốn người ở lại gói 0đ."""
        assert plan_limits.limits_for(Plan.TRIAL).max_seats < 4

    def test_gia_tri_plan_la_roi_ve_tran_thap_nhat_khong_mo_het(self):
        """Một `plan` không đọc được mà mở toàn quyền là lỗ hổng thương mại im
        lặng — không ai thấy tới khi xem hoá đơn."""
        assert plan_limits.limits_for("gói_bịa") == plan_limits.limits_for(Plan.TRIAL)  # type: ignore[arg-type]

    def test_chua_dung_het_thi_khong_chan(self):
        limit = plan_limits.limits_for(Plan.TIEM_NHO).max_seats
        plan_limits.check_seats(plan=Plan.TIEM_NHO, current=limit - 1)

    def test_dung_het_thi_chan_va_cau_loi_noi_ro_phai_lam_gi(self):
        limit = plan_limits.limits_for(Plan.TIEM_NHO).max_seats
        with pytest.raises(PlanLimitExceeded) as exc:
            plan_limits.check_seats(plan=Plan.TIEM_NHO, current=limit)

        message = str(exc.value)
        assert "Gói Khởi Nghiệp" in message
        assert str(limit) in message
        assert "Nâng gói" in message

    def test_khong_co_tran_so_thuong_hieu(self):
        """Mỗi thương hiệu là một workspace và trả gói riêng, nên tạo thương hiệu
        thứ hai là mở một thuê bao thứ hai — không lấn vào hạn mức của cái thứ
        nhất. Có `check_brands` nghĩa là ai đó đã hiểu sai mô hình tính tiền."""
        assert not hasattr(plan_limits, "check_brands")


    def test_so_tren_bang_gia_phai_khop_chinh_sach(self):
        """Chống lệch giữa hai nơi.

        `apps/web/src/features/billing/billing-screen.tsx` in các con số này ra
        cho khách đọc trước khi mua. Bảng giá nói "3 người" mà backend chặn ở 2 là
        một lời hứa sai được phát hiện sau khi đã thu tiền.

        Sửa `LIMITS` thì test này vỡ, và nó nói đúng file frontend cần sửa theo.
        """
        expected_on_pricing_page = {
            Plan.TRIAL: (2, 2),
            Plan.TIEM_NHO: (3, 3),
            Plan.TOAN_DIEN: (10, 8),
            Plan.DOANH_NGHIEP: (50, plan_limits.UNLIMITED),
        }
        for plan, (seats, channels) in expected_on_pricing_page.items():
            limits = plan_limits.limits_for(plan)
            assert (limits.max_seats, limits.max_channels) == (seats, channels), (
                f"{plan.value}: bảng giá đang in ({seats} người, {channels} kênh). "
                "Đổi LIMITS thì phải sửa billing-screen.tsx theo."
            )


async def _signup(client: AsyncClient, *, email: str, name: str = "Chị Hương") -> dict:
    signup = await client.post(
        "/auth/sign-up",
        json={"name": name, "email": email, "password": "matkhau123"},
    )
    assert signup.status_code == 201, signup.text
    return signup.json()


async def _onboard(client: AsyncClient, *, email: str) -> dict:
    token_pair = await _signup(client, email=email)
    create = await client.post(
        "/workspaces",
        json={"name": "Resort An Nhiên"},
        headers={"Authorization": f"Bearer {token_pair['access_token']}"},
    )
    assert create.status_code == 201, create.text
    refreshed = await client.post(
        "/auth/refresh", json={"refresh_token": token_pair["refresh_token"]}
    )
    return refreshed.json()


def _headers(token_pair: dict) -> dict:
    return {"Authorization": f"Bearer {token_pair['access_token']}"}


async def test_moi_qua_tran_ghe_tra_402_kem_cau_huong_dan(
    client: AsyncClient, db_session: AsyncSession
):
    """402 chứ không 429: trần ghế **không** tự hết khi sang tháng như quota
    token. Muốn thêm người thì phải nâng gói."""
    owner = await _onboard(client, email="seats-owner@havi.vn")
    workspace_id = owner["active_workspace_id"]
    limit = plan_limits.limits_for(Plan.TRIAL).max_seats

    # Chủ đã chiếm một ghế; mời thêm cho tới khi đầy.
    for index in range(limit - 1):
        await _signup(client, email=f"seats-ok-{index}@havi.vn", name=f"Nhân viên {index}")
        invited = await client.post(
            f"/workspaces/{workspace_id}/members",
            json={"email": f"seats-ok-{index}@havi.vn", "role": "marketer"},
            headers=_headers(owner),
        )
        assert invited.status_code == 201, invited.text

    await _signup(client, email="seats-over@havi.vn", name="Người thừa")
    blocked = await client.post(
        f"/workspaces/{workspace_id}/members",
        json={"email": "seats-over@havi.vn", "role": "marketer"},
        headers=_headers(owner),
    )

    assert blocked.status_code == 402, blocked.text
    detail = blocked.json()["detail"]
    assert "Gói Trải Nghiệm" in detail
    assert "Nâng gói" in detail


async def test_moi_lai_nguoi_da_la_thanh_vien_bao_409_khong_bao_het_ghe(
    client: AsyncClient, db_session: AsyncSession
):
    """Kiểm trần **sau** `AlreadyMember`. Mời lại người đã ở trong workspace không
    thêm ghế nào, nên báo "hết ghế" ở đó là nói sai nguyên nhân và đẩy người dùng
    đi nâng gói mà không cần."""
    owner = await _onboard(client, email="seats-dup-owner@havi.vn")
    workspace_id = owner["active_workspace_id"]

    await _signup(client, email="seats-dup@havi.vn", name="Nhân viên A")
    first = await client.post(
        f"/workspaces/{workspace_id}/members",
        json={"email": "seats-dup@havi.vn", "role": "marketer"},
        headers=_headers(owner),
    )
    assert first.status_code == 201, first.text

    again = await client.post(
        f"/workspaces/{workspace_id}/members",
        json={"email": "seats-dup@havi.vn", "role": "marketer"},
        headers=_headers(owner),
    )
    assert again.status_code == 409


async def test_subscription_tra_ve_tran_dang_duoc_cuong_che(client: AsyncClient):
    """Bảng giá và màn Đội ngũ phải đọc con số từ backend, không hardcode: đọc
    "3 người" rồi bị chặn ở người thứ ba là lỗi tệ nhất trong nhóm này."""
    token_pair = await _onboard(client, email="seats-sub@havi.vn")

    response = await client.get("/billing/subscription", headers=_headers(token_pair))

    assert response.status_code == 200, response.text
    body = response.json()
    limits = plan_limits.limits_for(Plan.TRIAL)
    assert body["seats_limit"] == limits.max_seats
    assert body["channels_limit"] == limits.max_channels
    # Chủ workspace đã chiếm một ghế.
    assert body["seats_used"] == 1
    assert body["channels_used"] == 0


async def test_subscription_tra_ve_so_ngay_con_lai_cua_ky(client: AsyncClient):
    """VietQR không có auto-renew: mỗi tháng khách phải chủ động quyết định trả
    tiếp, nên nhắc trước là cơ chế chống churn duy nhất hiện có."""
    token_pair = await _onboard(client, email="seats-due@havi.vn")

    body = (await client.get("/billing/subscription", headers=_headers(token_pair))).json()

    # Workspace mới đang trong kỳ dùng thử nên phải có hạn, và hạn còn ở tương lai.
    assert body["current_period_end"] is not None
    assert body["days_until_due"] is not None
    assert body["days_until_due"] >= 0
