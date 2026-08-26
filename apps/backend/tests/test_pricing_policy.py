"""Đơn giá LLM — ưu tiên model, và sai số phải nghiêng về phía đắt.

Không test giá cụ thể là bao nhiêu: bảng giá sẽ được cập nhật, và test bám con
số thì mỗi lần đổi giá lại có người sửa test cho qua. Test ở đây khoá *quy tắc*.
"""

from datetime import UTC, date, datetime, timedelta

from domain.policies import pricing


def test_model_thang_provider_khi_biet_ca_hai():
    """Cùng provider `anthropic`, Haiku phải rẻ hơn Sonnet.

    Đây là lý do tồn tại của cột `model`: tính theo provider là lấy giá của model
    mình đoán đang chạy, trong khi model thật do biến môi trường quyết định.
    """
    haiku = pricing.cost_vnd(
        tokens_in=10_000, tokens_out=10_000, model="claude-haiku-4-5", provider="anthropic"
    )
    sonnet = pricing.cost_vnd(
        tokens_in=10_000, tokens_out=10_000, model="claude-sonnet-4-5", provider="anthropic"
    )
    assert haiku < sonnet


def test_output_dat_hon_input():
    """Gộp hai chiều thành một đơn giá trung bình sẽ che mất chênh lệch này."""
    heavy_in = pricing.cost_vnd(
        tokens_in=10_000, tokens_out=0, model="gpt-4o-mini", provider="openai"
    )
    heavy_out = pricing.cost_vnd(
        tokens_in=0, tokens_out=10_000, model="gpt-4o-mini", provider="openai"
    )
    assert heavy_out > heavy_in


def test_khong_biet_model_thi_lay_gia_dat_nhat_cua_provider():
    """Dòng log cũ không có `model`. Đoán rẻ thì báo cáo đẹp và sai."""
    fallback = pricing.cost_vnd(
        tokens_in=10_000, tokens_out=10_000, model=None, provider="anthropic"
    )
    cheapest = pricing.cost_vnd(
        tokens_in=10_000, tokens_out=10_000, model="claude-3-5-haiku-latest", provider="anthropic"
    )
    assert fallback > cheapest


def test_model_la_khong_roi_ve_gia_provider():
    """Đổi `HAVI_*_MODEL` sang model chưa có trong bảng thì vẫn ra số thận trọng,
    không ra 0 — một chi phí bằng 0 đọc như "miễn phí"."""
    unknown_model = pricing.cost_vnd(
        tokens_in=10_000, tokens_out=10_000, model="gemini-9.9-experimental", provider="gemini"
    )
    provider_only = pricing.cost_vnd(
        tokens_in=10_000, tokens_out=10_000, model=None, provider="gemini"
    )
    assert unknown_model == provider_only > 0


def test_khong_biet_gi_ca_van_khong_tra_ve_khong():
    assert pricing.cost_vnd(tokens_in=1_000, tokens_out=1_000, model=None, provider=None) > 0


def test_khong_token_thi_khong_ton_tien():
    assert pricing.cost_vnd(tokens_in=0, tokens_out=0, model=None, provider=None) == 0


def test_khong_lam_tron_tung_dong():
    """Một lượt gọi lẻ có thể tốn dưới một đồng. Làm tròn từng dòng rồi mới cộng
    sẽ nuốt mất phần lớn chi phí khi cộng hàng nghìn dòng."""
    tiny = pricing.cost_vnd(tokens_in=1, tokens_out=1, model="gemini-1.5-flash", provider="gemini")
    assert 0 < tiny < 1


def test_bang_gia_moi_thi_khong_stale_va_qua_han_thi_stale():
    assert pricing.is_stale(now=datetime.combine(pricing.AS_OF, datetime.min.time(), UTC)) is False

    qua_han = pricing.AS_OF + timedelta(days=pricing.STALE_AFTER_DAYS + 1)
    assert pricing.is_stale(now=datetime.combine(qua_han, datetime.min.time(), UTC)) is True


def test_ty_gia_va_bang_gia_deu_co_ngay():
    """Con số tiền không có ngày là một phỏng đoán trông như số liệu."""
    assert isinstance(pricing.AS_OF, date)
    assert isinstance(pricing.USD_TO_VND_AS_OF, date)
