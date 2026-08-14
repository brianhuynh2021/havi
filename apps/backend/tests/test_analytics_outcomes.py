"""`/analytics/summary` phải đếm từ dữ liệu thật.

Trước đây endpoint này trả 0 cứng cho `price_inquiries`, `won_leads`,
`returning_customers`, `new_leads` và `lead_won_rate` — đúng là không bịa số,
nhưng cũng có nghĩa là màn hình Báo cáo không chứng minh được kết quả mà Havi
bán. Test ở đây khoá lại: mỗi con số phải đổi khi dữ liệu nguồn đổi, và phải
đứng yên khi dữ liệu thuộc workspace khác.
"""

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from domain.policies.scheduling import VIETNAM_TZ


async def _onboard(client: AsyncClient, email: str) -> dict:
    signup = await client.post(
        "/auth/sign-up",
        json={"name": "Chị Mai", "email": email, "password": "matkhau123"},
    )
    assert signup.status_code == 201, signup.text
    tokens = signup.json()

    create = await client.post(
        "/workspaces",
        json={"name": "Tiệm Mai Q7", "industry": "spa"},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert create.status_code == 201, create.text

    refreshed = await client.post(
        "/auth/refresh",
        headers={"Authorization": f"Bearer {tokens['refresh_token']}"},
    )
    return {"Authorization": f"Bearer {refreshed.json()['access_token']}"}


async def _create_lead(
    client: AsyncClient, headers: dict, *, name: str, phone: str | None = None
) -> str:
    resp = await client.post(
        "/leads",
        json={"name": name, "phone": phone, "source": "fanpage", "stage": "new"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _summary(client: AsyncClient, headers: dict) -> dict:
    now_vn = datetime.now(VIETNAM_TZ).date()
    params = {
        "start": (now_vn - timedelta(days=7)).isoformat(),
        "end": (now_vn + timedelta(days=1)).isoformat(),
    }
    resp = await client.get("/analytics/summary", params=params, headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()



@pytest.mark.asyncio
async def test_empty_workspace_reports_zero(client: AsyncClient):
    headers = await _onboard(client, "outcomes.empty@havi.vn")
    data = await _summary(client, headers)

    assert data["new_leads"] == 0
    assert data["price_inquiries"] == 0
    assert data["lead_won_rate"] == 0


@pytest.mark.asyncio
async def test_new_leads_counted(client: AsyncClient):
    headers = await _onboard(client, "outcomes.leads@havi.vn")
    await _create_lead(client, headers, name="Chị Lan", phone="0901234567")
    await _create_lead(client, headers, name="Chị Hoa", phone="0907654321")

    assert (await _summary(client, headers))["new_leads"] == 2


@pytest.mark.asyncio
async def test_won_leads_and_win_rate(client: AsyncClient):
    headers = await _onboard(client, "outcomes.won@havi.vn")
    won_id = await _create_lead(client, headers, name="Chị Lan", phone="0901111111")
    lost_id = await _create_lead(client, headers, name="Chị Hoa", phone="0902222222")
    await _create_lead(client, headers, name="Chị Mai", phone="0903333333")

    await client.patch(f"/leads/{won_id}", json={"stage": "won"}, headers=headers)
    await client.patch(f"/leads/{lost_id}", json={"stage": "lost"}, headers=headers)

    data = await _summary(client, headers)
    assert data["new_leads"] == 3
    assert data["won_leads"] == 1
    # Cái tên phải nói đúng thứ nó đo: không có nguồn check-in nào trong hệ thống
    # nên `/analytics/summary` không được phơi ra một trường tên `walk_ins`.
    assert "walk_ins" not in data
    # Tỉ lệ chốt tính trên lead đã có kết luận (won + lost), không tính lead còn
    # đang mở — lead mới tạo hôm nay chưa thua thì không được kéo tỉ lệ xuống.
    assert data["lead_won_rate"] == 0.5


@pytest.mark.asyncio
async def test_inbox_items_counted_as_price_inquiries(client: AsyncClient):
    headers = await _onboard(client, "outcomes.inbox@havi.vn")
    for i in range(3):
        resp = await client.post(
            "/webhooks/dev/simulate",
            json={"content": f"Bao nhiêu tiền ạ {i}", "external_message_id": f"m{i}"},
            headers=headers,
        )
        assert resp.status_code == 200, resp.text

    assert (await _summary(client, headers))["price_inquiries"] == 3


@pytest.mark.asyncio
async def test_duplicate_webhook_does_not_inflate_inquiries(client: AsyncClient):
    headers = await _onboard(client, "outcomes.dedupe@havi.vn")
    body = {"content": "Giá bao nhiêu ạ", "external_message_id": "same-mid"}
    await client.post("/webhooks/dev/simulate", json=body, headers=headers)
    await client.post("/webhooks/dev/simulate", json=body, headers=headers)

    assert (await _summary(client, headers))["price_inquiries"] == 1


@pytest.mark.asyncio
async def test_other_workspace_data_never_leaks(client: AsyncClient):
    theirs = await _onboard(client, "outcomes.tenant.a@havi.vn")
    await _create_lead(client, theirs, name="Khách của tiệm A", phone="0900000001")
    await client.post(
        "/webhooks/dev/simulate",
        json={"content": "Hỏi giá tiệm A"},
        headers=theirs,
    )

    mine = await _onboard(client, "outcomes.tenant.b@havi.vn")
    data = await _summary(client, mine)

    assert data["new_leads"] == 0
    assert data["price_inquiries"] == 0


@pytest.mark.asyncio
async def test_change_vs_previous_period_is_present_and_finite(client: AsyncClient):
    headers = await _onboard(client, "outcomes.change@havi.vn")
    await _create_lead(client, headers, name="Chị Lan", phone="0904444444")

    change = (await _summary(client, headers))["change_vs_previous_period"]

    assert "new_leads" in change
    # Kỳ trước rỗng thì không có phần trăm nào đúng — trả 0 chứ không +100%.
    assert change["new_leads"] == 0
