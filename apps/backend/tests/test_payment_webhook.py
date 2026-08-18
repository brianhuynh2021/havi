"""Test cho Cổng thanh toán VietQR & Webhook PayOS/SePay (chuẩn MIT/Stanford)."""

from datetime import UTC, datetime
import hashlib
import hmac
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from adapters.payment.payos_gateway import (
    extract_invoice_code,
    generate_vietqr_checkout,
    verify_payos_signature,
    verify_webhook_hmac,
)
from api.main import create_app
from core.config import Settings
from core.enums import InvoiceStatus, Plan
from domain.models.workspace import Invoice

pytestmark = pytest.mark.anyio


def test_vietqr_checkout_generation():
    settings = Settings(
        vietqr_bank_id="MB",
        vietqr_account_no="0987654321",
        vietqr_account_name="TRUNG TAM CONG NGHE NHAT MINH",
    )
    inv_id = uuid4()
    checkout = generate_vietqr_checkout(
        settings=settings,
        invoice_id=inv_id,
        amount_vnd=299000,
    )
    assert checkout.amount_vnd == 299000
    assert checkout.bank_id == "MB"
    assert checkout.account_no == "0987654321"
    assert "HAVI" in checkout.transfer_content
    assert "https://img.vietqr.io/image/MB-0987654321-compact2.png" in checkout.qr_code_url


def test_extract_invoice_code():
    assert extract_invoice_code("HAVI a1b2c3d4 nap tien") == "a1b2c3d4"
    assert extract_invoice_code("HAVI_94c510b7_PRO") == "94c510b7"
    inv_uuid = str(uuid4())
    assert extract_invoice_code(f"Chuyen khoan HAVI {inv_uuid}") == inv_uuid
    assert extract_invoice_code("Chuyen tien an trua") is None


def test_verify_payos_signature():
    checksum_key = "test_checksum_key_123"
    data = {
        "orderCode": 123456,
        "amount": 299000,
        "description": "HAVI a1b2c3d4",
        "accountNumber": "0987654321",
    }
    # Tạo signature đúng
    import hashlib
    import hmac

    sorted_keys = sorted(data.keys())
    sign_data = "&".join(f"{k}={data[k]}" for k in sorted_keys)
    signature = hmac.new(
        checksum_key.encode("utf-8"), sign_data.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    assert verify_payos_signature(data, signature, checksum_key) is True
    assert verify_payos_signature(data, "wrong_sig", checksum_key) is False


def test_verify_webhook_hmac():
    secret = "secret_key_abc"
    raw_body = b'{"amount": 299000, "content": "HAVI a1b2c3d4"}'
    import hashlib
    import hmac

    sig = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    assert verify_webhook_hmac(raw_body, sig, secret) is True
    assert verify_webhook_hmac(raw_body, f"sha256={sig}", secret) is True
    assert verify_webhook_hmac(raw_body, "wrong_sig", secret) is False


async def test_payos_webhook_success(monkeypatch):
    app = create_app()
    inv_id = uuid4()
    ws_id = uuid4()

    mock_invoice = Invoice(
        id=inv_id,
        workspace_id=ws_id,
        plan=Plan.TIEM_NHO,
        amount_vnd=299000,
        status=InvoiceStatus.PENDING,
        issued_at=datetime.now(UTC),
    )

    mock_billing = MagicMock()
    mock_billing.get_invoice = AsyncMock(return_value=mock_invoice)
    mock_billing.get_invoice_by_code = AsyncMock(return_value=mock_invoice)
    mock_billing.process_payment_success = AsyncMock(return_value=mock_invoice)

    from api import deps
    from core.config import get_settings
    settings = get_settings()
    app.dependency_overrides[deps.get_billing_service] = lambda: mock_billing

    data = {
        "amount": 299000,
        "description": f"HAVI {inv_id}",
        "orderCode": 9999,
        "reference": "FT260817001",
    }
    checksum_key = settings.payos_checksum_key or "test_checksum_key"
    if not settings.payos_checksum_key:
        app.dependency_overrides[deps.get_settings] = lambda: settings

    # Compute valid PayOS HMAC signature
    sorted_keys = sorted(k for k in data.keys() if k != "signature")
    sign_data = "&".join(f"{k}={data[k]}" for k in sorted_keys if data[k] is not None)
    signature = hmac.new(checksum_key.encode("utf-8"), sign_data.encode("utf-8"), hashlib.sha256).hexdigest()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "code": "00",
            "desc": "Success",
            "data": data,
            "signature": signature,
        }
        res = await client.post("/webhooks/payos", json=payload)
        assert res.status_code == 200
        assert res.json()["message"] == "Success"
        mock_billing.process_payment_success.assert_called_once_with(
            invoice_id=inv_id,
            gateway_reference="payos_FT260817001",
            amount_paid_vnd=299000,
        )


async def test_vietqr_webhook_success(monkeypatch):
    app = create_app()
    inv_id = uuid4()
    ws_id = uuid4()

    mock_invoice = Invoice(
        id=inv_id,
        workspace_id=ws_id,
        plan=Plan.TOAN_DIEN,
        amount_vnd=599000,
        status=InvoiceStatus.PENDING,
        issued_at=datetime.now(UTC),
    )

    mock_billing = MagicMock()
    mock_billing.get_invoice = AsyncMock(return_value=mock_invoice)
    mock_billing.process_payment_success = AsyncMock(return_value=mock_invoice)

    from api import deps
    app.dependency_overrides[deps.get_billing_service] = lambda: mock_billing

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "content": f"Chuyen khoan thanh toan HAVI {inv_id}",
            "transferAmount": 599000,
            "referenceCode": "MB_TX_9876",
        }
        res = await client.post("/webhooks/vietqr", json=payload)
        assert res.status_code == 200
        assert res.json()["success"] is True
        mock_billing.process_payment_success.assert_called_once_with(
            invoice_id=inv_id,
            gateway_reference="vietqr_MB_TX_9876",
            amount_paid_vnd=599000,
        )
