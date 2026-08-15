"""Domain policy cho Closed-Loop Sales & POS Attribution (Station 5).

Quy tắc:
1. Chuẩn hóa số điện thoại khách hàng VN (E.164 hoặc 09xxxxxxxxx).
2. Định dạng ghi chú đơn hàng từ POS (KiotViet, Sapo, Haravan, Pos365).
3. Phân bổ doanh thu cho Lead và cập nhật stage WON.
"""

from dataclasses import dataclass, field
from datetime import datetime

from domain.policies.phone import normalize_vietnamese_phone


@dataclass(frozen=True)
class PosOrder:
    order_id: str
    customer_name: str
    customer_phone: str | None
    amount_vnd: int
    source: str = "pos"
    items: list[str] = field(default_factory=list)
    timestamp: datetime | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "PosOrder":
        raw_phone = data.get("customer_phone") or data.get("phone")
        phone = None
        if raw_phone:
            try:
                phone = normalize_vietnamese_phone(str(raw_phone))
            except Exception:
                phone = str(raw_phone).strip()

        amount = int(data.get("amount_vnd") or data.get("amount") or data.get("total") or 0)
        items = data.get("items") or []
        if isinstance(items, str):
            items = [items]

        return cls(
            order_id=str(data.get("order_id") or data.get("id") or ""),
            customer_name=str(data.get("customer_name") or data.get("name") or "Khách tại quầy"),
            customer_phone=phone,
            amount_vnd=amount,
            source=str(data.get("source") or "pos").lower(),
            items=items,
        )


def format_pos_notes(order: PosOrder) -> str:
    items_summary = f" ({', '.join(order.items)})" if order.items else ""
    return (
        f"[{order.source.upper()}] Đơn hàng #{order.order_id}: "
        f"{order.amount_vnd:,.0f}đ{items_summary}"
    )
