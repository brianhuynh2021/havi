"""Router xử lý Webhook thanh toán VietQR (PayOS / SePay).

Bảo vệ bằng chữ ký số HMAC-SHA256:
- PayOS: `verify_payos_signature` trên object data.
- VietQR / SePay: `verify_webhook_hmac` trên raw payload.
"""

import logging
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel

from adapters.payment.payos_gateway import (
    extract_invoice_code,
    verify_payos_signature,
    verify_webhook_hmac,
)
from api.deps import BillingServiceDep, SettingsDep
from application.services.billing_service import (
    DuplicatePaymentReferenceError,
    InvoiceInvalidStatusError,
    InvoiceNotFound,
    UnderpaidInvoiceError,
)

logger = logging.getLogger("havi.payment_webhook")

router = APIRouter(prefix="/webhooks", tags=["payment_webhooks"])


class PayOSWebhookRequest(BaseModel):
    code: str | None = None
    desc: str | None = None
    data: dict[str, Any] = {}
    signature: str = ""


@router.post("/payos")
async def payos_webhook(
    payload: PayOSWebhookRequest,
    billing_service: BillingServiceDep,
    settings: SettingsDep,
) -> dict[str, Any]:
    """Nhận webhook từ PayOS khi khách quét VietQR thanh toán thành công."""
    data = payload.data or {}
    signature = payload.signature

    # Ping không chữ ký chỉ được dùng ở local. Ngoài local, mọi request đều phải
    # được xác thực như một webhook thật.
    if not data and not signature and settings.is_local:
        logger.info("Nhận ping xác nhận webhook URL từ PayOS")
        return {"success": True, "message": "Webhook verified"}

    # 2. Bắt buộc xác thực chữ ký số ở mọi môi trường không phải local.
    if settings.payos_checksum_key or not settings.is_local:
        if not signature:
            logger.warning("PayOS Webhook thiếu chữ ký số")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing PayOS webhook signature",
            )
        valid = verify_payos_signature(data, signature, settings.payos_checksum_key or "")
        if not valid:
            logger.warning("PayOS Webhook chữ ký không hợp lệ")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid PayOS webhook signature",
            )

    description = str(data.get("description", ""))
    order_code = str(data.get("orderCode", ""))
    amount = int(data.get("amount", 0))
    currency = str(data.get("currency") or "VND").upper()
    reference = str(data.get("reference") or "").strip()

    if str(payload.code or "").upper() != "00":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PayOS webhook is not a successful payment",
        )

    if not reference:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PayOS webhook is missing a unique transaction reference",
        )

    # 3. Tìm mã hoá đơn từ description (ví dụ: HAVI a1b2c3d4)
    code = extract_invoice_code(description) or extract_invoice_code(order_code)
    if not code:
        logger.warning(
            "Không tìm thấy mã hoá đơn HAVI trong description='%s', orderCode='%s'",
            description,
            order_code,
        )
        return {"error": 0, "message": "Ignored: No Havi invoice code", "data": None}

    # 4. Kích hoạt hoá đơn và gia hạn gói sau khi đối soát
    try:
        invoice = await billing_service.get_invoice_by_code(code=code)
        if invoice is None:
            logger.error("Không tìm thấy hoá đơn tương ứng với code=%s", code)
            return {"error": 1, "message": "Invoice not found", "data": None}

        await billing_service.process_payment_success(
            invoice_id=invoice.id,
            gateway_reference=f"payos_{reference}",
            amount_paid_vnd=amount,
            currency=currency,
        )
        logger.info("Đã kích hoạt thành công hoá đơn %s từ PayOS", invoice.id)
        return {"error": 0, "message": "Success", "data": None}

    except InvoiceNotFound:
        logger.warning("Invoice %s không tồn tại", code)
        return {"error": 1, "message": "Invoice not found", "data": None}
    except (UnderpaidInvoiceError, DuplicatePaymentReferenceError) as exc:
        logger.warning("PayOS webhook từ chối kích hoạt: %s", exc)
        return {"error": 1, "message": str(exc), "data": None}
    except InvoiceInvalidStatusError as exc:
        logger.warning("PayOS webhook trạng thái không hợp lệ: %s", exc)
        return {"error": 1, "message": str(exc), "data": None}
    except Exception as exc:
        logger.error("Lỗi khi xử lý PayOS webhook: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Payment webhook processing failed",
        ) from exc


@router.post("/vietqr")
async def vietqr_generic_webhook(
    request: Request,
    billing_service: BillingServiceDep,
    settings: SettingsDep,
    x_signature: str | None = Header(None, alias="X-Signature"),
) -> dict[str, Any]:
    """Webhook nhận biến động số dư VietQR / SePay từ tài khoản ngân hàng."""
    raw_body = await request.body()

    if settings.payment_webhook_secret or not settings.is_local:
        if not x_signature:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing Webhook HMAC signature",
            )
        if not verify_webhook_hmac(raw_body, x_signature, settings.payment_webhook_secret or ""):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Webhook HMAC signature",
            )

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        ) from None

    # SePay / VietQR format: { "content": "HAVI a1b2c3d4...", "transferAmount": 299000, "referenceCode": "MB123" }
    content = str(body.get("content") or body.get("description") or "")
    amount = int(body.get("transferAmount") or body.get("amount") or 0)
    ref_code = str(body.get("referenceCode") or body.get("id") or "").strip()
    currency = str(body.get("currency") or "VND").upper()
    transfer_type = str(body.get("transferType") or "in").lower()
    if transfer_type not in {"in", "credit"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook is not an incoming successful transfer",
        )
    if not ref_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook is missing a unique transaction reference",
        )

    code = extract_invoice_code(content)
    if not code:
        return {"success": True, "message": "Ignored: No invoice code found"}

    try:
        invoice = await billing_service.get_invoice_by_code(code=code)
        if invoice is None:
            return {"success": False, "message": "Invoice not found"}

        await billing_service.process_payment_success(
            invoice_id=invoice.id,
            gateway_reference=f"vietqr_{ref_code}",
            amount_paid_vnd=amount,
            currency=currency,
        )
        return {"success": True, "message": "Subscription activated"}
    except (
        DuplicatePaymentReferenceError,
        UnderpaidInvoiceError,
        InvoiceInvalidStatusError,
    ) as exc:
        logger.warning("VietQR webhook từ chối kích hoạt: %s", exc)
        return {"success": False, "message": str(exc)}
    except Exception as exc:
        logger.error("Lỗi xử lý VietQR webhook: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Payment webhook processing failed",
        ) from exc
