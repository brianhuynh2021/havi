"""Unit tests cho domain policy Sales Attribution & PosOrder."""

from domain.policies.sales_attribution import PosOrder, format_pos_notes


def test_pos_order_parsing_and_phone_normalization():
    data = {
        "order_id": "ORD-12345",
        "customer_name": "Nguyễn Thị Hoa",
        "customer_phone": "0912 345 678",
        "amount_vnd": "450000",
        "source": "KiotViet",
        "items": ["Chăm sóc da mặt", "Mặt nạ vàng 24k"],
    }
    order = PosOrder.from_dict(data)
    assert order.order_id == "ORD-12345"
    assert order.customer_name == "Nguyễn Thị Hoa"
    assert order.customer_phone == "+84912345678"
    assert order.amount_vnd == 450000
    assert order.source == "kiotviet"
    assert len(order.items) == 2


def test_format_pos_notes():
    order = PosOrder(
        order_id="POS-999",
        customer_name="Trần Văn Nam",
        customer_phone="+84988776655",
        amount_vnd=1200000,
        source="sapo",
        items=["Gói combo trị mụn", "Serum tế bào gốc"],
    )
    notes = format_pos_notes(order)
    assert "[SAPO]" in notes
    assert "Đơn hàng #POS-999" in notes
    assert "1,200,000đ" in notes
    assert "Gói combo trị mụn" in notes
