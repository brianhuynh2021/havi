import pytest
from pydantic import ValidationError

from core.config import Settings


def test_production_rejects_defaults_and_missing_real_providers():
    with pytest.raises(ValidationError, match="Production configuration"):
        Settings(
            env="production",
            use_mock_llm=False,
            use_fake_publisher=False,
            use_fake_reply=False,
            disable_rate_limit=False,
                email_provider="smtp",
            email_from="no-reply@havi.vn",
            smtp_host="smtp.havi.vn",
        )


class TestFakeReplyChiSongOLocal:
    """Fake reply hỏng im lặng, và nạn nhân là khách chứ không phải chủ tiệm.

    Inbox hiện "đã gửi", người trực ca chuyển sang tin kế tiếp, còn khách ngồi
    chờ một câu trả lời không bao giờ tới. Không ai thấy gì bất thường — nên
    phải chặn ở lúc khởi động, không phải lúc khách phàn nàn.
    """

    @pytest.mark.parametrize("env", ["staging", "production"])
    def test_ngoai_local_thi_khong_khoi_dong_duoc(self, env):
        """Tắt tường minh MỌI cờ fake khác, chỉ để `use_fake_reply` bật.

        Bốn validator chạy theo thứ tự khai báo (mock_llm → fake_publisher →
        fake_reply → rate_limit) và cái đầu tiên thấy vi phạm sẽ ném. Cả ba cờ
        này **default là `True`** trong `Settings`, nên nếu không tắt tay thì
        validator fake-publisher ném trước và test không bao giờ chạm tới thông
        báo fake-reply mà nó đang assert.

        Trước đây test xanh chỉ vì `.env` trên máy dev đặt các cờ đó thành
        `false` — `Settings` đọc `.env`. Trên CI không có file đó nên default
        `True` có hiệu lực và test đỏ. Pin hết là cách duy nhất khiến test kiểm
        đúng một thứ, độc lập với máy chạy.
        """
        with pytest.raises(ValidationError, match="HAVI_USE_FAKE_REPLY"):
            Settings(
                env=env,
                use_fake_reply=True,
                use_mock_llm=False,
                use_fake_publisher=False,
                disable_rate_limit=False,
            )

    def test_local_van_duoc_dung_fake(self):
        assert Settings(env="local", use_fake_reply=True).use_fake_reply is True

    def test_tach_roi_khoi_co_dang_bai(self):
        """Thử đăng bài thật không có nghĩa là đồng ý nhắn thật cho khách.

        Đăng nhầm lên Trang test thì xoá được; nhắn nhầm vào hộp thư người thật
        thì không rút lại được, nên hai cờ phải bật tắt độc lập.
        """
        settings = Settings(env="local", use_fake_publisher=False, use_fake_reply=True)

        assert settings.use_fake_publisher is False
        assert settings.use_fake_reply is True


class TestChonReplyPublisherTheoCo:
    """Cờ phải quyết định publisher, và web với worker phải chọn giống nhau."""

    def _publishers(self, settings, monkeypatch):
        import worker.inbox_service_factory as factory

        monkeypatch.setattr(factory, "get_settings", lambda: settings)
        return factory.build_reply_publishers(session=None)

    def test_bat_co_thi_dung_fake(self, monkeypatch):
        from adapters.publishers.fake_reply import FakeReplyPublisher
        from core.enums import Platform

        publishers = self._publishers(Settings(env="local", use_fake_reply=True), monkeypatch)

        assert isinstance(publishers[Platform.FACEBOOK], FakeReplyPublisher)

    def test_tat_co_thi_gui_that_du_van_o_local(self, monkeypatch):
        """Điểm chính của cờ này: thử nhắn thật mà không phải đổi HAVI_ENV.

        Đổi ENV kéo theo cả CORS, rate limit và việc chặn endpoint dev — quá
        nhiều thứ đổi cùng lúc chỉ để thử một tin nhắn.
        """
        from adapters.publishers.facebook_reply import FacebookReplyAdapter
        from core.enums import Platform

        publishers = self._publishers(Settings(env="local", use_fake_reply=False), monkeypatch)

        assert isinstance(publishers[Platform.FACEBOOK], FacebookReplyAdapter)
