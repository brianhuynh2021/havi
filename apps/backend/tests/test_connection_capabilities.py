"""Kết nối thiếu quyền vẫn dùng được phần còn lại — và chỉ phần còn lại."""

from core.enums import Platform
from domain.policies.connection_capabilities import (
    Capability,
    capabilities_for,
    has_capability,
)

FULL = [
    "pages_manage_posts",
    "pages_manage_engagement",
    "pages_messaging",
    "pages_manage_metadata",
]


def test_du_quyen_thi_bat_moi_kha_nang():
    assert capabilities_for(Platform.FACEBOOK, FULL) == frozenset(Capability)


def test_thieu_messaging_chi_tat_tra_loi_tin_nhan():
    """Ca chính: tiệm không dùng Messenger vẫn đăng bài và trả lời bình luận."""
    caps = capabilities_for(
        Platform.FACEBOOK, [s for s in FULL if s != "pages_messaging"]
    )
    assert Capability.REPLY_MESSAGE not in caps
    assert Capability.PUBLISH_POST in caps
    assert Capability.REPLY_COMMENT in caps
    assert Capability.RECEIVE_INBOX in caps


def test_ket_noi_cu_khong_ghi_quyen_duoc_coi_la_du():
    """`None` là "không rõ", không phải "không có quyền nào".

    Kết nối nối trước khi có cột `granted_scopes` đã qua vòng kiểm đủ-mọi-quyền
    của phiên bản cũ. Suy ra "không có gì" sẽ tắt oan tính năng đang chạy tốt
    ngay sau khi deploy.
    """
    assert capabilities_for(Platform.FACEBOOK, None) == frozenset(Capability)


def test_danh_sach_rong_khac_han_none():
    """`[]` là đã hỏi và biết chắc không có quyền nào."""
    assert capabilities_for(Platform.FACEBOOK, []) == frozenset()


def test_nen_tang_chua_khai_bang_quyen_thi_khong_tat_gi():
    """Kênh mới thêm mà chưa có mục trong `_REQUIREMENTS` không được im lặng chết."""
    from typing import cast
    unlisted = cast(Platform, "unlisted_platform")
    assert capabilities_for(unlisted, ["bat_ky_gi"]) == frozenset(Capability)


class TestTikTokChiDangDuoc:
    """TikTok không trả lời bình luận/tin nhắn được — API không có đường đó.

    Trước khi TikTok được khai trong `_REQUIREMENTS`, `capabilities_for` rơi vào
    nhánh "chưa khai → coi như đủ" và trả về cả bốn khả năng. UI hiện TikTok trả
    lời được bình luận trong khi không có dòng code nào làm việc đó — đúng cái
    bẫy "UI báo xanh trong khi Inbox im lặng" mà docstring module cảnh báo.
    """

    def test_chi_co_publish_post(self):
        caps = capabilities_for(Platform.TIKTOK, ["user.info.basic", "video.upload"])
        assert caps == frozenset({Capability.PUBLISH_POST})

    def test_khong_bao_gio_bat_reply_hay_inbox(self):
        for scopes in (None, [], ["video.upload"], ["video.publish", "comment.list"]):
            caps = capabilities_for(Platform.TIKTOK, scopes)
            assert Capability.REPLY_COMMENT not in caps
            assert Capability.REPLY_MESSAGE not in caps
            assert Capability.RECEIVE_INBOX not in caps

    def test_ket_noi_cu_van_dang_duoc(self):
        """`None` = kết nối tạo trước khi có cột `granted_scopes`; không tắt oan."""
        assert Capability.PUBLISH_POST in capabilities_for(Platform.TIKTOK, None)

    def test_thieu_video_upload_thi_tat_dang_bai(self):
        assert capabilities_for(Platform.TIKTOK, ["user.info.basic"]) == frozenset()


def test_has_capability_khop_voi_capabilities_for():
    scopes = ["pages_manage_posts"]
    assert has_capability(Platform.FACEBOOK, scopes, Capability.PUBLISH_POST)
    assert not has_capability(Platform.FACEBOOK, scopes, Capability.REPLY_MESSAGE)
