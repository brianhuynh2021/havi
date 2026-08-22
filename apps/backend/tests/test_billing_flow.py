"""Test Billing Service & API routes (/billing/subscription, /billing/invoices, /billing/plan)."""

from httpx import AsyncClient

from core.enums import Plan, SubscriptionStatus


async def _onboard(client: AsyncClient, *, email: str) -> dict:
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
    return refreshed.json()


def _headers(tokens: dict) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def test_get_subscription_initial_trial(client: AsyncClient):
    tokens = await _onboard(client, email="billing_trial@havi.vn")
    res = await client.get("/billing/subscription", headers=_headers(tokens))
    assert res.status_code == 200, res.text

    data = res.json()
    assert data["plan"] == Plan.TRIAL
    assert data["status"] == SubscriptionStatus.TRIALING
    assert data["token_quota_limit"] > 0
    assert data["token_quota_used"] == 0
    assert data["current_period_end"] is not None


async def test_list_invoices_empty_on_creation(client: AsyncClient):
    tokens = await _onboard(client, email="billing_invoices_empty@havi.vn")
    res = await client.get("/billing/invoices", headers=_headers(tokens))
    assert res.status_code == 200, res.text

    invoices = res.json()
    assert invoices == []


async def test_change_plan_success_issues_invoice(client: AsyncClient):
    tokens = await _onboard(client, email="billing_change_plan@havi.vn")

    # Request plan change to tiem_nho -> creates pending invoice without premature plan grant
    res = await client.post(
        "/billing/plan",
        json={"plan": "tiem_nho"},
        headers=_headers(tokens),
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["plan"] == Plan.TRIAL
    assert data["status"] == SubscriptionStatus.TRIALING

    # Check invoice created with PENDING status
    inv_res = await client.get("/billing/invoices", headers=_headers(tokens))
    assert inv_res.status_code == 200, inv_res.text
    invoices = inv_res.json()
    assert len(invoices) == 1
    assert invoices[0]["plan"] == Plan.TIEM_NHO
    assert invoices[0]["amount_vnd"] == 189_000
    assert invoices[0]["status"] == "pending"


async def test_change_plan_same_plan_rejected(client: AsyncClient):
    tokens = await _onboard(client, email="billing_same_plan@havi.vn")
    res = await client.post(
        "/billing/plan",
        json={"plan": "trial"},
        headers=_headers(tokens),
    )
    assert res.status_code == 400, res.text
    assert "đang ở gói trial" in res.json()["detail"]


async def test_change_plan_downgrade_to_trial_rejected(client: AsyncClient):
    tokens = await _onboard(client, email="billing_downgrade@havi.vn")

    # Upgrade first
    await client.post(
        "/billing/plan",
        json={"plan": "tiem_nho"},
        headers=_headers(tokens),
    )

    # Downgrade back to trial
    res = await client.post(
        "/billing/plan",
        json={"plan": "trial"},
        headers=_headers(tokens),
    )
    assert res.status_code == 400, res.text
    detail = res.json()["detail"]
    assert "gói trial" in detail or "Không quay lại gói dùng thử" in detail


async def test_billing_tenant_isolation(client: AsyncClient):
    tokens_a = await _onboard(client, email="billing_owner_a@havi.vn")
    tokens_b = await _onboard(client, email="billing_owner_b@havi.vn")

    # Workspace A upgrades
    await client.post(
        "/billing/plan",
        json={"plan": "tiem_nho"},
        headers=_headers(tokens_a),
    )

    # Workspace B checks subscription and invoices
    res_b_sub = await client.get("/billing/subscription", headers=_headers(tokens_b))
    assert res_b_sub.json()["plan"] == Plan.TRIAL

    res_b_inv = await client.get("/billing/invoices", headers=_headers(tokens_b))
    assert res_b_inv.json() == []
