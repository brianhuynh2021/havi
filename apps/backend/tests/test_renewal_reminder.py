"""Nhắc gia hạn — mốc nhắc, và chỗ cố ý không nhắc.

Havi đã có banner nhắc trong app khi còn ≤7 ngày, nhưng nó có một lỗ hổng logic:
**người sắp rời đi chính là người đã ngừng mở app**. Kênh ra ngoài app là cách duy
nhất tới được đúng ca churn thật.
"""

from datetime import UTC, datetime, timedelta

import httpx
import pytest

from adapters.outbound.telegram_alerts import TelegramAlertSink
from core.alerts import Alert
from core.enums import Plan, SubscriptionStatus
from domain.policies import renewal


def _in(days: float) -> datetime:
    return datetime.now(UTC) + timedelta(days=days)


class TestMocNhac:
    @pytest.mark.parametrize("days", renewal.REMINDER_DAYS)
    def test_nhac_dung_o_moi_moc(self, days: int):
        # +0.5 ngày để `days` sau khi làm tròn xuống ra đúng mốc.
        assert (
            renewal.should_remind(
                plan=Plan.TIEM_NHO,
                status=SubscriptionStatus.ACTIVE,
                paid_until=_in(days + 0.5),
            )
            is True
        )

    @pytest.mark.parametrize("days", [10, 5, 2, -3, -20])
    def test_ngoai_moc_thi_khong_nhac(self, days: int):
        """Nhắc mỗi ngày thì người ta thôi đọc — và một kênh bị bỏ qua thì tệ hơn
        không có, vì lần thật sự cần đọc cũng bị bỏ qua cùng."""
        assert (
            renewal.should_remind(
                plan=Plan.TIEM_NHO,
                status=SubscriptionStatus.ACTIVE,
                paid_until=_in(days + 0.5),
            )
            is False
        )

    def test_khong_nhac_workspace_dang_dung_thu(self):
        """Hết hạn trial không phải một lần gia hạn bị quên — nó là một quyết định
        mua chưa từng xảy ra. Nhắc ở đó là đòi tiền một người chưa từng trả."""
        assert (
            renewal.should_remind(
                plan=Plan.TRIAL,
                status=SubscriptionStatus.TRIALING,
                paid_until=_in(3.5),
            )
            is False
        )

    def test_khong_nhac_workspace_da_huy(self):
        """Họ đã nói không."""
        assert (
            renewal.should_remind(
                plan=Plan.TIEM_NHO,
                status=SubscriptionStatus.CANCELED,
                paid_until=_in(3.5),
            )
            is False
        )

    def test_khong_co_moc_het_han_thi_khong_nhac(self):
        assert (
            renewal.should_remind(
                plan=Plan.TIEM_NHO,
                status=SubscriptionStatus.ACTIVE,
                paid_until=None,
            )
            is False
        )

    def test_lam_tron_xuong_de_nhac_som_hon_chu_khong_muon_hon(self):
        """Nhắc sớm hơn thực tế thì vô hại; nhắc muộn hơn thì khách mất quyền giữa
        lúc đang trực khách."""
        assert renewal.days_until(_in(1.9)) == 1

    def test_nhan_ca_datetime_khong_timezone(self):
        """Cột `paid_until` đọc từ database có thể về dạng naive."""
        naive = (datetime.now(UTC) + timedelta(days=3.5)).replace(tzinfo=None)
        assert renewal.days_until(naive) == 3


class TestCauNhac:
    def test_viet_cho_nguoi_se_goi_khach(self):
        """Người đọc câu này đang mở danh bạ, không mở terminal: có tên thương hiệu
        và việc cần làm, không có id hay mã trạng thái."""
        summary = renewal.reminder_summary(workspace_name="Resort An Nhiên", days_left=3)
        assert "Resort An Nhiên" in summary
        assert "3 ngày" in summary
        for jargon in ("workspace", "uuid", "past_due", "plan="):
            assert jargon not in summary

    def test_het_han_hom_nay_noi_khac_voi_con_may_ngay(self):
        assert "hôm nay" in renewal.reminder_summary(workspace_name="X", days_left=0)

    def test_qua_han_thi_doi_giong_sang_hoi_con_dung_khong(self):
        summary = renewal.reminder_summary(workspace_name="X", days_left=-2)
        assert "2 ngày" in summary
        assert "còn dùng tiếp" in summary


class TestTelegramSink:
    async def test_chua_cau_hinh_thi_khong_goi_mang_va_khong_nem(self, monkeypatch):
        """Thiếu token là trạng thái bình thường ở local và trong test. Một adapter
        thông báo ném khi chưa cấu hình sẽ làm đổ đúng cái task nó chỉ đóng vai
        phụ."""
        called = False

        def _fail(*args, **kwargs):
            nonlocal called
            called = True
            raise AssertionError("không được gọi mạng khi chưa cấu hình")

        monkeypatch.setattr(httpx, "AsyncClient", _fail)
        sink = TelegramAlertSink(bot_token="", chat_id="")

        assert sink.configured is False
        await sink.send(Alert(type="t", severity="warning", summary="thử"))
        assert called is False

    async def test_telegram_sap_thi_log_roi_di_tiep(self, monkeypatch):
        """Telegram sập không phải sự cố của Havi."""

        class _Boom:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return False

            async def post(self, *args, **kwargs):
                raise httpx.ConnectError("down")

        monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: _Boom())
        sink = TelegramAlertSink(bot_token="tok", chat_id="chat")

        # Không ném là toàn bộ điều cần khẳng định.
        await sink.send(Alert(type="t", severity="error", summary="thử"))

    async def test_khong_dung_parse_mode(self, monkeypatch):
        """Tên thương hiệu của khách có thể chứa `_` hay `*`, và Telegram sẽ từ chối
        cả tin nhắn vì Markdown không hợp lệ. Chữ thường không bao giờ hỏng."""
        sent: dict = {}

        class _Capture:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return False

            async def post(self, url, json):  # noqa: A002
                sent.update(json)
                return httpx.Response(200)

        monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: _Capture())
        sink = TelegramAlertSink(bot_token="tok", chat_id="chat")

        await sink.send(
            Alert(
                type="billing.renewal_due",
                severity="warning",
                summary="Spa_An*Nhiên còn 3 ngày là hết hạn",
            )
        )

        assert "parse_mode" not in sent
        assert "Spa_An*Nhiên" in sent["text"]
