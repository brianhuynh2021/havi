"""Chuông Hot Lead: `True` phải nghĩa là Telegram đã nhận tin.

Bộ test này canh một lỗi đã từng có thật và im lặng tuyệt đối: khi thiếu token,
notifier rơi về nhánh mock, ghi log "Gửi thông báo thành công" rồi trả `True`.
Khách để lại số điện thoại, hệ thống báo đã bắn chuông, không có gì được gửi.
Không log lỗi, không exception, không dashboard nào đỏ — chỉ có một lead nguội.

Vì vậy phần lớn test ở đây khẳng định điều ngược lại với trực giác: **những
đường mà code chạy trót lọt vẫn phải trả `False`** nếu Telegram chưa xác nhận.
"""

import httpx
import pytest

from adapters.outbound.telegram_notifier import TelegramNotifier
from core.config import Settings

pytestmark = pytest.mark.anyio


#: Cấu hình tối thiểu để `Settings` qua được mọi validator production khác —
#: giữ cho test ở file này chỉ nói về Telegram, không vô tình test lại email hay
#: rate limit. Khớp với `tests/test_production_config.py`.
_PRODUCTION_BASELINE = {
    "use_mock_llm": False,
    "use_fake_publisher": False,
    "disable_rate_limit": False,
    "email_provider": "smtp",
    "email_from": "no-reply@havi.vn",
    "smtp_host": "smtp.havi.vn",
}


def _settings(*, token: str = "123:abc", chat_id: str = "-100999") -> Settings:
    return Settings(telegram_bot_token=token, telegram_default_chat_id=chat_id)


class Recorder:
    """Bắt request gửi đi, trả về mã trạng thái đã khai."""

    def __init__(self, status: int = 200, *, boom: Exception | None = None) -> None:
        self.status = status
        self.boom = boom
        self.requests: list[httpx.Request] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.boom:
            raise self.boom
        return httpx.Response(self.status, json={"ok": self.status == 200}, request=request)

    def payload(self) -> dict:
        import json

        return json.loads(self.requests[0].content.decode())


@pytest.fixture
def telegram(monkeypatch):
    """Dựng notifier với tầng vận chuyển giả, giữ nguyên logic dựng nội dung."""

    def _make(recorder: Recorder, settings: Settings | None = None) -> TelegramNotifier:
        original_init = httpx.AsyncClient.__init__

        def patched_init(self, *args, **kwargs):  # noqa: ANN001, ANN202
            kwargs["transport"] = httpx.MockTransport(recorder.handler)
            original_init(self, *args, **kwargs)

        monkeypatch.setattr(httpx.AsyncClient, "__init__", patched_init)
        return TelegramNotifier(settings or _settings())

    return _make


async def _send(notifier: TelegramNotifier, **overrides) -> bool:
    params = {
        "shop_name": "Spa Hương Sen",
        "customer_name": "Nguyễn Thu Hương",
        "phone": "0984883750",
        "message": "Cho hỏi gói chăm da bao nhiêu ạ",
        "platform": "Facebook Fanpage",
    }
    params.update(overrides)
    return await notifier.send_hot_lead_alert(**params)


class TestKhongDuocBaoThanhCongKhiChuaGui:
    """Nhóm test quan trọng nhất của file."""

    async def test_thieu_token_thi_tra_false_chu_khong_phai_true(self, telegram):
        recorder = Recorder()
        notifier = telegram(recorder, _settings(token=""))

        assert await _send(notifier) is False
        assert recorder.requests == [], "chưa cấu hình thì không được chạm tới mạng"

    async def test_thieu_chat_id_thi_tra_false(self, telegram):
        recorder = Recorder()
        notifier = telegram(recorder, _settings(chat_id=""))

        assert await _send(notifier) is False
        assert recorder.requests == []

    async def test_telegram_tra_loi_thi_tra_false(self, telegram):
        recorder = Recorder(status=403)
        notifier = telegram(recorder)

        assert await _send(notifier) is False

    async def test_mat_mang_thi_tra_false_chu_khong_nem_len_tren(self, telegram):
        """Chuông hỏng không được làm hỏng luôn việc lưu lead."""
        recorder = Recorder(boom=httpx.ConnectError("mất mạng"))
        notifier = telegram(recorder)

        assert await _send(notifier) is False

    async def test_telegram_nhan_that_thi_moi_tra_true(self, telegram):
        recorder = Recorder(status=200)
        notifier = telegram(recorder)

        assert await _send(notifier) is True
        assert len(recorder.requests) == 1


class TestNoiDungChuong:
    async def test_gui_dung_chat_id_mac_dinh(self, telegram):
        recorder = Recorder()
        notifier = telegram(recorder)

        await _send(notifier)
        assert recorder.payload()["chat_id"] == "-100999"

    async def test_chat_id_truyen_vao_ghi_de_mac_dinh(self, telegram):
        recorder = Recorder()
        notifier = telegram(recorder)

        await _send(notifier, chat_id="-100111")
        assert recorder.payload()["chat_id"] == "-100111"

    async def test_ten_tiem_that_nam_o_tieu_de(self, telegram):
        """Người trực nhiều cơ sở cần biết ngay khách này của tiệm nào."""
        recorder = Recorder()
        notifier = telegram(recorder)

        await _send(notifier)
        assert "Spa Hương Sen" in recorder.payload()["text"]

    async def test_co_nut_goi_va_nut_zalo_kem_so_dien_thoai(self, telegram):
        """Bắt người trực gõ lại số là một lý do để hoãn — hoãn thì lead nguội."""
        recorder = Recorder()
        notifier = telegram(recorder)

        await _send(notifier)
        text = recorder.payload()["text"]
        assert "tel:0984883750" in text
        assert "zalo.me/0984883750" in text

    async def test_so_dien_thoai_co_dau_cach_van_dung_duoc_cho_nut_bam(self, telegram):
        recorder = Recorder()
        notifier = telegram(recorder)

        await _send(notifier, phone="098 488 3750")
        assert "tel:0984883750" in recorder.payload()["text"]

    async def test_ten_khach_chua_ky_tu_html_van_gui_duoc(self, telegram):
        """Tên lạ không được thành lý do khiến chuông im.

        `parse_mode=HTML` khiến một cái tên chứa `<` làm Telegram từ chối cả tin
        nhắn. Nghĩa là đúng những lead có tên lạ lại là những lead bị bỏ lỡ.
        """
        recorder = Recorder()
        notifier = telegram(recorder)

        assert await _send(notifier, customer_name="Trang <script>") is True
        text = recorder.payload()["text"]
        assert "<script>" not in text
        assert "&lt;script&gt;" in text

    async def test_noi_dung_tin_nhan_khach_cung_duoc_thoat(self, telegram):
        recorder = Recorder()
        notifier = telegram(recorder)

        await _send(notifier, message="giá <b>bao nhiêu</b>?")
        text = recorder.payload()["text"]
        assert "&lt;b&gt;bao nhiêu&lt;/b&gt;" in text

    async def test_khong_co_tin_nhan_thi_khong_hien_dong_nhu_cau_rong(self, telegram):
        recorder = Recorder()
        notifier = telegram(recorder)

        await _send(notifier, message=None)
        assert "Nhu cầu" not in recorder.payload()["text"]

    async def test_tin_nhan_dai_bi_cat_nhung_giu_nguyen_so_va_nut_bam(self, telegram):
        """Telegram cắt tin quá 4096 ký tự — cắt chủ động, và cắt đúng chỗ."""
        recorder = Recorder()
        notifier = telegram(recorder)

        assert await _send(notifier, message="dài " * 2000) is True
        text = recorder.payload()["text"]
        assert len(text) <= 4096
        assert "tel:0984883750" in text
        assert "0984883750" in text


class TestChanTokenGia:
    """Validator ở `Settings` — chỉ chặn thứ *trông như đã cấu hình* mà không phải."""

    def test_local_van_chay_duoc_khi_chua_cau_hinh(self):
        settings = Settings(env="local", telegram_bot_token="", telegram_default_chat_id="")
        assert settings.telegram_bot_token == ""

    def test_de_rong_o_staging_van_deploy_duoc(self):
        """Cơ sở không dùng chuông Telegram vẫn phải deploy được.

        Notifier đã nói thật về việc chưa gửi (`False` + log cảnh báo kèm nguyên
        nội dung), nên không cần chặn ở tầng cấu hình. Chặn ở đây sẽ biến
        Telegram thành phụ thuộc cứng của cả app.
        """
        settings = Settings(env="staging", telegram_bot_token="", **_PRODUCTION_BASELINE)
        assert settings.telegram_bot_token == ""

    def test_telegram_khong_nam_trong_danh_sach_bat_buoc_cua_production(self):
        """Production có validator "thiếu gì thì liệt kê ra" — Telegram không ở đó.

        Kiểm bằng thông báo lỗi thay vì dựng một config production đầy đủ: điều
        cần khẳng định là *Telegram không bị liệt vào danh sách bắt buộc*, và
        thông báo đó nói thẳng ra điều ấy.
        """
        with pytest.raises(ValueError) as exc:
            Settings(env="production", telegram_bot_token="", **_PRODUCTION_BASELINE)

        # Pydantic in lại cả dict đầu vào trong thông báo, nên chỉ đọc đúng đoạn
        # liệt kê biến còn thiếu.
        message = str(exc.value)
        marker = "Production configuration thiếu hoặc không an toàn:"
        assert marker in message
        missing = message.split(marker, 1)[1].split("[type=")[0]
        assert "TELEGRAM" not in missing.upper()

    @pytest.mark.parametrize("env", ["staging", "production"])
    def test_token_mock_bi_tu_choi_vi_trong_nhu_da_cau_hinh(self, env):
        with pytest.raises(ValueError, match="MOCK"):
            Settings(
                env=env,
                telegram_bot_token="MOCK_TELEGRAM_BOT_TOKEN",
                telegram_default_chat_id="-100999",
                **_PRODUCTION_BASELINE,
            )
