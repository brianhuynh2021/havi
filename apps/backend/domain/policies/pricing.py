"""Đơn giá LLM — quy token đã tiêu thành tiền, để trả lời một câu hỏi kinh doanh.

Câu hỏi đó là: **một workspace tốn bao nhiêu mỗi tháng, so với giá gói nó đang
trả?** Không trả lời được thì mỗi khách hàng mới có thể là một khoản lỗ, và
không ai biết cho tới lúc nhìn hoá đơn provider.

Vì sao là chính sách miền chứ không nằm trong adapter
-----------------------------------------------------
Bảng giá này trước nằm trong `adapters/persistence/event_log_repository.py` —
tức là một quyết định kinh doanh nằm trong tầng đọc ghi database. `core/events.py`
thì đã trỏ tới đúng file này từ trước. Giá thay đổi độc lập với cách lưu trữ, và
sẽ được sửa bởi người nghĩ về biên lợi nhuận chứ không phải người sửa query.

Tính theo *model*, không theo *provider*
-----------------------------------------
Trong cùng một nhà cung cấp, hai model chênh nhau tới hơn mười lần đơn giá. Tính
theo provider là lấy giá của model mình *đoán* rằng đang chạy, trong khi model
thật do biến môi trường quyết định (`HAVI_ANTHROPIC_MODEL`, `HAVI_OPENAI_MODEL`,
`HAVI_GEMINI_MODEL`). Đổi biến môi trường một cái là mọi con số sai âm thầm.

Dòng `event_log` ghi trước khi có cột `model` thì không có model để tra. Những
dòng đó rơi về `_PROVIDER_FALLBACK` — **cố ý lấy giá cao nhất trong nhóm**, để
sai số nghiêng về phía "đắt hơn tưởng". Một ước lượng chi phí sai theo hướng lạc
quan là loại sai nguy hiểm: nó khiến người ta giữ nguyên bảng giá đang lỗ.

Số liệu này hết hạn
-------------------
`AS_OF` và `USD_TO_VND_AS_OF` là ngày của lần cập nhật cuối. Cả đơn giá LLM lẫn
tỷ giá đều trôi. Một bảng giá cũ vẫn cho ra con số trông rất chính xác, nên
`is_stale()` tồn tại để chỗ dùng có thể nói rõ "đây là phỏng đoán" thay vì hiện
một con số như thể nó là sự thật.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime

#: Ngày cập nhật đơn giá lần cuối. Sửa giá thì sửa luôn ngày này.
AS_OF = date(2026, 8, 26)

#: Tỷ giá quy đổi, kèm ngày riêng vì nó trôi theo nhịp khác đơn giá LLM.
USD_TO_VND = 26_000
USD_TO_VND_AS_OF = date(2026, 8, 26)

#: Quá mốc này thì con số là phỏng đoán, không phải số liệu.
STALE_AFTER_DAYS = 120


@dataclass(frozen=True)
class ModelRate:
    """Đơn giá USD cho mỗi 1 triệu token, tách chiều vào và chiều ra.

    Tách hai chiều là bắt buộc, không phải để cho đẹp: output thường đắt gấp
    3–5 lần input. Gộp lại thành một đơn giá trung bình thì hai workspace tiêu
    cùng một lượng token có thể chênh nhau vài lần chi phí thật.
    """

    input_usd_per_mtok: float
    output_usd_per_mtok: float


#: Đơn giá theo tên model. Khoá là chuỗi model mà provider trả về trong response,
#: khớp với giá trị nằm ở `HAVI_*_MODEL`.
MODEL_RATES: dict[str, ModelRate] = {
    # Anthropic
    "claude-haiku-4-5": ModelRate(1.00, 5.00),
    "claude-haiku-4-5-20251001": ModelRate(1.00, 5.00),
    "claude-sonnet-4-5": ModelRate(3.00, 15.00),
    "claude-3-5-sonnet-latest": ModelRate(3.00, 15.00),
    "claude-3-5-haiku-latest": ModelRate(0.80, 4.00),
    # OpenAI
    "gpt-4o-mini": ModelRate(0.15, 0.60),
    "gpt-4o": ModelRate(2.50, 10.00),
    "gpt-4.1-mini": ModelRate(0.40, 1.60),
    # Google
    "gemini-1.5-flash": ModelRate(0.075, 0.30),
    "gemini-2.0-flash": ModelRate(0.10, 0.40),
    "gemini-2.5-flash": ModelRate(0.30, 2.50),
}

#: Dùng khi dòng log không có `model` (ghi trước khi có cột) hoặc model lạ.
#:
#: Lấy model **đắt nhất** đang dùng của provider đó. Đoán rẻ thì báo cáo đẹp và
#: sai; đoán đắt thì cùng lắm là thận trọng thừa.
_PROVIDER_FALLBACK: dict[str, ModelRate] = {
    "anthropic": MODEL_RATES["claude-sonnet-4-5"],
    "openai": MODEL_RATES["gpt-4o"],
    "gemini": MODEL_RATES["gemini-2.5-flash"],
}

#: Không biết cả provider lẫn model. Lấy mức đắt nhất trong bảng.
_UNKNOWN = ModelRate(3.00, 15.00)


def rate_for(*, model: str | None, provider: str | None) -> ModelRate:
    """Đơn giá cho một lượt gọi, ưu tiên model rồi mới tới provider."""
    if model and model in MODEL_RATES:
        return MODEL_RATES[model]
    if provider and provider in _PROVIDER_FALLBACK:
        return _PROVIDER_FALLBACK[provider]
    return _UNKNOWN


def cost_vnd(*, tokens_in: int, tokens_out: int, model: str | None, provider: str | None) -> float:
    """Chi phí VND của một lượt gọi.

    Trả `float` chứ không làm tròn: một lượt gọi lẻ có thể tốn dưới một đồng, và
    làm tròn từng dòng rồi mới cộng sẽ nuốt mất phần lớn chi phí khi cộng hàng
    nghìn dòng. Làm tròn ở chỗ hiển thị.
    """
    rate = rate_for(model=model, provider=provider)
    usd = (tokens_in * rate.input_usd_per_mtok + tokens_out * rate.output_usd_per_mtok) / 1_000_000
    return usd * USD_TO_VND


def is_stale(*, now: datetime | None = None) -> bool:
    """`True` khi bảng giá đã quá cũ để coi là số liệu."""
    today = (now or datetime.now(UTC)).date()
    return (today - AS_OF).days > STALE_AFTER_DAYS
