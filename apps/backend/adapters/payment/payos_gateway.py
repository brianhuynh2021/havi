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
    account_no = settings.vietqr_account_no or "0987654321"
    account_name = settings.vietqr_account_name or "TRUNG TAM CONG NGHE NHAT MINH"

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


def verify_payos_signature(
    data: dict[str, Any],
    signature: str,
    checksum_key: str,
) -> bool:
    """Xác thực chữ ký HMAC-SHA256 theo chuẩn PayOS.

    PayOS sắp xếp các key theo thứ tự a-z (trừ signature), nối thành chuỗi
    `k1=v1&k2=v2` rồi tính HMAC-SHA256 với checksum_key.
    """
    if not checksum_key or not signature:
        return False

    # Loại bỏ signature ra khỏi dữ liệu cần hash nếu có
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
    match = re.search(r"HAVI[\s_-]*([0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})?|[0-9a-fA-F]{8,32})", transfer_content, re.IGNORECASE)
    if match:
        return match.group(1).lower()
    return None
