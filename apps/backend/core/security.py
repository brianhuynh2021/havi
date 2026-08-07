"""JWT access token, hash OTP và hash refresh token.

Không dùng bcrypt/passlib cho OTP — mã 6 số sống rất ngắn (otp_ttl_seconds) và bị
chặn brute-force bằng attempt_count, không cần cost factor cao như password.
Refresh token là chuỗi ngẫu nhiên entropy cao (secrets.token_urlsafe) nên hash
thường (sha256) là đủ — khác với password người dùng tự chọn (entropy thấp).
"""

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt

from core.config import Settings


def hash_otp_code(code: str, phone: str, settings: Settings) -> str:
    message = f"{phone}:{code}".encode()
    return hmac.new(settings.jwt_secret.encode(), message, hashlib.sha256).hexdigest()


def generate_otp_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(32)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_access_token(
    *, user_id: UUID, active_workspace_id: UUID | None, settings: Settings
) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "active_workspace_id": str(active_workspace_id) if active_workspace_id else None,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_ttl_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


class DecodedAccessToken:
    def __init__(self, user_id: UUID, active_workspace_id: UUID | None) -> None:
        self.user_id = user_id
        self.active_workspace_id = active_workspace_id


def decode_access_token(token: str, settings: Settings) -> DecodedAccessToken:
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    workspace_id = payload.get("active_workspace_id")
    return DecodedAccessToken(
        user_id=UUID(payload["sub"]),
        active_workspace_id=UUID(workspace_id) if workspace_id else None,
    )
