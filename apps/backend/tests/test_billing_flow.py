"""Test Billing Service & API routes (/billing/subscription, /billing/invoices, /billing/plan)."""

from datetime import UTC, datetime

import pytest
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


async def _billing_service(db_session):
    from adapters.persistence.billing_repository import BillingRepository
    from adapters.persistence.event_log_repository import EventLogRepository
    from adapters.persistence.workspace_repository import WorkspaceRepository
    from application.services.billing_service import BillingService

    return BillingService(
        billing=BillingRepository(db_session),
        workspaces=WorkspaceRepository(db_session),
        events=EventLogRepository(db_session),
    )


async def test_payment_requires_exact_amount_and_vnd(client: AsyncClient, db_session):
    from application.services.billing_service import UnderpaidInvoiceError

    tokens = await _onboard(client, email="billing_exact_match@havi.vn")
    await client.post(
        "/billing/plan",
        json={"plan": "tiem_nho"},
        headers=_headers(tokens),
    )
    invoices = (await client.get("/billing/invoices", headers=_headers(tokens))).json()
    invoice_id = invoices[0]["id"]
    service = await _billing_service(db_session)

    with pytest.raises(UnderpaidInvoiceError):
        await service.process_payment_success(
            invoice_id=invoice_id,
            gateway_reference="payos_overpaid",
            amount_paid_vnd=invoices[0]["amount_vnd"] + 1,
        )
    with pytest.raises(UnderpaidInvoiceError):
        await service.process_payment_success(
            invoice_id=invoice_id,
            gateway_reference="payos_wrong_currency",
            amount_paid_vnd=invoices[0]["amount_vnd"],
            currency="USD",
        )


async def test_payment_replay_is_idempotent_and_reference_is_unique(
    client: AsyncClient, db_session
):
    from application.services.billing_service import DuplicatePaymentReferenceError

    tokens = await _onboard(client, email="billing_replay@havi.vn")
    for _ in range(2):
        await client.post(
            "/billing/plan",
            json={"plan": "tiem_nho"},
            headers=_headers(tokens),
        )
    invoices = (await client.get("/billing/invoices", headers=_headers(tokens))).json()
    first, second = invoices[0], invoices[1]
    service = await _billing_service(db_session)
    paid_at = datetime(2026, 8, 23, tzinfo=UTC)

    paid = await service.process_payment_success(
        invoice_id=first["id"],
        gateway_reference="payos_unique_reference",
        amount_paid_vnd=first["amount_vnd"],
        now=paid_at,
    )
    first_paid_until = paid_at.replace()  # giữ mốc gọi để kiểm replay bên dưới
    replayed = await service.process_payment_success(
        invoice_id=first["id"],
        gateway_reference="payos_unique_reference",
        amount_paid_vnd=first["amount_vnd"],
        now=paid_at,
    )
    assert replayed.id == paid.id

    with pytest.raises(DuplicatePaymentReferenceError):
        await service.process_payment_success(
            invoice_id=second["id"],
            gateway_reference="payos_unique_reference",
            amount_paid_vnd=second["amount_vnd"],
            now=first_paid_until,
        )


def test_past_due_scheduled_publish_grace_policy():
    """Chính sách hết hạn (b):
    - Gói ACTIVE/TRIALING: Cho phép xuất bản.
    - Gói PAST_DUE: Cho phép xuất bản bài đã lên lịch trong 7 ngày tới.
    - Quá 7 ngày: Chặn xuất bản.
    """
    from datetime import timedelta
    from domain.policies.subscription import (
        SubscriptionState,
        can_publish_scheduled_post,
    )

    now = datetime(2026, 9, 2, 10, 0, tzinfo=UTC)
    expired_end = datetime(2026, 9, 1, 0, 0, tzinfo=UTC)

    # 1. Active / Trialing -> True
    active_sub = SubscriptionState(
        plan=Plan.TIEM_NHO,
        status=SubscriptionStatus.ACTIVE,
        current_period_end=now + timedelta(days=20),
    )
    assert can_publish_scheduled_post(
        subscription_state=active_sub,
        scheduled_at=now + timedelta(days=10),
        now=now,
    )

    # 2. Past due nhưng bài lên lịch trong vòng 7 ngày kể từ lúc hết hạn -> True
    past_due_sub = SubscriptionState(
        plan=Plan.TIEM_NHO,
        status=SubscriptionStatus.PAST_DUE,
        current_period_end=expired_end,
    )
    scheduled_within_7d = expired_end + timedelta(days=3)
    assert can_publish_scheduled_post(
        subscription_state=past_due_sub,
        scheduled_at=scheduled_within_7d,
        now=now,
    )

    # 3. Past due nhưng bài lên lịch sau 7 ngày -> False
    scheduled_after_7d = expired_end + timedelta(days=8)
    assert not can_publish_scheduled_post(
        subscription_state=past_due_sub,
        scheduled_at=scheduled_after_7d,
        now=now,
    )
