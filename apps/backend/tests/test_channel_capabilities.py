"""Kênh nào nhận loại nội dung nào, và kênh nào đã thật sự mở.

Bộ chọn kênh ở màn Đăng bài từng là một mảng viết cứng trong JSX, liệt kê ba kênh
cố định cho **mọi** loại nội dung. Hai chỗ sai: nó bày ra kênh chưa nối được, và
nó cho phép chọn "Bài viết + TikTok" — mà TikTok không nhận bài chữ.
"""

from httpx import AsyncClient

from core.enums import Channel, ContentKind
from domain.policies import channel_capabilities as caps


class TestPolicy:
    def test_moi_kenh_deu_khai_bao_nhan_gi(self):
        """Thiếu một kênh ở đây thì `channels_for` lặng lẽ bỏ nó, và không ai biết."""
        for channel in Channel:
            assert channel in caps.CHANNEL_ACCEPTS, f"thiếu khai báo cho {channel}"
            assert channel in caps.CHANNEL_LABELS, f"thiếu nhãn cho {channel}"

    def test_tiktok_va_youtube_khong_nhan_bai_chu(self):
        """Đây là luật của nền tảng, không phải lựa chọn của Havi."""
        for channel in (Channel.TIKTOK, Channel.YOUTUBE, Channel.REELS):
            assert caps.accepts(channel=channel, kind=ContentKind.VIDEO) is True
            assert caps.accepts(channel=channel, kind=ContentKind.POST) is False

    def test_facebook_page_nhan_ca_hai(self):
        """Một bài Trang có thể là chữ, ảnh, hoặc video đính kèm."""
        assert caps.accepts(channel=Channel.FACEBOOK_PAGE, kind=ContentKind.POST) is True
        assert caps.accepts(channel=Channel.FACEBOOK_PAGE, kind=ContentKind.VIDEO) is True

    def test_chi_tra_ve_kenh_da_mo(self):
        """Bật một kênh trước khi nó đăng được thật là hứa một thứ chưa tồn tại."""
        for kind in ContentKind:
            for channel in caps.channels_for(kind):
                assert channel in caps.LIVE_CHANNELS

    def test_kenh_chua_mo_thi_khong_lot_vao_danh_sach(self):
        assert Channel.TIKTOK not in caps.channels_for(ContentKind.VIDEO)
        assert Channel.GOOGLE_BUSINESS not in caps.channels_for(ContentKind.POST)

    def test_thu_tu_on_dinh_giua_hai_lan_goi(self):
        """Danh sách nhảy chỗ thì người dùng tick nhầm kênh."""
        assert caps.channels_for(ContentKind.POST) == caps.channels_for(ContentKind.POST)
        assert caps.channels_for(ContentKind.VIDEO) == caps.channels_for(ContentKind.VIDEO)

    def test_moi_loai_noi_dung_deu_con_it_nhat_mot_kenh(self):
        """Không loại nào được rơi vào trạng thái không đăng được ở đâu — lúc đó
        bước 1 của luồng Đăng bài dẫn tới một ngõ cụt."""
        for kind in ContentKind:
            assert caps.channels_for(kind), f"{kind} không còn kênh nào"

    def test_cau_tu_choi_noi_ro_phai_lam_gi(self):
        video_only = caps.reject_reason(channel=Channel.REELS, kind=ContentKind.POST)
        assert video_only is not None
        assert "video" in video_only.lower()

        not_live = caps.reject_reason(channel=Channel.TIKTOK, kind=ContentKind.VIDEO)
        assert not_live is not None
        assert "chưa mở" in not_live

    def test_to_hop_hop_le_thi_khong_co_ly_do_tu_choi(self):
        assert caps.reject_reason(channel=Channel.FACEBOOK_PAGE, kind=ContentKind.POST) is None


async def _onboard(client: AsyncClient, *, email: str) -> dict:
    signup = await client.post(
        "/auth/sign-up",
        json={"name": "Chủ", "email": email, "password": "matkhau123"},
    )
    token_pair = signup.json()
    await client.post(
        "/workspaces",
        json={"name": "Resort"},
        headers={"Authorization": f"Bearer {token_pair['access_token']}"},
    )
    refreshed = await client.post(
        "/auth/refresh", json={"refresh_token": token_pair["refresh_token"]}
    )
    return refreshed.json()


def _headers(token_pair: dict) -> dict:
    return {"Authorization": f"Bearer {token_pair['access_token']}"}


async def test_endpoint_tra_ve_kenh_kem_loai_noi_dung(client: AsyncClient):
    """Trả `kinds` để frontend lọc tại chỗ khi đổi loại nội dung — đổi tab mà phải
    chờ mạng thì ô tick nhảy chỗ."""
    token_pair = await _onboard(client, email="channels-list@havi.vn")

    response = await client.get("/content/channels", headers=_headers(token_pair))

    assert response.status_code == 200, response.text
    options = response.json()
    assert options, "phải có ít nhất một kênh"

    by_channel = {item["channel"]: item for item in options}
    # Chỉ kênh đang mở.
    assert set(by_channel) == {c.value for c in caps.LIVE_CHANNELS}
    assert "post" in by_channel["facebook_page"]["kinds"]
    assert by_channel["reels"]["kinds"] == ["video"]
    # Mỗi kênh có nhãn đọc được, không phải giá trị enum.
    for item in options:
        assert item["label"] and item["label"] != item["channel"]


async def test_kenh_chua_noi_van_hien_nhung_bao_la_chua_noi(client: AsyncClient):
    """Ẩn đi thì người dùng không biết Havi hỗ trợ kênh đó và không biết đi nối."""
    token_pair = await _onboard(client, email="channels-unconnected@havi.vn")

    options = (await client.get("/content/channels", headers=_headers(token_pair))).json()

    assert all(item["connected"] is False for item in options)


async def test_endpoint_khong_lan_sang_workspace_khac(client: AsyncClient):
    token_a = await _onboard(client, email="channels-a@havi.vn")
    token_b = await _onboard(client, email="channels-b@havi.vn")

    a = (await client.get("/content/channels", headers=_headers(token_a))).json()
    b = (await client.get("/content/channels", headers=_headers(token_b))).json()

    # Danh sách kênh giống nhau (cùng luật), nhưng trạng thái nối là của riêng mỗi
    # workspace — cả hai chưa nối nên đều False.
    assert [i["channel"] for i in a] == [i["channel"] for i in b]
    assert all(i["connected"] is False for i in a + b)
