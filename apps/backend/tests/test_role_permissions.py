"""Vai trò phải được **cưỡng chế**, không chỉ hiển thị.

Quy trình soạn → duyệt → đăng chỉ có nghĩa khi hai vai đó tách rời được. Nếu
người soạn tự duyệt được bài mình viết thì bước duyệt chỉ là một cú bấm thêm,
và lời hứa "không gì lên kênh mà chưa qua mắt người khác" thành trang trí.

Màn Đội ngũ có hiện vai từ trước, nhưng backend chưa kiểm — tức là ai gọi thẳng
API cũng duyệt được. Bộ test này khoá lại điều đó.
"""

import pytest

from core.enums import WorkspaceRole
from domain.policies.permissions import Permission, can, roles_with

pytestmark = pytest.mark.anyio

#: Liệt kê tường minh thay vì `vars(Permission)` — `vars` kéo theo `__module__`,
#: `__doc__`… và một test quét qua chúng sẽ đỏ vì lý do không liên quan.
_ALL_PERMISSIONS = [
    Permission.DRAFT_CONTENT,
    Permission.APPROVE_CONTENT,
    Permission.REPLY_CONVERSATION,
    Permission.MANAGE_CONNECTIONS,
    Permission.MANAGE_MEMBERS,
    Permission.VIEW_AUDIT_LOG,
]


class TestBangPhanQuyen:
    """Policy thuần — không DB, không HTTP."""

    def test_nguoi_soan_khong_tu_duyet_duoc(self):
        """Đây là lý do vai Marketer tồn tại tách khỏi Reviewer."""
        assert can(WorkspaceRole.MARKETER, Permission.DRAFT_CONTENT)
        assert not can(WorkspaceRole.MARKETER, Permission.APPROVE_CONTENT)

    def test_nguoi_duyet_cung_soan_duoc(self):
        """Tiệm nhỏ một người kiêm cả hai. Chặn thì họ dùng chung tài khoản Owner
        — tệ hơn hẳn, vì lúc đó không còn phân biệt được ai làm gì."""
        assert can(WorkspaceRole.REVIEWER, Permission.DRAFT_CONTENT)
        assert can(WorkspaceRole.REVIEWER, Permission.APPROVE_CONTENT)

    def test_truc_hoi_thoai_khong_cham_toi_noi_dung_len_kenh(self):
        assert can(WorkspaceRole.SALES, Permission.REPLY_CONVERSATION)
        assert not can(WorkspaceRole.SALES, Permission.APPROVE_CONTENT)
        assert not can(WorkspaceRole.SALES, Permission.DRAFT_CONTENT)

    def test_chi_chu_workspace_quan_tri_duoc_thanh_vien(self):
        for role in (WorkspaceRole.MARKETER, WorkspaceRole.REVIEWER, WorkspaceRole.SALES):
            assert not can(role, Permission.MANAGE_MEMBERS), role

    def test_khong_phai_thanh_vien_thi_khong_quyen_gi(self):
        """Fail-closed: `None` không được rơi vào nhánh mặc định nào."""
        for permission in _ALL_PERMISSIONS:
            assert not can(None, permission), permission

    def test_moi_quyen_deu_co_it_nhat_mot_vai_lam_duoc(self):
        """Một quyền không ai có là một tính năng chết mà không ai nhận ra."""
        for permission in _ALL_PERMISSIONS:
            assert roles_with(permission), permission


async def _member_headers(client, *, owner_headers, ws_id, email, role):
    """Tạo một người mới, mời vào workspace với vai chỉ định, trả headers của họ."""
    signup = await client.post(
        "/auth/sign-up", json={"name": f"Nhân sự {role}", "email": email, "password": "matkhau123"}
    )
    assert signup.status_code == 201, signup.text

    invite = await client.post(
        f"/workspaces/{ws_id}/members",
        json={"email": email, "role": role},
        headers=owner_headers,
    )
    assert invite.status_code == 201, invite.text

    # Token lúc đăng ký chưa trỏ vào workspace nào — người được mời phải
    # activate, giống hệt lúc họ đăng nhập rồi chọn workspace trên UI.
    fresh = {"Authorization": f"Bearer {signup.json()['access_token']}"}
    activated = await client.post(f"/workspaces/{ws_id}/activate", headers=fresh)
    assert activated.status_code == 200, activated.text
    return {"Authorization": f"Bearer {activated.json()['access_token']}"}


async def _owner_workspace(client, email: str):
    signup = await client.post(
        "/auth/sign-up", json={"name": "Chủ", "email": email, "password": "matkhau123"}
    )
    headers = {"Authorization": f"Bearer {signup.json()['access_token']}"}
    ws = await client.post(
        "/workspaces", json={"name": "Tiệm Phân Quyền", "industry": "spa"}, headers=headers
    )
    ws_id = ws.json()["id"]
    refreshed = await client.post(
        "/auth/refresh", json={"refresh_token": signup.json()["refresh_token"]}
    )
    return {"Authorization": f"Bearer {refreshed.json()['access_token']}"}, ws_id


async def test_nguoi_soan_goi_thang_api_duyet_van_bi_chan(client):
    """Ẩn nút ở UI không phải là phân quyền."""
    owner_headers, ws_id = await _owner_workspace(client, "owner_perm@havi.vn")
    marketer = await _member_headers(
        client, owner_headers=owner_headers, ws_id=ws_id,
        email="marketer_perm@havi.vn", role="marketer",
    )

    res = await client.post(
        "/content/approve-all",
        json={"content_item_ids": ["11111111-1111-1111-1111-111111111111"]},
        headers=marketer,
    )

    assert res.status_code == 403, res.text
    # Thông báo phải nói AI làm được, để người bị chặn tự nhắn đúng đồng nghiệp.
    assert "Người duyệt" in res.json()["detail"]


async def test_truc_hoi_thoai_cung_bi_chan_khoi_viec_duyet(client):
    owner_headers, ws_id = await _owner_workspace(client, "owner_perm2@havi.vn")
    sales = await _member_headers(
        client, owner_headers=owner_headers, ws_id=ws_id,
        email="sales_perm@havi.vn", role="sales",
    )

    res = await client.post(
        "/content/approve-all",
        json={"content_item_ids": ["11111111-1111-1111-1111-111111111111"]},
        headers=sales,
    )
    assert res.status_code == 403, res.text


async def test_nguoi_duyet_qua_duoc_cong_phan_quyen(client):
    """Qua được cổng vai — hỏng sau đó là vì id bài không tồn tại, không phải 403."""
    owner_headers, ws_id = await _owner_workspace(client, "owner_perm3@havi.vn")
    reviewer = await _member_headers(
        client, owner_headers=owner_headers, ws_id=ws_id,
        email="reviewer_perm@havi.vn", role="reviewer",
    )

    res = await client.post(
        "/content/approve-all",
        json={"content_item_ids": ["11111111-1111-1111-1111-111111111111"]},
        headers=reviewer,
    )
    assert res.status_code != 403, res.text


async def test_chu_workspace_van_duyet_duoc(client):
    owner_headers, _ = await _owner_workspace(client, "owner_perm4@havi.vn")
    res = await client.post(
        "/content/approve-all",
        json={"content_item_ids": ["11111111-1111-1111-1111-111111111111"]},
        headers=owner_headers,
    )
    assert res.status_code != 403, res.text
