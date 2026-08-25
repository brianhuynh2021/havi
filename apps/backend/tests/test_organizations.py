"""Tầng doanh nghiệp: nhiều thương hiệu / chi nhánh trong một tổ chức.

Hai điều bộ test này canh:

1. **Dữ liệu không chảy chéo giữa các thương hiệu** trong cùng một tổ chức. Đó
   là điểm khiến multi-brand khác với việc gắn nhãn: chi nhánh Quận 1 không được
   thấy nội dung hay hộp thư của chi nhánh Quận 7.
2. **Tổ chức của người khác là vô hình.** Biết id không được đọc ra gì — và câu
   trả lời phải là 404, vì 403 đã tự nó xác nhận tổ chức đó tồn tại.
"""

from httpx import AsyncClient

pytest_plugins: list[str] = []


async def _signup(client: AsyncClient, email: str, name: str = "Chủ doanh nghiệp"):
    res = await client.post(
        "/auth/sign-up", json={"name": name, "email": email, "password": "matkhau123"}
    )
    assert res.status_code == 201, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}, res.json()


async def _with_first_workspace(client: AsyncClient, email: str, ws_name: str):
    """Đăng ký + tạo workspace đầu tiên. Trả headers đã active và org id."""
    headers, tokens = await _signup(client, email)
    ws = await client.post(
        "/workspaces", json={"name": ws_name, "industry": "spa"}, headers=headers
    )
    assert ws.status_code == 201, ws.text

    refreshed = await client.post(
        "/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    active = {"Authorization": f"Bearer {refreshed.json()['access_token']}"}

    orgs = await client.get("/organizations", headers=active)
    assert orgs.status_code == 200, orgs.text
    return active, orgs.json(), ws.json()["id"]


async def test_workspace_dau_tien_tu_dong_thuoc_mot_to_chuc(client: AsyncClient):
    """Chủ tiệm đơn lẻ không bao giờ thấy khái niệm "tổ chức".

    Nhưng workspace của họ vẫn phải thuộc về một tổ chức, để ngày họ mở thương
    hiệu thứ hai thì không phải migrate gì.
    """
    _, orgs, ws_id = await _with_first_workspace(client, "solo@havi.vn", "Spa An Nhiên")

    assert len(orgs) == 1
    assert orgs[0]["organization"]["name"] == "Spa An Nhiên"
    assert [b["id"] for b in orgs[0]["brands"]] == [ws_id]


async def test_mo_them_thuong_hieu_trong_cung_to_chuc(client: AsyncClient):
    headers, orgs, first_ws = await _with_first_workspace(
        client, "chain@havi.vn", "Chuỗi Spa An Nhiên"
    )
    org_id = orgs[0]["organization"]["id"]

    second = await client.post(
        f"/organizations/{org_id}/brands",
        json={"name": "An Nhiên Quận 7", "industry": "spa"},
        headers=headers,
    )
    assert second.status_code == 201, second.text

    after = await client.get("/organizations", headers=headers)
    brands = after.json()[0]["brands"]
    assert len(brands) == 2
    assert {b["name"] for b in brands} == {"Chuỗi Spa An Nhiên", "An Nhiên Quận 7"}


async def test_du_lieu_khong_chay_cheo_giua_hai_thuong_hieu(client: AsyncClient):
    """Điểm khiến multi-brand khác với gắn nhãn.

    Hai chi nhánh cùng tổ chức, nhưng nội dung của chi nhánh này không được lọt
    sang chi nhánh kia — lớp cách ly vẫn là `workspace_id`, không phải
    `organization_id`.
    """
    headers, orgs, ws_one = await _with_first_workspace(
        client, "isolate@havi.vn", "Chi nhánh Quận 1"
    )
    org_id = orgs[0]["organization"]["id"]

    ws_two = (
        await client.post(
            f"/organizations/{org_id}/brands",
            json={"name": "Chi nhánh Quận 7", "industry": "spa"},
            headers=headers,
        )
    ).json()["id"]

    # Tạo nội dung ở chi nhánh 1 (workspace đang active).
    job = await client.post(
        "/content/jobs",
        json={"raw_inputs": [{"kind": "text", "text": "Ưu đãi riêng Quận 1"}]},
        headers=headers,
    )
    assert job.status_code == 202, job.text
    assert job.json()["workspace_id"] == ws_one

    # Chuyển sang chi nhánh 2 rồi đọc lại — phải trống.
    switched = await client.post(f"/workspaces/{ws_two}/activate", headers=headers)
    assert switched.status_code == 200, switched.text
    other = {"Authorization": f"Bearer {switched.json()['access_token']}"}

    content = await client.get("/content", headers=other)
    assert content.status_code == 200
    assert content.json()["items"] == [], "nội dung không được chảy sang thương hiệu khác"


async def test_to_chuc_cua_nguoi_khac_la_vo_hinh(client: AsyncClient):
    """404 chứ không 403: 403 đã tự xác nhận tổ chức đó tồn tại."""
    _, orgs, _ = await _with_first_workspace(client, "victim@havi.vn", "Tiệm Của Tôi")
    victim_org = orgs[0]["organization"]["id"]

    intruder, _ = await _signup(client, "intruder@havi.vn", "Người lạ")

    res = await client.post(
        f"/organizations/{victim_org}/brands",
        json={"name": "Chi nhánh cướp", "industry": "spa"},
        headers=intruder,
    )
    assert res.status_code == 404, res.text

    invite = await client.post(
        f"/organizations/{victim_org}/members",
        json={"email": "intruder@havi.vn"},
        headers=intruder,
    )
    assert invite.status_code == 404, invite.text


async def test_thanh_vien_thuong_khong_mo_duoc_thuong_hieu(client: AsyncClient):
    """Vào tổ chức ≠ được mở chi nhánh mới bằng tiền của công ty."""
    owner, orgs, _ = await _with_first_workspace(client, "boss@havi.vn", "Công Ty A")
    org_id = orgs[0]["organization"]["id"]

    member_headers, _ = await _signup(client, "staff@havi.vn", "Nhân viên")
    invited = await client.post(
        f"/organizations/{org_id}/members",
        json={"email": "staff@havi.vn"},
        headers=owner,
    )
    assert invited.status_code == 204, invited.text

    # Thấy tổ chức...
    seen = await client.get("/organizations", headers=member_headers)
    assert len(seen.json()) == 1

    # ...nhưng không mở được thương hiệu.
    res = await client.post(
        f"/organizations/{org_id}/brands",
        json={"name": "Chi nhánh tự mở", "industry": "spa"},
        headers=member_headers,
    )
    assert res.status_code == 403, res.text


async def test_vao_to_chuc_chua_phai_la_vao_thuong_hieu(client: AsyncClient):
    """Thành viên tổ chức chưa có vai ở workspace nào thì chưa làm được gì ở đó."""
    owner, orgs, ws_id = await _with_first_workspace(client, "boss2@havi.vn", "Công Ty B")
    org_id = orgs[0]["organization"]["id"]

    staff, staff_tokens = await _signup(client, "staff2@havi.vn", "Nhân viên")
    await client.post(
        f"/organizations/{org_id}/members",
        json={"email": "staff2@havi.vn"},
        headers=owner,
    )

    # Chưa được cấp vai ở workspace → không activate được vào đó.
    res = await client.post(f"/workspaces/{ws_id}/activate", headers=staff)
    assert res.status_code in (403, 404), res.text


async def test_moi_email_chua_co_tai_khoan_thi_bao_ro(client: AsyncClient):
    owner, orgs, _ = await _with_first_workspace(client, "boss3@havi.vn", "Công Ty C")
    org_id = orgs[0]["organization"]["id"]

    res = await client.post(
        f"/organizations/{org_id}/members",
        json={"email": "chuacotaikhoan@havi.vn"},
        headers=owner,
    )
    assert res.status_code == 404
    assert "đăng ký" in res.json()["detail"]


async def test_moi_lai_cung_mot_nguoi_khong_loi(client: AsyncClient):
    """Onboarding và lời mời có thể chạy song song — insert trùng không được nổ."""
    owner, orgs, _ = await _with_first_workspace(client, "boss4@havi.vn", "Công Ty D")
    org_id = orgs[0]["organization"]["id"]
    await _signup(client, "staff4@havi.vn", "Nhân viên")

    for _ in range(2):
        res = await client.post(
            f"/organizations/{org_id}/members",
            json={"email": "staff4@havi.vn"},
            headers=owner,
        )
        assert res.status_code == 204, res.text
