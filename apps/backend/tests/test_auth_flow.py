"""Test end-to-end thật trên Postgres (docker compose up -d) — không mock DB.

Mỗi test rollback transaction riêng (xem conftest.py) nên không cần dọn dữ liệu.
"""

from httpx import AsyncClient

from adapters.persistence.otp_repository import OtpRepository
from adapters.persistence.refresh_session_repository import RefreshSessionRepository
from adapters.persistence.user_repository import UserRepository
from application.services.auth_service import AuthService
from core.config import Settings

PASSWORD = "matkhau123"


class RecordingEmailSender:
    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def send_password_reset_code(
        self, *, email: str, code: str, expires_in_seconds: int
    ) -> None:
        self.sent.append({"email": email, "code": code, "expires_in_seconds": expires_in_seconds})


async def _sign_up(
    client: AsyncClient,
    *,
    name: str = "Chị Hương",
    email: str = "huong@spaannhien.vn",
    password: str = PASSWORD,
) -> dict:
    response = await client.post(
        "/auth/sign-up", json={"name": name, "email": email, "password": password}
    )
    assert response.status_code == 201, response.text
    return response.json()


def _headers(token_pair: dict) -> dict:
    return {"Authorization": f"Bearer {token_pair['access_token']}"}


async def test_sign_up_tra_token_va_needs_onboarding(client: AsyncClient):
    body = await _sign_up(client, email="a1@havi.vn")
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["needs_onboarding"] is True
    assert body["active_workspace_id"] is None


async def test_sign_up_trung_email_tra_409(client: AsyncClient):
    await _sign_up(client, email="a2@havi.vn")
    response = await client.post(
        "/auth/sign-up",
        json={"name": "Người khác", "email": "a2@havi.vn", "password": PASSWORD},
    )
    assert response.status_code == 409


async def test_email_khong_phan_biet_chu_hoa_chu_thuong(client: AsyncClient):
    await _sign_up(client, email="a3@havi.vn")
    # "A3@Havi.vn" phải bị coi là cùng một email, không tạo tài khoản thứ hai.
    response = await client.post(
        "/auth/sign-up",
        json={"name": "Người khác", "email": "A3@Havi.vn", "password": PASSWORD},
    )
    assert response.status_code == 409


async def test_sign_up_email_sai_format_tra_422(client: AsyncClient):
    response = await client.post(
        "/auth/sign-up", json={"name": "A", "email": "khong-phai-email", "password": PASSWORD}
    )
    assert response.status_code == 422


async def test_sign_up_mat_khau_qua_ngan_tra_422(client: AsyncClient):
    response = await client.post(
        "/auth/sign-up", json={"name": "A", "email": "a4@havi.vn", "password": "123"}
    )
    assert response.status_code == 422


async def test_login_dung_mat_khau_tra_token(client: AsyncClient):
    await _sign_up(client, email="a5@havi.vn")
    response = await client.post(
        "/auth/login/email", json={"email": "a5@havi.vn", "password": PASSWORD}
    )
    assert response.status_code == 200, response.text
    assert response.json()["access_token"]


async def test_login_sai_mat_khau_tra_401(client: AsyncClient):
    await _sign_up(client, email="a6@havi.vn")
    response = await client.post(
        "/auth/login/email", json={"email": "a6@havi.vn", "password": "saibetbet"}
    )
    assert response.status_code == 401


async def test_login_email_chua_dang_ky_tra_401_giong_sai_mat_khau(client: AsyncClient):
    """Không được phân biệt — nếu khác nhau thì người ngoài dò được email nào đã đăng ký."""
    await _sign_up(client, email="a7@havi.vn")
    wrong_password = await client.post(
        "/auth/login/email", json={"email": "a7@havi.vn", "password": "saibetbet"}
    )
    unknown_email = await client.post(
        "/auth/login/email", json={"email": "khongtontai@havi.vn", "password": PASSWORD}
    )
    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json()["detail"] == unknown_email.json()["detail"]


async def test_me_tra_dung_thong_tin_user(client: AsyncClient):
    token_pair = await _sign_up(client, name="Chị Mai", email="a8@havi.vn")
    response = await client.get("/auth/me", headers=_headers(token_pair))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["name"] == "Chị Mai"
    assert body["email"] == "a8@havi.vn"
    assert body["phone"] is None
    assert body["active_workspace_id"] is None


async def test_me_khong_co_token_tra_401(client: AsyncClient):
    assert (await client.get("/auth/me")).status_code == 401


async def test_refresh_xoay_vong_token_cu_khong_dung_lai_duoc(client: AsyncClient):
    token_pair = await _sign_up(client, email="a9@havi.vn")
    old_refresh_token = token_pair["refresh_token"]

    refreshed = await client.post("/auth/refresh", json={"refresh_token": old_refresh_token})
    assert refreshed.status_code == 200, refreshed.text
    assert refreshed.json()["refresh_token"] != old_refresh_token

    reused = await client.post("/auth/refresh", json={"refresh_token": old_refresh_token})
    assert reused.status_code == 401


async def test_logout_huy_refresh_token_hien_tai(client: AsyncClient):
    token_pair = await _sign_up(client, email="a10@havi.vn")
    refresh_token = token_pair["refresh_token"]

    response = await client.post("/auth/logout", json={"refresh_token": refresh_token})
    assert response.status_code == 204

    reused = await client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert reused.status_code == 401


async def test_logout_token_khong_hop_le_van_tra_204(client: AsyncClient):
    response = await client.post("/auth/logout", json={"refresh_token": "invalid-token"})
    assert response.status_code == 204


# --- Quên mật khẩu ----------------------------------------------------------


async def test_password_reset_doi_duoc_mat_khau_va_dang_nhap_luon(client: AsyncClient):
    await _sign_up(client, email="b1@havi.vn")

    request = await client.post("/auth/password-reset/request", json={"email": "b1@havi.vn"})
    assert request.status_code == 202, request.text
    code = request.json()["debug_code"]
    assert code is not None

    confirm = await client.post(
        "/auth/password-reset/confirm",
        json={"email": "b1@havi.vn", "code": code, "new_password": "matkhaumoi456"},
    )
    assert confirm.status_code == 200, confirm.text
    assert confirm.json()["access_token"]

    # Mật khẩu cũ phải hết tác dụng, mật khẩu mới phải dùng được.
    assert (
        await client.post("/auth/login/email", json={"email": "b1@havi.vn", "password": PASSWORD})
    ).status_code == 401
    assert (
        await client.post(
            "/auth/login/email", json={"email": "b1@havi.vn", "password": "matkhaumoi456"}
        )
    ).status_code == 200


async def test_password_reset_goi_email_sender_va_chi_local_moi_tra_debug_code(
    db_session,
):
    email_sender = RecordingEmailSender()
    settings = Settings(
        env="production",
        debug=True,
        use_mock_llm=False,
        use_fake_publisher=False,
        disable_rate_limit=False,
        email_provider="smtp",
        email_from="no-reply@havi.vn",
        smtp_host="smtp.havi.vn",
        smtp_username="smtp-user",
        smtp_password="smtp-password",
        database_url="postgresql+psycopg://havi:strong-password@postgres/havi",
        cors_origins=["https://app.havi.vn"],
        web_base_url="https://app.havi.vn",
        media_endpoint_url="http://minio:9000",
        media_external_endpoint_url="https://app.havi.vn",
        # Địa chỉ Facebook/TikTok/Google dùng để TẢI ảnh, nên phải công khai.
        media_public_url="https://media.havi.vn/havi-media",
        media_access_key="production-media-user",
        media_secret_key="production-media-secret",
        jwt_secret="production-jwt-secret-at-least-32-bytes-long",
        token_encryption_key="Z3A5T2I3NTRLN3Y4OTAxMjM0NTY3ODkwMTIzNDU2Nzg=",
        payment_webhook_secret="production-payment-secret-at-least-32-bytes",
        gemini_api_key="gemini-production-key",
        facebook_client_id="facebook-client-id",
        facebook_client_secret="facebook-client-secret",
        facebook_redirect_uri="https://app.havi.vn/connections/facebook/callback",
        meta_webhook_verify_token="meta-verify-token",
        payos_client_id="payos-client-id",
        payos_api_key="payos-api-key",
        payos_checksum_key="payos-checksum-key",
    )
    service = AuthService(
        users=UserRepository(db_session),
        otp_challenges=OtpRepository(db_session),
        refresh_sessions=RefreshSessionRepository(db_session),
        settings=settings,
        email_sender=email_sender,
    )

    await service.sign_up(name="Chị Lan", email="b6@havi.vn", password=PASSWORD)
    result = await service.request_password_reset(email="B6@Havi.vn")

    assert result.debug_code is None
    assert len(email_sender.sent) == 1
    assert email_sender.sent[0]["email"] == "b6@havi.vn"
    assert email_sender.sent[0]["code"]


def test_staging_thieu_email_provider_that_thi_config_fail_ro_rang():
    try:
        Settings(
            env="staging",
            debug=False,
            use_mock_llm=False,
            use_fake_publisher=False,
            disable_rate_limit=False,
            email_provider="debug",
        )
    except ValueError as exc:
        assert "HAVI_EMAIL_PROVIDER=debug" in str(exc)
    else:
        raise AssertionError("staging must reject debug email provider")


async def test_password_reset_email_chua_dang_ky_van_tra_202_khong_co_ma(client: AsyncClient):
    """Không tiết lộ email nào đã đăng ký — response giống hệt trường hợp có thật."""
    response = await client.post(
        "/auth/password-reset/request", json={"email": "khongtontai@havi.vn"}
    )
    assert response.status_code == 202
    assert response.json()["debug_code"] is None


async def test_password_reset_gui_lai_qua_nhanh_bi_429(client: AsyncClient):
    await _sign_up(client, email="b2@havi.vn")
    await client.post("/auth/password-reset/request", json={"email": "b2@havi.vn"})
    again = await client.post("/auth/password-reset/request", json={"email": "b2@havi.vn"})
    assert again.status_code == 429


async def test_password_reset_ma_sai_tra_400(client: AsyncClient):
    await _sign_up(client, email="b3@havi.vn")
    await client.post("/auth/password-reset/request", json={"email": "b3@havi.vn"})
    response = await client.post(
        "/auth/password-reset/confirm",
        json={"email": "b3@havi.vn", "code": "000000", "new_password": "matkhaumoi456"},
    )
    assert response.status_code == 400


async def test_password_reset_ma_da_dung_khong_dung_lai_duoc(client: AsyncClient):
    await _sign_up(client, email="b4@havi.vn")
    request = await client.post("/auth/password-reset/request", json={"email": "b4@havi.vn"})
    code = request.json()["debug_code"]

    first = await client.post(
        "/auth/password-reset/confirm",
        json={"email": "b4@havi.vn", "code": code, "new_password": "matkhaumoi456"},
    )
    assert first.status_code == 200

    second = await client.post(
        "/auth/password-reset/confirm",
        json={"email": "b4@havi.vn", "code": code, "new_password": "matkhaukhac789"},
    )
    assert second.status_code == 400


# --- SĐT tuỳ chọn (Zalo OA) -------------------------------------------------


async def test_them_sdt_duoc_chuan_hoa_ve_dang_quoc_te(client: AsyncClient):
    token_pair = await _sign_up(client, email="c1@havi.vn")
    response = await client.put(
        "/auth/phone", json={"phone": "0912345678"}, headers=_headers(token_pair)
    )
    assert response.status_code == 200, response.text
    assert response.json()["phone"] == "+84912345678"


async def test_them_sdt_sai_format_tra_400(client: AsyncClient):
    token_pair = await _sign_up(client, email="c2@havi.vn")
    response = await client.put(
        "/auth/phone", json={"phone": "1123456789"}, headers=_headers(token_pair)
    )
    assert response.status_code == 400


async def test_sdt_da_gan_tai_khoan_khac_tra_409(client: AsyncClient):
    first = await _sign_up(client, email="c3@havi.vn")
    second = await _sign_up(client, email="c4@havi.vn")

    assert (
        await client.put("/auth/phone", json={"phone": "0987654321"}, headers=_headers(first))
    ).status_code == 200
    response = await client.put(
        "/auth/phone", json={"phone": "0987654321"}, headers=_headers(second)
    )
    assert response.status_code == 409


async def test_doi_sdt_cua_chinh_minh_khong_bi_chan(client: AsyncClient):
    token_pair = await _sign_up(client, email="c5@havi.vn")
    headers = _headers(token_pair)
    await client.put("/auth/phone", json={"phone": "0911111111"}, headers=headers)
    # Ghi lại cùng số của chính mình — không được coi là trùng với người khác.
    again = await client.put("/auth/phone", json={"phone": "0911111111"}, headers=headers)
    assert again.status_code == 200
    assert again.json()["phone"] == "+84911111111"


async def test_them_sdt_khong_co_token_tra_401(client: AsyncClient):
    assert (await client.put("/auth/phone", json={"phone": "0912345678"})).status_code == 401
