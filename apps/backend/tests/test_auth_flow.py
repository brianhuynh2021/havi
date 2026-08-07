"""Test end-to-end thật trên Postgres (docker compose up -d) — không mock DB.

Mỗi test rollback transaction riêng (xem conftest.py) nên không cần dọn dữ liệu.
"""

from httpx import AsyncClient


async def _sign_up(client: AsyncClient, *, name: str = "Chị Hương", phone: str = "0912345678"):
    response = await client.post("/auth/sign-up", json={"name": name, "phone": phone})
    assert response.status_code == 202, response.text
    return response.json()


async def test_sign_up_tra_ve_otp_challenge_co_debug_code(client: AsyncClient):
    body = await _sign_up(client)
    assert body["expires_in_seconds"] == 300
    assert body["resend_after_seconds"] == 30
    assert body["debug_code"] is not None
    assert len(body["debug_code"]) == 6


async def test_sign_up_trung_so_dien_thoai_tra_409(client: AsyncClient):
    await _sign_up(client, phone="0987654321")
    response = await client.post(
        "/auth/sign-up", json={"name": "Người khác", "phone": "0987654321"}
    )
    assert response.status_code == 409


async def test_sign_up_gui_lai_qua_nhanh_bi_429(client: AsyncClient):
    await _sign_up(client, phone="0911111111")
    response = await client.post(
        "/auth/otp/request", json={"phone": "0911111111"}
    )
    assert response.status_code == 429


async def test_verify_otp_sai_ma_tra_400(client: AsyncClient):
    await _sign_up(client, phone="0922222222")
    response = await client.post(
        "/auth/otp/verify", json={"phone": "0922222222", "code": "000000"}
    )
    assert response.status_code == 400


async def test_verify_otp_dung_ma_tra_token_va_needs_onboarding(client: AsyncClient):
    challenge = await _sign_up(client, phone="0933333333")
    response = await client.post(
        "/auth/otp/verify", json={"phone": "0933333333", "code": challenge["debug_code"]}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["needs_onboarding"] is True
    assert body["access_token"]
    assert body["refresh_token"]


async def test_verify_otp_da_dung_khong_the_dung_lai(client: AsyncClient):
    challenge = await _sign_up(client, phone="0944444444")
    code = challenge["debug_code"]
    first = await client.post(
        "/auth/otp/verify", json={"phone": "0944444444", "code": code}
    )
    assert first.status_code == 200

    second = await client.post(
        "/auth/otp/verify", json={"phone": "0944444444", "code": code}
    )
    assert second.status_code == 400


async def test_me_tra_dung_thong_tin_user_da_dang_nhap(client: AsyncClient):
    challenge = await _sign_up(client, name="Chị Mai", phone="0955555555")
    login = await client.post(
        "/auth/otp/verify", json={"phone": "0955555555", "code": challenge["debug_code"]}
    )
    access_token = login.json()["access_token"]

    response = await client.get(
        "/auth/me", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["name"] == "Chị Mai"
    assert body["phone"] == "+84955555555"
    assert body["active_workspace_id"] is None


async def test_me_khong_co_token_tra_401(client: AsyncClient):
    response = await client.get("/auth/me")
    assert response.status_code == 401


async def test_refresh_xoay_vong_token_cu_khong_dung_lai_duoc(client: AsyncClient):
    challenge = await _sign_up(client, phone="0966666666")
    login = await client.post(
        "/auth/otp/verify", json={"phone": "0966666666", "code": challenge["debug_code"]}
    )
    old_refresh_token = login.json()["refresh_token"]

    refreshed = await client.post("/auth/refresh", json={"refresh_token": old_refresh_token})
    assert refreshed.status_code == 200, refreshed.text
    assert refreshed.json()["refresh_token"] != old_refresh_token

    reused = await client.post("/auth/refresh", json={"refresh_token": old_refresh_token})
    assert reused.status_code == 401


async def test_request_otp_cho_so_chua_dang_ky_tra_404(client: AsyncClient):
    response = await client.post("/auth/otp/request", json={"phone": "0999999999"})
    assert response.status_code == 404


async def test_sign_up_so_dien_thoai_sai_format_tra_400(client: AsyncClient):
    # Đủ dài để qua Pydantic min_length=9 (422), nhưng sai format Việt Nam thật
    # (không bắt đầu bằng 0 hoặc +84) — phải bị chặn ở tầng service, không phải schema.
    response = await client.post("/auth/sign-up", json={"name": "A", "phone": "1123456789"})
    assert response.status_code == 400
