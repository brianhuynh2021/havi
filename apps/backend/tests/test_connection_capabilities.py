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
    """Kênh mới thêm mà quên khai bảng quyền không được im lặng chết."""
    assert capabilities_for(Platform.TIKTOK, ["bat_ky_gi"]) == frozenset(Capability)


def test_has_capability_khop_voi_capabilities_for():
    scopes = ["pages_manage_posts"]
    assert has_capability(Platform.FACEBOOK, scopes, Capability.PUBLISH_POST)
    assert not has_capability(Platform.FACEBOOK, scopes, Capability.REPLY_MESSAGE)
