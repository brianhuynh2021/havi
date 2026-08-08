"""Mã hoá token nền tảng và signed OAuth state.

Hai lớp này bảo vệ chìa khoá đăng bài lên Fanpage của chủ tiệm. Lộ token nghĩa
là người khác đăng được lên trang của họ, nên test ở đây kiểm cả đường thành
công lẫn mọi cách tấn công đã lường trước.
"""

import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from cryptography.fernet import Fernet

from core.config import Settings
from core.enums import Platform
from core.oauth_state import (
    InvalidOAuthState,
    create_oauth_state,
    verify_oauth_state,
)
from core.token_crypto import (
    TokenDecryptionFailed,
    TokenEncryptionUnavailable,
    decrypt_token,
    encrypt_token,
    is_encryption_configured,
)


@pytest.fixture
def crypto_settings(monkeypatch):
    """Khoá Fernet thật cho mỗi test, và xoá cache của get_settings."""
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("HAVI_TOKEN_ENCRYPTION_KEY", key)
    from core.config import get_settings

    get_settings.cache_clear()
    yield key
    get_settings.cache_clear()


class TestTokenCrypto:
    def test_ma_hoa_roi_giai_ma_ra_dung_token(self, crypto_settings):
        token = "EAAGm0PX4ZCpsBA...facebook-page-token"
        assert decrypt_token(encrypt_token(token)) == token

    def test_ban_ma_khong_chua_token_goc(self, crypto_settings):
        """Chốt chặn hiển nhiên nhưng đáng test: nếu ai đó lỡ đổi sang encode
        base64 thay vì mã hoá, dump DB sẽ lộ token."""
        token = "EAAGm0PX4ZCpsBA"
        assert token not in encrypt_token(token)

    def test_ma_hoa_hai_lan_ra_hai_ban_ma_khac_nhau(self, crypto_settings):
        """Fernet random IV mỗi lần. Nếu hai bản mã giống nhau thì kẻ có quyền
        đọc DB suy ra được hai workspace đang dùng chung một token."""
        token = "cung-mot-token"
        assert encrypt_token(token) != encrypt_token(token)

    def test_sai_khoa_thi_khong_giai_ma_duoc(self, crypto_settings, monkeypatch):
        ciphertext = encrypt_token("token-cua-tiem")

        from core.config import get_settings

        monkeypatch.setenv("HAVI_TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())
        get_settings.cache_clear()

        with pytest.raises(TokenDecryptionFailed):
            decrypt_token(ciphertext)

    def test_ban_ma_bi_sua_thi_bi_tu_choi(self, crypto_settings):
        """HMAC của Fernet phải bắt được sửa đổi — không được im lặng trả rác."""
        ciphertext = encrypt_token("token-goc")
        tampered = ciphertext[:-4] + ("AAAA" if not ciphertext.endswith("AAAA") else "BBBB")

        with pytest.raises(TokenDecryptionFailed):
            decrypt_token(tampered)

    def test_chua_cau_hinh_khoa_thi_nem_loi_chu_khong_luu_plaintext(self, monkeypatch):
        """Thà không nối được kênh còn hơn ghi token trần vào DB."""
        from core.config import get_settings

        monkeypatch.setenv("HAVI_TOKEN_ENCRYPTION_KEY", "")
        get_settings.cache_clear()

        assert is_encryption_configured() is False
        with pytest.raises(TokenEncryptionUnavailable):
            encrypt_token("token")
        get_settings.cache_clear()

    def test_khoa_sai_dinh_dang_bao_loi_ro_rang(self, monkeypatch):
        from core.config import get_settings

        monkeypatch.setenv("HAVI_TOKEN_ENCRYPTION_KEY", "khoa-bay-ba-khong-phai-fernet")
        get_settings.cache_clear()

        with pytest.raises(TokenEncryptionUnavailable, match="Fernet"):
            encrypt_token("token")
        get_settings.cache_clear()


def _settings() -> Settings:
    return Settings(jwt_secret="test-secret-cho-oauth-state", token_encryption_key="")


class TestOAuthState:
    def test_state_hop_le_giai_ra_dung_workspace_va_user(self):
        s = _settings()
        ws, user = uuid.uuid4(), uuid.uuid4()

        state = create_oauth_state(
            workspace_id=ws, user_id=user, platform=Platform.FACEBOOK, settings=s
        )
        payload = verify_oauth_state(state, platform=Platform.FACEBOOK, settings=s)

        assert payload.workspace_id == ws
        assert payload.user_id == user
        assert payload.platform is Platform.FACEBOOK

    def test_state_cua_platform_khac_bi_tu_choi(self):
        """Chống dùng lại state phát cho Facebook ở callback Zalo — nếu không,
        một lần cấp quyền Facebook mở đường nối nhầm kênh khác."""
        s = _settings()
        state = create_oauth_state(
            workspace_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            platform=Platform.FACEBOOK,
            settings=s,
        )

        with pytest.raises(InvalidOAuthState, match="không khớp nền tảng"):
            verify_oauth_state(state, platform=Platform.ZALO_OA, settings=s)

    def test_state_ky_bang_khoa_khac_bi_tu_choi(self):
        """Đây chính là lớp chống CSRF: kẻ tấn công không ký được state hợp lệ."""
        attacker = Settings(jwt_secret="khoa-cua-ke-tan-cong", token_encryption_key="")
        state = create_oauth_state(
            workspace_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            platform=Platform.FACEBOOK,
            settings=attacker,
        )

        with pytest.raises(InvalidOAuthState):
            verify_oauth_state(state, platform=Platform.FACEBOOK, settings=_settings())

    def test_state_het_han_bi_tu_choi_voi_thong_bao_de_hieu(self):
        """Link callback bị chụp lại phải hết hạn nhanh."""
        s = _settings()
        expired = jwt.encode(
            {
                "aud": "havi:oauth-state",
                "ws": str(uuid.uuid4()),
                "sub": str(uuid.uuid4()),
                "plt": Platform.FACEBOOK.value,
                "iat": datetime.now(UTC) - timedelta(hours=2),
                "exp": datetime.now(UTC) - timedelta(hours=1),
            },
            s.jwt_secret,
            algorithm=s.jwt_algorithm,
        )

        with pytest.raises(InvalidOAuthState, match="hết hạn"):
            verify_oauth_state(expired, platform=Platform.FACEBOOK, settings=s)

    def test_access_token_khong_dung_duoc_lam_oauth_state(self):
        """Cùng khoá ký, nên phải phân biệt bằng `aud`. Thiếu chỗ này thì một
        access token hợp lệ lọt qua được kiểm tra state."""
        from core.security import create_access_token

        s = _settings()
        access = create_access_token(
            user_id=uuid.uuid4(), active_workspace_id=uuid.uuid4(), settings=s
        )

        with pytest.raises(InvalidOAuthState):
            verify_oauth_state(access, platform=Platform.FACEBOOK, settings=s)

    def test_hai_lan_goi_ra_hai_state_khac_nhau(self):
        """Nonce: hai lần bấm nối kênh không sinh state giống hệt."""
        s = _settings()
        ws, user = uuid.uuid4(), uuid.uuid4()
        args = {"workspace_id": ws, "user_id": user, "platform": Platform.FACEBOOK, "settings": s}

        assert create_oauth_state(**args) != create_oauth_state(**args)

    def test_state_rac_bi_tu_choi(self):
        with pytest.raises(InvalidOAuthState):
            verify_oauth_state("khong-phai-jwt", platform=Platform.FACEBOOK, settings=_settings())
