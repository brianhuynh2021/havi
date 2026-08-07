"""Test thật trên Postgres cho /brand-profile.

Đây là domain đầu tiên dùng `WorkspaceDep` (workspace đọc từ JWT, không phải path
param), nên cũng là nơi test được: chưa onboarding thì bị chặn, và hai workspace
không đọc thấy profile của nhau.
"""

from httpx import AsyncClient


async def _sign_up_and_login(
    client: AsyncClient, *, name: str = "Chị Hương", phone: str
) -> dict:
    signup = await client.post("/auth/sign-up", json={"name": name, "phone": phone})
    assert signup.status_code == 202, signup.text
    login = await client.post(
        "/auth/otp/verify", json={"phone": phone, "code": signup.json()["debug_code"]}
    )
    assert login.status_code == 200, login.text
    return login.json()


async def _onboard(client: AsyncClient, *, phone: str, name: str, industry: str) -> dict:
    """Đăng ký → tạo workspace → refresh để JWT mang active_workspace_id."""
    token_pair = await _sign_up_and_login(client, name=name, phone=phone)
    create = await client.post(
        "/workspaces",
        json={"name": f"Tiệm {name}", "industry": industry},
        headers={"Authorization": f"Bearer {token_pair['access_token']}"},
    )
    assert create.status_code == 201, create.text
    refreshed = await client.post(
        "/auth/refresh", json={"refresh_token": token_pair["refresh_token"]}
    )
    assert refreshed.status_code == 200, refreshed.text
    return refreshed.json()


def _headers(token_pair: dict) -> dict:
    return {"Authorization": f"Bearer {token_pair['access_token']}"}


async def test_get_lan_dau_tu_tao_profile_rong_theo_nganh_workspace(client: AsyncClient):
    token_pair = await _onboard(
        client, phone="0920000001", name="Hương", industry="spa"
    )

    response = await client.get("/brand-profile", headers=_headers(token_pair))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["workspace_id"] == token_pair["active_workspace_id"]
    assert body["industry"] == "spa"
    assert body["tone"] == ""
    assert body["banned_claims"] == []
    assert body["faq"] == []


async def test_chua_co_workspace_thi_bi_chan_409(client: AsyncClient):
    # Đăng ký xong nhưng chưa tạo workspace — active_workspace_id vẫn None.
    token_pair = await _sign_up_and_login(client, phone="0920000002")
    assert token_pair["needs_onboarding"] is True

    response = await client.get("/brand-profile", headers=_headers(token_pair))
    assert response.status_code == 409


async def test_put_ghi_duoc_tone_banned_claims_va_faq(client: AsyncClient):
    token_pair = await _onboard(
        client, phone="0920000003", name="Hương", industry="spa"
    )
    headers = _headers(token_pair)

    update = await client.put(
        "/brand-profile",
        json={
            "tone": "thân thiện, gọi khách là chị/em",
            "banned_claims": ["cam kết 100%", "trắng da sau 1 lần"],
            "faq": [
                {"question": "Giờ mở cửa?", "answer": "8h-20h mỗi ngày", "approved": True},
                {"question": "Có giữ xe?", "answer": "Có, miễn phí", "approved": False},
            ],
            "brand_colors": ["#D4956F", "#2C2C2C"],
        },
        headers=headers,
    )
    assert update.status_code == 200, update.text
    body = update.json()
    assert body["tone"] == "thân thiện, gọi khách là chị/em"
    assert body["banned_claims"] == ["cam kết 100%", "trắng da sau 1 lần"]
    assert len(body["faq"]) == 2
    assert body["faq"][0]["approved"] is True
    assert body["faq"][1]["approved"] is False
    assert body["brand_colors"] == ["#D4956F", "#2C2C2C"]


async def test_put_ghi_xong_get_doc_lai_dung_du_lieu(client: AsyncClient):
    token_pair = await _onboard(
        client, phone="0920000004", name="Hương", industry="food_beverage"
    )
    headers = _headers(token_pair)

    await client.put("/brand-profile", json={"tone": "vui vẻ"}, headers=headers)

    response = await client.get("/brand-profile", headers=headers)
    assert response.status_code == 200
    assert response.json()["tone"] == "vui vẻ"
    assert response.json()["industry"] == "food_beverage"


async def test_put_field_khong_gui_thi_giu_nguyen_gia_tri_cu(client: AsyncClient):
    token_pair = await _onboard(
        client, phone="0920000005", name="Hương", industry="spa"
    )
    headers = _headers(token_pair)

    await client.put(
        "/brand-profile",
        json={"tone": "trang trọng", "banned_claims": ["cam kết 100%"]},
        headers=headers,
    )
    # Chỉ đổi tone — banned_claims phải còn nguyên, không bị xoá về [].
    second = await client.put("/brand-profile", json={"tone": "thân thiện"}, headers=headers)
    assert second.status_code == 200
    assert second.json()["tone"] == "thân thiện"
    assert second.json()["banned_claims"] == ["cam kết 100%"]


async def test_hai_workspace_khong_doc_thay_profile_cua_nhau(client: AsyncClient):
    token_a = await _onboard(client, phone="0920000006", name="A", industry="spa")
    token_b = await _onboard(
        client, phone="0920000007", name="B", industry="real_estate"
    )

    await client.put(
        "/brand-profile", json={"tone": "giọng của tiệm A"}, headers=_headers(token_a)
    )

    profile_b = await client.get("/brand-profile", headers=_headers(token_b))
    assert profile_b.status_code == 200
    assert profile_b.json()["workspace_id"] == token_b["active_workspace_id"]
    assert profile_b.json()["tone"] == ""
    assert profile_b.json()["industry"] == "real_estate"


async def test_khong_co_token_tra_401(client: AsyncClient):
    assert (await client.get("/brand-profile")).status_code == 401
    assert (await client.put("/brand-profile", json={"tone": "x"})).status_code == 401
