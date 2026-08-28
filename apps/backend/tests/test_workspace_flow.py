"""Test end-to-end thật trên Postgres — bao gồm chặn cross-tenant access."""

from httpx import AsyncClient


async def _sign_up_and_login(client: AsyncClient, *, name: str = "Chị Hương", email: str) -> dict:
    signup = await client.post(
        "/auth/sign-up", json={"name": name, "email": email, "password": "matkhau123"}
    )
    assert signup.status_code == 201, signup.text
    return signup.json()


def _auth_headers(token_pair: dict) -> dict:
    return {"Authorization": f"Bearer {token_pair['access_token']}"}


async def test_tao_workspace_tu_dong_thanh_active(client: AsyncClient):
    token_pair = await _sign_up_and_login(client, email="w0001@havi.vn")
    headers = _auth_headers(token_pair)

    create = await client.post(
        "/workspaces",
        json={"name": "Spa An Nhiên", "industry": "spa"},
        headers=headers,
    )
    assert create.status_code == 201, create.text
    workspace = create.json()
    assert workspace["name"] == "Spa An Nhiên"
    assert workspace["plan"] == "trial"
    assert workspace["publish_mode"] == "review_first"

    # JWT cũ chưa có active_workspace_id — refresh để lấy token phản ánh workspace mới.
    refreshed = await client.post(
        "/auth/refresh", json={"refresh_token": token_pair["refresh_token"]}
    )
    assert refreshed.status_code == 200
    assert refreshed.json()["active_workspace_id"] == workspace["id"]
    assert refreshed.json()["needs_onboarding"] is False


async def test_list_workspaces_chi_thay_workspace_cua_minh(client: AsyncClient):
    token_a = await _sign_up_and_login(client, name="Chị A", email="w0002@havi.vn")
    token_b = await _sign_up_and_login(client, name="Chị B", email="w0003@havi.vn")

    await client.post(
        "/workspaces", json={"name": "Tiệm A", "industry": "spa"}, headers=_auth_headers(token_a)
    )
    await client.post(
        "/workspaces",
        json={"name": "Tiệm B", "industry": "food_beverage"},
        headers=_auth_headers(token_b),
    )

    list_a = await client.get("/workspaces", headers=_auth_headers(token_a))
    names_a = [w["name"] for w in list_a.json()]
    assert names_a == ["Tiệm A"]


async def test_khong_the_doc_workspace_cua_nguoi_khac(client: AsyncClient):
    token_a = await _sign_up_and_login(client, name="Chị A", email="w0004@havi.vn")
    token_b = await _sign_up_and_login(client, name="Chị B", email="w0005@havi.vn")

    create_a = await client.post(
        "/workspaces", json={"name": "Tiệm A", "industry": "spa"}, headers=_auth_headers(token_a)
    )
    workspace_a_id = create_a.json()["id"]

    # Chị B có JWT hợp lệ, nhưng không thuộc workspace của chị A.
    response = await client.get(f"/workspaces/{workspace_a_id}", headers=_auth_headers(token_b))
    assert response.status_code == 403


async def test_update_workspace_doi_ten_nganh(client: AsyncClient):
    token = await _sign_up_and_login(client, email="w0006@havi.vn")
    headers = _auth_headers(token)
    create = await client.post(
        "/workspaces", json={"name": "Tiệm", "industry": "spa"}, headers=headers
    )
    workspace_id = create.json()["id"]

    update = await client.patch(
        f"/workspaces/{workspace_id}", json={"name": "Tiệm Mới", "industry": "food_beverage"}, headers=headers
    )
    assert update.status_code == 200
    assert update.json()["name"] == "Tiệm Mới"
    assert update.json()["industry"] == "food_beverage"


async def test_activate_workspace_tra_token_moi(client: AsyncClient):
    token = await _sign_up_and_login(client, email="w0007@havi.vn")
    headers = _auth_headers(token)
    create = await client.post(
        "/workspaces", json={"name": "Tiệm", "industry": "spa"}, headers=headers
    )
    workspace_id = create.json()["id"]

    activate = await client.post(f"/workspaces/{workspace_id}/activate", headers=headers)
    assert activate.status_code == 200
    body = activate.json()
    assert body["active_workspace_id"] == workspace_id
    assert body["needs_onboarding"] is False


async def test_invite_member_bang_email_da_co_tai_khoan(client: AsyncClient):
    owner_token = await _sign_up_and_login(client, name="Chị Owner", email="w0008@havi.vn")
    await _sign_up_and_login(client, name="Anh Marketer", email="w0009@havi.vn")

    headers = _auth_headers(owner_token)
    create = await client.post(
        "/workspaces", json={"name": "Tiệm", "industry": "spa"}, headers=headers
    )
    workspace_id = create.json()["id"]

    invite = await client.post(
        f"/workspaces/{workspace_id}/members",
        json={"email": "w0009@havi.vn", "role": "marketer"},
        headers=headers,
    )
    assert invite.status_code == 201, invite.text
    assert invite.json()["name"] == "Anh Marketer"
    assert invite.json()["role"] == "marketer"

    members = await client.get(f"/workspaces/{workspace_id}/members", headers=headers)
    names = {m["name"] for m in members.json()}
    assert names == {"Chị Owner", "Anh Marketer"}


async def test_invite_member_email_chua_co_tai_khoan_tra_404(client: AsyncClient):
    owner_token = await _sign_up_and_login(client, email="w0010@havi.vn")
    headers = _auth_headers(owner_token)
    create = await client.post(
        "/workspaces", json={"name": "Tiệm", "industry": "spa"}, headers=headers
    )
    workspace_id = create.json()["id"]

    invite = await client.post(
        f"/workspaces/{workspace_id}/members",
        json={"email": "khongtontai@havi.vn", "role": "marketer"},
        headers=headers,
    )
    assert invite.status_code == 404


async def test_khong_the_xoa_owner_duy_nhat(client: AsyncClient):
    token = await _sign_up_and_login(client, email="w0011@havi.vn")
    headers = _auth_headers(token)
    create = await client.post(
        "/workspaces", json={"name": "Tiệm", "industry": "spa"}, headers=headers
    )
    workspace_id = create.json()["id"]
    me = await client.get("/auth/me", headers=headers)
    owner_id = me.json()["id"]

    response = await client.delete(
        f"/workspaces/{workspace_id}/members/{owner_id}", headers=headers
    )
    assert response.status_code == 409


async def test_xoa_member_thuong_thanh_cong(client: AsyncClient):
    owner_token = await _sign_up_and_login(client, name="Chị Owner", email="w0012@havi.vn")
    member_login = await _sign_up_and_login(client, name="Anh M", email="w0013@havi.vn")

    headers = _auth_headers(owner_token)
    create = await client.post(
        "/workspaces", json={"name": "Tiệm", "industry": "spa"}, headers=headers
    )
    workspace_id = create.json()["id"]
    await client.post(
        f"/workspaces/{workspace_id}/members",
        json={"email": "w0013@havi.vn", "role": "marketer"},
        headers=headers,
    )
    member_me = await client.get("/auth/me", headers=_auth_headers(member_login))
    member_id = member_me.json()["id"]

    response = await client.delete(
        f"/workspaces/{workspace_id}/members/{member_id}", headers=headers
    )
    assert response.status_code == 204

    members = await client.get(f"/workspaces/{workspace_id}/members", headers=headers)
    names = {m["name"] for m in members.json()}
    assert names == {"Chị Owner"}
