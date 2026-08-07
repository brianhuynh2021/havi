"""Test end-to-end thật trên Postgres — bao gồm chặn cross-tenant access."""

from httpx import AsyncClient


async def _sign_up_and_login(
    client: AsyncClient, *, name: str = "Chị Hương", phone: str = "0912345678"
) -> dict:
    signup = await client.post("/auth/sign-up", json={"name": name, "phone": phone})
    assert signup.status_code == 202, signup.text
    code = signup.json()["debug_code"]

    login = await client.post("/auth/otp/verify", json={"phone": phone, "code": code})
    assert login.status_code == 200, login.text
    return login.json()


def _auth_headers(token_pair: dict) -> dict:
    return {"Authorization": f"Bearer {token_pair['access_token']}"}


async def test_tao_workspace_tu_dong_thanh_active(client: AsyncClient):
    token_pair = await _sign_up_and_login(client, phone="0910000001")
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
    token_a = await _sign_up_and_login(client, name="Chị A", phone="0910000002")
    token_b = await _sign_up_and_login(client, name="Chị B", phone="0910000003")

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
    token_a = await _sign_up_and_login(client, name="Chị A", phone="0910000004")
    token_b = await _sign_up_and_login(client, name="Chị B", phone="0910000005")

    create_a = await client.post(
        "/workspaces", json={"name": "Tiệm A", "industry": "spa"}, headers=_auth_headers(token_a)
    )
    workspace_a_id = create_a.json()["id"]

    # Chị B có JWT hợp lệ, nhưng không thuộc workspace của chị A.
    response = await client.get(f"/workspaces/{workspace_a_id}", headers=_auth_headers(token_b))
    assert response.status_code == 403


async def test_update_workspace_doi_publish_mode(client: AsyncClient):
    token = await _sign_up_and_login(client, phone="0910000006")
    headers = _auth_headers(token)
    create = await client.post(
        "/workspaces", json={"name": "Tiệm", "industry": "spa"}, headers=headers
    )
    workspace_id = create.json()["id"]

    update = await client.patch(
        f"/workspaces/{workspace_id}", json={"publish_mode": "full_auto"}, headers=headers
    )
    assert update.status_code == 200
    assert update.json()["publish_mode"] == "full_auto"


async def test_activate_workspace_tra_token_moi(client: AsyncClient):
    token = await _sign_up_and_login(client, phone="0910000007")
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


async def test_invite_member_bang_sdt_da_co_tai_khoan(client: AsyncClient):
    owner_token = await _sign_up_and_login(client, name="Chị Owner", phone="0910000008")
    await _sign_up_and_login(client, name="Anh Marketer", phone="0910000009")

    headers = _auth_headers(owner_token)
    create = await client.post(
        "/workspaces", json={"name": "Tiệm", "industry": "spa"}, headers=headers
    )
    workspace_id = create.json()["id"]

    invite = await client.post(
        f"/workspaces/{workspace_id}/members",
        json={"phone": "0910000009", "role": "marketer"},
        headers=headers,
    )
    assert invite.status_code == 201, invite.text
    assert invite.json()["name"] == "Anh Marketer"
    assert invite.json()["role"] == "marketer"

    members = await client.get(f"/workspaces/{workspace_id}/members", headers=headers)
    names = {m["name"] for m in members.json()}
    assert names == {"Chị Owner", "Anh Marketer"}


async def test_invite_member_sdt_chua_co_tai_khoan_tra_404(client: AsyncClient):
    owner_token = await _sign_up_and_login(client, phone="0910000010")
    headers = _auth_headers(owner_token)
    create = await client.post(
        "/workspaces", json={"name": "Tiệm", "industry": "spa"}, headers=headers
    )
    workspace_id = create.json()["id"]

    invite = await client.post(
        f"/workspaces/{workspace_id}/members",
        json={"phone": "0999999999", "role": "marketer"},
        headers=headers,
    )
    assert invite.status_code == 404


async def test_khong_the_xoa_owner_duy_nhat(client: AsyncClient):
    token = await _sign_up_and_login(client, phone="0910000011")
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
    owner_token = await _sign_up_and_login(client, name="Chị Owner", phone="0910000012")
    member_login = await _sign_up_and_login(client, name="Anh M", phone="0910000013")

    headers = _auth_headers(owner_token)
    create = await client.post(
        "/workspaces", json={"name": "Tiệm", "industry": "spa"}, headers=headers
    )
    workspace_id = create.json()["id"]
    await client.post(
        f"/workspaces/{workspace_id}/members",
        json={"phone": "0910000013", "role": "marketer"},
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
