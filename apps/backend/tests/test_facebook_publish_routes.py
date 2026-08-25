"""Bài nào đi đường nào trên Graph API — và Havi cầm về mã bài nào.

Bộ test này canh phần dễ sai nhất và đắt nhất của adapter Facebook: **chọn sai
endpoint hoặc lấy sai ID**. Cả hai đều không làm request đỏ, nên không có test
thì chúng chỉ lộ ra khi chủ tiệm mở Trang lên xem — lúc đó bài đã đăng rồi.

Ba cạm bẫy được khoá lại ở đây:

1. `/photos` trả cả `id` (ID *ảnh*) lẫn `post_id` (ID *bài*). Lấy nhầm `id` thì
   về sau đối soát tra không ra bài, mà đối soát là thứ duy nhất chặn đăng trùng.
2. Album phải upload từng ảnh với `published=false` trước. Thiếu cờ đó là mỗi
   ảnh thành một bài rời trên Trang khách.
3. Graph trả 2xx mà không kèm ID nghĩa là bài **rất có thể đã lên**. Đường duy
   nhất đúng ở đó là dừng lại cho người đối soát, không phải thử lại.

Không gọi mạng thật: `httpx.MockTransport` ghi lại từng request để khẳng định
Havi đã gõ đúng cửa nào.
"""

import httpx
import pytest

from adapters.publishers.facebook import FacebookPublisher
from core.config import Settings
from core.enums import Channel
from domain.ports.publisher import (
    PublishError,
    PublishRequest,
    ValidationPublishError,
)

pytestmark = pytest.mark.anyio


class GraphRecorder:
    """Giả lập Graph API, giữ lại mọi request để test soi lại."""

    def __init__(self, responses: dict[str, dict]) -> None:
        #: khớp theo hậu tố đường dẫn ("/photos", "/feed"…)
        self._responses = responses
        self.calls: list[httpx.Request] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        for suffix, body in self._responses.items():
            if request.url.path.endswith(suffix):
                return httpx.Response(200, json=body, request=request)
        return httpx.Response(200, json={"id": "generic"}, request=request)

    def paths(self) -> list[str]:
        return [call.url.path for call in self.calls]

    def form_of(self, index: int) -> dict[str, str]:
        raw = self.calls[index].content.decode()
        return dict(pair.split("=", 1) for pair in raw.split("&") if "=" in pair)


@pytest.fixture
def graph(monkeypatch):
    """Bọc `httpx.AsyncClient` để mọi request trong test đi qua recorder."""

    def _make(responses: dict[str, dict]) -> tuple[FacebookPublisher, GraphRecorder]:
        recorder = GraphRecorder(responses)
        original_init = httpx.AsyncClient.__init__

        def patched_init(self, *args, **kwargs):  # noqa: ANN001, ANN202
            kwargs["transport"] = httpx.MockTransport(recorder.handler)
            original_init(self, *args, **kwargs)

        monkeypatch.setattr(httpx.AsyncClient, "__init__", patched_init)
        publisher = FacebookPublisher(
            Settings(facebook_client_id="x", facebook_client_secret="y")
        )
        return publisher, recorder

    return _make


async def test_bai_khong_anh_di_duong_feed(graph):
    publisher, recorder = graph({"/feed": {"id": "page_1_post_9"}})

    result = await publisher.publish(
        PublishRequest(text="Tuần này giảm 20%", external_account_id="page_1"),
        access_token="tok",
    )

    assert recorder.paths() == ["/v21.0/page_1/feed"]
    assert recorder.form_of(0)["message"].startswith("Tu")
    assert result.external_post_id == "page_1_post_9"


async def test_bai_mot_anh_di_duong_photos(graph):
    publisher, recorder = graph({"/photos": {"id": "photo_1", "post_id": "page_1_post_5"}})

    result = await publisher.publish(
        PublishRequest(
            text="Ảnh tiệm mới",
            media_urls=["https://storage.havi.vn/a.jpg"],
            external_account_id="page_1",
        ),
        access_token="tok",
    )

    assert recorder.paths() == ["/v21.0/page_1/photos"]
    # ID *bài*, không phải ID *ảnh*. Lấy nhầm là mất khả năng đối soát.
    assert result.external_post_id == "page_1_post_5"


async def test_nhieu_anh_upload_an_truoc_roi_moi_dang_mot_bai(graph):
    """Thiếu `published=false` là mỗi ảnh thành một bài rời trên Trang khách."""
    publisher, recorder = graph(
        {"/photos": {"id": "photo_x"}, "/feed": {"id": "page_1_post_7"}}
    )

    result = await publisher.publish(
        PublishRequest(
            text="Bộ ảnh tiệm",
            media_urls=[
                "https://storage.havi.vn/a.jpg",
                "https://storage.havi.vn/b.jpg",
                "https://storage.havi.vn/c.jpg",
            ],
            external_account_id="page_1",
        ),
        access_token="tok",
    )

    paths = recorder.paths()
    assert paths[:3] == ["/v21.0/page_1/photos"] * 3
    assert paths[3] == "/v21.0/page_1/feed"
    for index in range(3):
        assert recorder.form_of(index)["published"] == "false"
    assert result.external_post_id == "page_1_post_7"


async def test_kenh_reels_khong_bao_gio_di_duong_feed(graph):
    """Reels có pha start/upload/finish riêng — đẩy vào /feed là đăng sai loại."""
    publisher, recorder = graph({"/video_reels": {}})

    # Pha start trả rỗng nên adapter dừng ở đó — không sao, điều cần kiểm là
    # Havi đã gõ cửa `/video_reels` chứ không phải `/feed`.
    with pytest.raises(PublishError):
        await publisher.publish(
            PublishRequest(
                text="Clip 15 giây",
                media_urls=["https://storage.havi.vn/clip.mp4"],
                external_account_id="page_1",
                channel=Channel.REELS,
            ),
            access_token="tok",
        )

    assert all(not path.endswith("/feed") for path in recorder.paths())
    assert recorder.paths()[0].endswith("/video_reels")


async def test_file_mp4_di_duong_reels_du_khong_khai_channel(graph):
    """Nhận ra video từ đuôi file: caller cũ không khai `channel` vẫn không đăng nhầm."""
    publisher, recorder = graph({"/video_reels": {}})

    with pytest.raises(PublishError):
        await publisher.publish(
            PublishRequest(
                text="Clip",
                media_urls=["https://storage.havi.vn/clip.mp4"],
                external_account_id="page_1",
            ),
            access_token="tok",
        )

    assert recorder.paths()[0].endswith("/video_reels")


async def test_graph_tra_2xx_khong_kem_ma_bai_thi_dung_lai_cho_doi_soat(graph):
    """2xx không ID = bài rất có thể ĐÃ lên. Thử lại ở đây là đăng hai bài."""
    publisher, _ = graph({"/feed": {"success": True}})

    with pytest.raises(ValidationPublishError) as exc:
        await publisher.publish(
            PublishRequest(text="Bài không ảnh", external_account_id="page_1"),
            access_token="tok",
        )

    assert "kiểm tra Trang" in str(exc.value)


async def test_thieu_page_id_thi_khong_cham_toi_mang(graph):
    publisher, recorder = graph({})

    with pytest.raises(ValidationPublishError):
        await publisher.publish(
            PublishRequest(text="Bài", external_account_id=None), access_token="tok"
        )

    assert recorder.calls == []
