"""Use case cho /auth/* — OTP là kênh chính, JWT access + refresh token xoay vòng.

Ném exception thuần (không phải HTTPException) để giữ layer này không phụ thuộc
FastAPI — router (`api/routers/auth.py`) là nơi dịch sang HTTP status, giống cách
`core/content_state.py` + `api/errors.transition_conflict` đã làm.
"""

import hmac
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from adapters.persistence.otp_repository import OtpRepository
from adapters.persistence.refresh_session_repository import RefreshSessionRepository
from adapters.persistence.user_repository import UserRepository
from core.config import Settings
from core.phone import InvalidPhoneNumber, normalize_vietnamese_phone
from core.security import (
    create_access_token,
    generate_otp_code,
    generate_refresh_token,
    hash_otp_code,
    hash_refresh_token,
)
from domain.models.user import User


class PhoneAlreadyRegistered(Exception):
    pass


class PhoneNotRegistered(Exception):
    pass


class OtpRateLimited(Exception):
    def __init__(self, retry_after_seconds: int) -> None:
        self.retry_after_seconds = retry_after_seconds


class OtpInvalidOrExpired(Exception):
    pass


class OtpTooManyAttempts(Exception):
    pass


class RefreshTokenInvalid(Exception):
    pass


class InvalidPhoneFormat(Exception):
    pass


@dataclass
class OtpChallengeResult:
    resend_after_seconds: int
    expires_in_seconds: int
    debug_code: str | None = None


@dataclass
class TokenPairResult:
    access_token: str
    refresh_token: str
    active_workspace_id: UUID | None
    needs_onboarding: bool


class AuthService:
    def __init__(
        self,
        *,
        users: UserRepository,
        otp_challenges: OtpRepository,
        refresh_sessions: RefreshSessionRepository,
        settings: Settings,
    ) -> None:
        self._users = users
        self._otp_challenges = otp_challenges
        self._refresh_sessions = refresh_sessions
        self._settings = settings

    async def sign_up(self, *, name: str, phone: str) -> OtpChallengeResult:
        normalized = self._normalize_or_raise(phone)
        if await self._users.get_by_phone(normalized) is not None:
            raise PhoneAlreadyRegistered()
        await self._users.create(phone=normalized, name=name)
        return await self._issue_otp_challenge(normalized)

    async def request_otp(self, *, phone: str) -> OtpChallengeResult:
        normalized = self._normalize_or_raise(phone)
        if await self._users.get_by_phone(normalized) is None:
            raise PhoneNotRegistered()
        return await self._issue_otp_challenge(normalized)

    async def _issue_otp_challenge(self, phone: str) -> OtpChallengeResult:
        cooldown = self._settings.otp_resend_cooldown_seconds
        latest = await self._otp_challenges.get_latest_for_phone(phone)
        if latest is not None:
            elapsed = (datetime.now(UTC) - latest.created_at).total_seconds()
            if elapsed < cooldown:
                raise OtpRateLimited(retry_after_seconds=int(cooldown - elapsed))

        code = generate_otp_code()
        code_hash = hash_otp_code(code, phone, self._settings)
        ttl = self._settings.otp_ttl_seconds
        await self._otp_challenges.create(
            phone=phone,
            code_hash=code_hash,
            expires_at=datetime.now(UTC) + timedelta(seconds=ttl),
        )
        return OtpChallengeResult(
            resend_after_seconds=cooldown,
            expires_in_seconds=ttl,
            debug_code=code if self._settings.debug else None,
        )

    async def verify_otp(self, *, phone: str, code: str) -> TokenPairResult:
        normalized = self._normalize_or_raise(phone)
        challenge = await self._otp_challenges.get_active_for_phone(normalized)
        if challenge is None:
            raise OtpInvalidOrExpired()
        if challenge.attempt_count >= self._settings.otp_max_attempts:
            raise OtpTooManyAttempts()

        expected_hash = hash_otp_code(code, normalized, self._settings)
        if not hmac.compare_digest(expected_hash, challenge.code_hash):
            await self._otp_challenges.increment_attempt(challenge)
            raise OtpInvalidOrExpired()

        await self._otp_challenges.consume(challenge)
        user = await self._users.get_by_phone(normalized)
        if user is None:
            # Không nên xảy ra: challenge chỉ tạo sau khi user đã tồn tại.
            raise PhoneNotRegistered()
        return await self._issue_token_pair(user)

    async def get_user_by_id(self, user_id: UUID) -> User | None:
        return await self._users.get_by_id(user_id)

    async def refresh(self, *, refresh_token: str) -> TokenPairResult:
        token_hash = hash_refresh_token(refresh_token)
        session_row = await self._refresh_sessions.get_active_by_token_hash(token_hash)
        if session_row is None:
            raise RefreshTokenInvalid()
        await self._refresh_sessions.revoke(session_row)  # rotate — không tái sử dụng

        user = await self._users.get_by_id(session_row.user_id)
        if user is None:
            raise RefreshTokenInvalid()
        return await self._issue_token_pair(user)

    async def issue_token_pair(self, user: User) -> TokenPairResult:
        """Public — WorkspaceService gọi lại khi activate workspace đổi active_workspace_id."""
        return await self._issue_token_pair(user)

    async def _issue_token_pair(self, user: User) -> TokenPairResult:
        access_token = create_access_token(
            user_id=user.id,
            active_workspace_id=user.active_workspace_id,
            settings=self._settings,
        )
        raw_refresh_token = generate_refresh_token()
        await self._refresh_sessions.create(
            user_id=user.id,
            token_hash=hash_refresh_token(raw_refresh_token),
            expires_at=datetime.now(UTC) + timedelta(days=self._settings.refresh_token_ttl_days),
        )
        return TokenPairResult(
            access_token=access_token,
            refresh_token=raw_refresh_token,
            active_workspace_id=user.active_workspace_id,
            needs_onboarding=user.active_workspace_id is None,
        )

    def _normalize_or_raise(self, phone: str) -> str:
        try:
            return normalize_vietnamese_phone(phone)
        except InvalidPhoneNumber as exc:
            raise InvalidPhoneFormat() from exc
