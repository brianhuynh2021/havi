"""Mã hoá token nền tảng trước khi lưu DB.

Token Facebook/Zalo/Google là chìa khoá đăng bài lên trang của chủ tiệm. Lộ một
token nghĩa là người khác đăng được lên Fanpage của họ — nên nó không được nằm
plaintext trong database, kể cả khi ai đó có bản dump.

Dùng Fernet (AES-128-CBC + HMAC-SHA256) chứ không tự ghép AES: Fernet gói sẵn
IV ngẫu nhiên mỗi lần mã hoá, HMAC để phát hiện bản mã bị sửa, và timestamp —
ba thứ dễ làm sai nhất khi tự cuộn. Mã hoá cùng một token hai lần ra hai chuỗi
khác nhau, nên không thể so sánh bản mã để đoán token trùng.

Khoá đọc từ `HAVI_TOKEN_ENCRYPTION_KEY`. Đổi khoá thì token cũ giải mã không
được nữa — chủ tiệm phải nối lại kênh. Vì vậy khoá phải nằm trong secret
manager và có kế hoạch xoay vòng (ROADMAP §3 "Secret management và token
encryption key rotation plan").
"""

from cryptography.fernet import Fernet, InvalidToken

from core.config import get_settings


class TokenEncryptionUnavailable(RuntimeError):
    """Chưa cấu hình khoá mã hoá.

    Ném lỗi thay vì lưu plaintext: thà không nối được kênh còn hơn ghi token
    trần vào DB rồi không ai biết.
    """


class TokenDecryptionFailed(RuntimeError):
    """Bản mã sai khoá hoặc đã bị sửa."""


def _cipher() -> Fernet:
    key = get_settings().token_encryption_key
    if not key:
        raise TokenEncryptionUnavailable(
            "Chưa đặt HAVI_TOKEN_ENCRYPTION_KEY — không thể lưu token nền tảng. "
            "Sinh khoá bằng: python -c "
            "'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
        )
    try:
        return Fernet(key.encode())
    except (ValueError, TypeError) as exc:
        raise TokenEncryptionUnavailable(
            "HAVI_TOKEN_ENCRYPTION_KEY không đúng định dạng Fernet (cần 32 byte urlsafe-base64)"
        ) from exc


def encrypt_token(plaintext: str) -> str:
    """Mã hoá token để lưu DB. Trả chuỗi urlsafe-base64."""
    return _cipher().encrypt(plaintext.encode()).decode()


def decrypt_token(ciphertext: str) -> str:
    """Giải mã token đọc từ DB.

    Ném `TokenDecryptionFailed` khi sai khoá hoặc bản mã bị sửa — nơi gọi phải
    coi kết nối đó là hỏng và bắt chủ tiệm nối lại, không được im lặng bỏ qua.
    """
    try:
        return _cipher().decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:
        raise TokenDecryptionFailed(
            "Không giải mã được token — sai khoá mã hoá hoặc dữ liệu đã hỏng"
        ) from exc


def is_encryption_configured() -> bool:
    """Cho health check / startup báo sớm thay vì đợi user bấm nối kênh mới lỗi."""
    try:
        _cipher()
    except TokenEncryptionUnavailable:
        return False
    return True
