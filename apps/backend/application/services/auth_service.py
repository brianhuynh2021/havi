"""Use case cho /auth/* — email + mật khẩu là kênh duy nhất tạo/đăng nhập tài khoản.

SĐT là field tuỳ chọn, chỉ để gửi bản nháp qua Zalo OA — không dùng để đăng nhập
(OTP SMS ở VN tốn phí thật, ăn vào margin gói 299K/tháng).

Ném exception thuần (không phải HTTPException) để giữ layer này không phụ thuộc
FastAPI — router (`api/routers/auth.py`) là nơi dịch sang HTTP status, giống cách
`core/content_state.py` + `api/errors.transition_conflict` đã làm.
"""

import hmac
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from adapters.persistence.event_log_repository import EventLogRepository
from adapters.persistence.otp_repository import OtpRepository
from adapters.persistence.refresh_session_repository import RefreshSessionRepository
from adapters.persistence.user_repository import UserRepository
from adapters.persistence.workspace_member_repository import WorkspaceMemberRepository
from adapters.persistence.workspace_repository import WorkspaceRepository
from core.config import Settings
from core.enums import WorkspaceRole
from core.events import EventLogEntry
from core.phone import InvalidPhoneNumber, normalize_vietnamese_phone
from core.security import (
    create_access_token,
    generate_otp_code,
    generate_refresh_token,
    hash_otp_code,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from domain.models.user import User
from domain.ports.email import EmailSender


class EmailAlreadyRegistered(Exception):
    pass


class InvalidCredentials(Exception):
    """Dùng chung cho "email không tồn tại" và "sai mật khẩu" — không tiết lộ
    email nào đã đăng ký (user enumeration)."""


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


class PhoneAlreadyUsed(Exception):
    pass


class CannotDeleteUserWithOwnedWorkspaces(Exception):
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
        email_sender: EmailSender,
        members: WorkspaceMemberRepository | None = None,
        workspaces: WorkspaceRepository | None = None,
        events: EventLogRepository | None = None,
    ) -> None:
        self._users = users
        self._otp_challenges = otp_challenges
        self._refresh_sessions = refresh_sessions
        self._settings = settings
        self._email_sender = email_sender
        self._members = members
        self._workspaces = workspaces
        self._events = events

    async def sign_up(self, *, name: str, email: str, password: str) -> TokenPairResult:
        """Đăng ký xong đăng nhập luôn — email chưa cần xác minh để dùng app.

        (Khác luồng SĐT+OTP cũ: ở đó phải verify OTP mới cấp token vì cần chứng
        minh sở hữu số. Với email+password, mật khẩu chính là bằng chứng.)
        """
        normalized_email = self._normalize_email(email)
        if await self._users.get_by_email(normalized_email) is not None:
            raise EmailAlreadyRegistered()
        user = await self._users.create(
            email=normalized_email, name=name, password_hash=hash_password(password)
        )
        return await self._issue_token_pair(user)

    async def login_with_email(self, *, email: str, password: str) -> TokenPairResult:
        user = await self._users.get_by_email(self._normalize_email(email))
        if user is None or user.password_hash is None:
            raise InvalidCredentials()
        if not verify_password(password, user.password_hash):
            raise InvalidCredentials()
        return await self._issue_token_pair(user)

    async def social_sign_in(self, *, provider: str, email: str, name: str) -> TokenPairResult:
        normalized_email = self._normalize_email(email)
        user = await self._users.get_by_email(normalized_email)
        if user is None:
            user = await self._users.create(
                email=normalized_email,
                name=name or normalized_email.split("@")[0],
                password_hash=hash_password(
                    f"social_{provider}_{normalized_email}_{self._settings.secret_key}"
                ),
            )
        return await self._issue_token_pair(user)

    async def request_password_reset(self, *, email: str) -> OtpChallengeResult:
        """Không tiết lộ email có tồn tại hay không — luôn trả về challenge giống nhau.

        Với email chưa đăng ký thì không tạo challenge (không gửi mail), nhưng
        response vẫn như thành công để tránh user enumeration.
        """
        normalized_email = self._normalize_email(email)
        cooldown = self._settings.otp_resend_cooldown_seconds
        ttl = self._settings.otp_ttl_seconds

        if await self._users.get_by_email(normalized_email) is None:
            return OtpChallengeResult(resend_after_seconds=cooldown, expires_in_seconds=ttl)

        latest = await self._otp_challenges.get_latest_for_email(normalized_email)
        if latest is not None:
            elapsed = (datetime.now(UTC) - latest.created_at).total_seconds()
            if elapsed < cooldown:
                raise OtpRateLimited(retry_after_seconds=int(cooldown - elapsed))

        code = generate_otp_code()
        await self._otp_challenges.create(
            email=normalized_email,
            code_hash=hash_otp_code(code, normalized_email, self._settings),
            expires_at=datetime.now(UTC) + timedelta(seconds=ttl),
        )
        await self._email_sender.send_password_reset_code(
            email=normalized_email,
            code=code,
            expires_in_seconds=ttl,
        )
        return OtpChallengeResult(
            resend_after_seconds=cooldown,
            expires_in_seconds=ttl,
            debug_code=code if self._settings.expose_debug_codes else None,
        )

    async def confirm_password_reset(
        self, *, email: str, code: str, new_password: str
    ) -> TokenPairResult:
        normalized_email = self._normalize_email(email)
        challenge = await self._otp_challenges.get_active_for_email(normalized_email)
        if challenge is None:
            raise OtpInvalidOrExpired()
        if challenge.attempt_count >= self._settings.otp_max_attempts:
            raise OtpTooManyAttempts()

        expected_hash = hash_otp_code(code, normalized_email, self._settings)
        if not hmac.compare_digest(expected_hash, challenge.code_hash):
            await self._otp_challenges.increment_attempt(challenge)
            raise OtpInvalidOrExpired()

        await self._otp_challenges.consume(challenge)
        user = await self._users.get_by_email(normalized_email)
        if user is None:
            # Không nên xảy ra: challenge chỉ tạo cho email đã đăng ký.
            raise OtpInvalidOrExpired()
        await self._users.set_password_hash(user, hash_password(new_password))
        return await self._issue_token_pair(user)

    async def set_phone(self, *, user_id: UUID, phone: str) -> User:
        """SĐT tuỳ chọn cho Zalo OA — vẫn unique để một số không gắn 2 tài khoản."""
        try:
            normalized = normalize_vietnamese_phone(phone)
        except InvalidPhoneNumber as exc:
            raise InvalidPhoneFormat() from exc

        existing = await self._users.get_by_phone(normalized)
        if existing is not None and existing.id != user_id:
            raise PhoneAlreadyUsed()

        user = await self._users.get_by_id(user_id)
        if user is None:
            raise InvalidCredentials()
        await self._users.set_phone(user, normalized)
        return user

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

    async def logout(self, *, refresh_token: str) -> None:
        token_hash = hash_refresh_token(refresh_token)
        session_row = await self._refresh_sessions.get_active_by_token_hash(token_hash)
        if session_row is not None:
            await self._refresh_sessions.revoke(session_row)

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

    async def delete_user_account(self, *, user_id: UUID) -> None:
        user = await self._users.get_by_id(user_id)
        if user is None:
            return

        if self._members is not None and self._workspaces is not None:
            memberships = await self._members.list_for_user(user_id)
            for m in memberships:
                if m.role == WorkspaceRole.OWNER:
                    total_members = await self._members.count_members(m.workspace_id)
                    total_owners = await self._members.count_owners(m.workspace_id)
                    if total_members <= 1:
                        await self._workspaces.delete_workspace_cascade(m.workspace_id)
                    elif total_owners <= 1:
                        raise CannotDeleteUserWithOwnedWorkspaces()

            await self._members.remove_all_for_user(user_id)

        await self._refresh_sessions.delete_all_for_user(user_id)

        if self._events is not None:
            await self._events.record(
                EventLogEntry(
                    workspace_id=None,
                    job_kind="consent.user_account_deleted",
                    input_summary=f"user_id={user_id} email={user.email}",
                )
            )

        await self._users.delete(user)

    @staticmethod
    def _normalize_email(email: str) -> str:
        """Lowercase để "Huong@x.vn" và "huong@x.vn" không tạo 2 tài khoản."""
        return email.strip().lower()
