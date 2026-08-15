"""Adapter Facebook: map lỗi Graph API sang ba loại worker biết xử.

Không gọi mạng thật — dựng `httpx.Response` với đúng shape Graph API trả về.
Map sai một mã nghĩa là hoặc retry vô tận một thứ không bao giờ chạy (token hết
hạn), hoặc bỏ cuộc trên một lỗi mạng thoáng qua.
"""

import httpx
import pytest

from adapters.publishers.facebook import FacebookPublisher
from core.config import Settings
from domain.ports.publisher import (
    AuthPermissionError,
    PublishRequest,
    TemporaryPublishError,
    ValidationPublishError,
)

pytestmark = pytest.mark.anyio


def _publisher() -> FacebookPublisher:
    return FacebookPublisher(Settings(facebook_client_id="x", facebook_client_secret="y"))


def _response(status: int, *, code: int | None = None, message: str = "loi") -> httpx.Response:
    body = {"error": {"message": message}}
    if code is not None:
        body["error"]["code"] = code
    return httpx.Response(status, json=body, request=httpx.Request("POST", "https://x"))


class TestPhanLoaiLoi:
    @pytest.mark.parametrize("code", [190, 200, 102, 10])
    def test_ma_loi_token_va_quyen_khong_duoc_retry(self, code):
        """Retry khi token hết hạn chỉ đập API và vẫn hỏng — cần nối lại kênh."""
        err = _publisher()._classify_error(_response(400, code=code))
        assert isinstance(err, AuthPermissionError)

    @pytest.mark.parametrize("code", [4, 17, 32, 613, 1, 2])
    def test_ma_loi_rate_limit_duoc_retry(self, code):
        err = _publisher()._classify_error(_response(400, code=code))
        assert isinstance(err, TemporaryPublishError)

    def test_uu_tien_ma_graph_hon_http_status(self):
        """Graph trả 400 cho cả token hết hạn lẫn nội dung bị từ chối — hai thứ
        cần xử khác hẳn nhau, nên `code` phải thắng status."""
        err = _publisher()._classify_error(_response(400, code=190))
        assert isinstance(err, AuthPermissionError), "400 + code 190 là lỗi token"

    def test_429_khong_co_ma_van_duoc_retry(self):
        err = _publisher()._classify_error(_response(429))
        assert isinstance(err, TemporaryPublishError)

    def test_5xx_duoc_retry(self):
        err = _publisher()._classify_error(_response(503))
        assert isinstance(err, TemporaryPublishError)

    def test_401_403_khong_retry(self):
        for status in (401, 403):
            err = _publisher()._classify_error(_response(status))
            assert isinstance(err, AuthPermissionError)

    def test_ma_la_coi_la_loi_noi_dung_khong_retry(self):
        """Cùng payload sẽ bị từ chối y hệt — vào dead-letter để người xem."""
        err = _publisher()._classify_error(_response(400, code=99999))
        assert isinstance(err, ValidationPublishError)

    def test_response_khong_phai_json_van_phan_loai_duoc(self):
        raw = httpx.Response(
            500, text="<html>gateway</html>", request=httpx.Request("POST", "https://x")
        )
        assert isinstance(_publisher()._classify_error(raw), TemporaryPublishError)

    def test_thong_bao_loi_giu_ma_de_support_tra_duoc(self):
        err = _publisher()._classify_error(_response(400, code=190, message="Token het han"))
        assert "190" in err.detail and "Token het han" in err.detail


class TestPublish:
    async def test_thieu_page_id_la_loi_cau_hinh_khong_retry(self):
        with pytest.raises(ValidationPublishError, match="Page ID"):
            await _publisher().publish(
                PublishRequest(text="x", external_account_id=None), access_token="t"
            )
