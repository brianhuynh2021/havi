"""Cổng thanh toán tự động VietQR (PayOS / SePay).

Hỗ trợ:
1. Tạo mã VietQR chuẩn EMVCo hiển thị ảnh QR code kèm số tiền và nội dung chuyển khoản.
2. Kiểm tra chữ ký số HMAC-SHA256 bảo vệ Webhook chống giả mạo số dư.
3. Trích xuất mã hoá đơn từ nội dung chuyển khoản ngân hàng (cú pháp: HAVI_<INVOICE_ID>).
"""

import hashlib
import hmac
import logging
import re
import urllib.parse
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from core.config import Settings

logger = logging.getLogger("havi.payment")


@dataclass
class VietQRCheckout:
    invoice_id: str
    amount_vnd: int
    transfer_content: str
    bank_id: str
    account_no: str
    account_name: str
    qr_code_url: str


def generate_vietqr_checkout(
    *,
    settings: Settings,
    invoice_id: UUID,
    amount_vnd: int,
    custom_content: str | None = None,
) -> VietQRCheckout:
    """Tạo thông tin thanh toán VietQR động."""
    invoice_id_str = str(invoice_id)
    # Lấy 8 ký tự đầu hoặc full uuid để tiện cho khách nhập trên app ngân hàng
    transfer_content = custom_content or f"HAVI {invoice_id_str.replace('-', '')[:8]}"

    bank_id = settings.vietqr_bank_id or "MB"
    account_no = settings.vietqr_account_no or "0984883750"
    account_name = settings.vietqr_account_name or "NGUYEN THANH HUYNH"

    encoded_name = urllib.parse.quote(account_name)
    encoded_desc = urllib.parse.quote(transfer_content)

    # API VietQR chuẩn tạo ảnh QR chất lượng cao
    qr_url = (
        f"https://img.vietqr.io/image/{bank_id}-{account_no}-compact2.png"
        f"?amount={amount_vnd}&addInfo={encoded_desc}&accountName={encoded_name}"
    )

    return VietQRCheckout(
        invoice_id=invoice_id_str,
        amount_vnd=amount_vnd,
        transfer_content=transfer_content,
        bank_id=bank_id,
        account_no=account_no,
        account_name=account_name,
        qr_code_url=qr_url,
    )


class PaymentGatewayError(Exception):
    """Lỗi cổng thanh toán PayOS gián đoạn hoặc cấu hình không hợp lệ."""


async def create_payos_payment_link(
    *,
    settings: Settings,
    invoice_id: UUID,
    amount_vnd: int,
    custom_content: str | None = None,
) -> VietQRCheckout:
    """Tạo link thanh toán chính thức qua PayOS SDK kèm Fallback VietQR chuẩn."""
    from datetime import UTC, datetime

    from payos import AsyncPayOS
    from payos.types.v2.payment_requests.payment_requests import CreatePaymentLinkRequest

    invoice_id_str = str(invoice_id)
    clean_id = invoice_id_str.replace("-", "")[:8]
    description = custom_content or f"HAVI {clean_id}"

    order_code = int(
        f"{int(datetime.now(UTC).timestamp()) % 1000000}{int(invoice_id.hex[:4], 16) % 10000:04d}"
    )
    ret_url = f"{settings.web_base_url}/billing"
    can_url = f"{settings.web_base_url}/billing"

    if settings.payos_client_id and settings.payos_api_key and settings.payos_checksum_key:
        try:
            payos_client = AsyncPayOS(
                client_id=settings.payos_client_id,
                api_key=settings.payos_api_key,
                checksum_key=settings.payos_checksum_key,
            )
            req = CreatePaymentLinkRequest(
                order_code=order_code,
                amount=amount_vnd,
                description=description,
                return_url=ret_url,
                cancel_url=can_url,
            )
            res = await payos_client.payment_requests.create(req)
            account_no = res.account_number or settings.vietqr_account_no or "0984883750"
            account_name = res.account_name or settings.vietqr_account_name or "NGUYEN THANH HUYNH"
            bin_code = res.bin or "970422"
            qr_url = (
                f"https://img.vietqr.io/image/{bin_code}-{account_no}-compact2.png"
                f"?amount={amount_vnd}&addInfo={urllib.parse.quote(description)}&accountName={urllib.parse.quote(account_name)}"
            )
            logger.info(
                "Đã tạo PayOS payment link thành công: orderCode=%s invoice=%s account=%s",
                order_code,
                invoice_id,
                account_no,
            )
            return VietQRCheckout(
                invoice_id=invoice_id_str,
                amount_vnd=amount_vnd,
                transfer_content=description,
                bank_id=settings.vietqr_bank_id or "MB",
                account_no=account_no,
                account_name=account_name,
                qr_code_url=qr_url,
            )
        except Exception as exc:
            logger.error("Lỗi khi kết nối PayOS SDK: %s", exc)
            if settings.env == "production":
                raise PaymentGatewayError(
                    "Cổng thanh toán PayOS tạm thời gián đoạn. Vui lòng thử lại sau giây lát."
                ) from exc

    if settings.env == "production":
        raise PaymentGatewayError(
            "Cổng thanh toán PayOS chưa được cấu hình đầy đủ trên môi trường Production."
        )

    return generate_vietqr_checkout(
        settings=settings,
        invoice_id=invoice_id,
        amount_vnd=amount_vnd,
        custom_content=description,
    )


def verify_payos_signature(
    data: dict[str, Any],
    signature: str,
    checksum_key: str,
) -> bool:
    """Xác thực chữ ký HMAC-SHA256 theo chuẩn PayOS SDK."""
    if not checksum_key or not signature:
        return False

    try:
        from payos import PayOS

        p = PayOS(client_id="dummy", api_key="dummy", checksum_key=checksum_key)
        payload = {"data": data, "signature": signature}
        p.webhooks.verify(payload)
        return True
    except Exception:
        # Fallback manual calculation
        sorted_keys = sorted(k for k in data.keys() if k != "signature")
        sign_data = "&".join(f"{k}={data[k]}" for k in sorted_keys if data[k] is not None)
        computed = hmac.new(
            checksum_key.encode("utf-8"),
            sign_data.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(computed.lower(), signature.lower())


def verify_webhook_hmac(
    raw_body: bytes,
    signature_header: str,
    secret_key: str,
) -> bool:
    """Xác thực chữ ký HMAC-SHA256 cho raw body webhook tổng quát (SePay, Generic Webhooks)."""
    if not secret_key or not signature_header:
        return False

    computed = hmac.new(
        secret_key.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    # Hỗ trợ cả hex thuần và sha256=hex
    expected = signature_header.removeprefix("sha256=")
    return hmac.compare_digest(computed.lower(), expected.lower())


def extract_invoice_code(transfer_content: str) -> str | None:
    """Trích xuất mã hoá đơn từ nội dung chuyển khoản ngân hàng.

    Ví dụ:
      - "HAVI a1b2c3d4" -> "a1b2c3d4"
      - "HAVI_a1b2c3d4_NAPTIEN" -> "a1b2c3d4"
      - "CT tu 098... HAVIa1b2c3d4..." -> "a1b2c3d4"
    """
    if not transfer_content:
        return None

    # Tìm mẫu HAVI kèm 8 ký tự hex hoặc UUID
    match = re.search(
        r"HAVI[\s_-]*([0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})?|[0-9a-fA-F]{8,32})",
        transfer_content,
        re.IGNORECASE,
    )
    if match:
        return match.group(1).lower()
    return None
