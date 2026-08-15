"""/auth/* — email + mật khẩu là kênh duy nhất tạo/đăng nhập tài khoản.

Màn Đăng Nhập: email + mật khẩu. Đăng ký: tên + email + mật khẩu → vào Onboarding
luôn (`needs_onboarding=true`). Quên mật khẩu: nhập email → mã 6 số gửi qua email
→ đặt mật khẩu mới.

SĐT (`PUT /auth/phone`) là tuỳ chọn, chỉ để nhận bản nháp/nhắc duyệt qua Zalo OA
— không dùng để đăng nhập.
"""

from fastapi import APIRouter, HTTPException, Request, Response, status

from api.deps import AuthDep, AuthServiceDep
from api.rate_limit import limit_by_ip
from application.services.auth_service import (
    CannotDeleteUserWithOwnedWorkspaces,
    EmailAlreadyRegistered,
    InvalidCredentials,
    InvalidPhoneFormat,
    OtpInvalidOrExpired,
    OtpRateLimited,
    OtpTooManyAttempts,
    PhoneAlreadyUsed,
    RefreshTokenInvalid,
)
from core.config import get_settings
from core.schemas import (
    CurrentUser,
    EmailLoginRequest,
    HaviModel,
    PasswordResetConfirm,
    PasswordResetRequest,
    PhoneUpdateRequest,
    RefreshRequest,
    SignUpRequest,
    TokenPair,
)
from domain.policies import rate_limits

router = APIRouter(prefix="/auth", tags=["auth"])
COOKIE_NAME = "havi_refresh_token"


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        samesite="lax",
        secure=not settings.debug,
        max_age=30 * 24 * 3600,
        path="/",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=COOKIE_NAME, path="/")


class OtpChallenge(HaviModel):
    """Frontend dùng `resend_after_seconds` để chạy đồng hồ đếm ngược trên màn OTP.

    `debug_code` chỉ có giá trị ở local khi `HAVI_DEBUG=true`. Staging/production
    phải gửi email thật và không bao giờ trả mã trong API response.
    """

    resend_after_seconds: int
    expires_in_seconds: int
    debug_code: str | None = None


def _to_token_pair(result) -> TokenPair:
    return TokenPair(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        active_workspace_id=result.active_workspace_id,
        needs_onboarding=result.needs_onboarding,
    )


@router.post(
    "/sign-up",
    response_model=TokenPair,
    status_code=status.HTTP_201_CREATED,
    dependencies=[limit_by_ip("auth_login", rate_limits.AUTH_LOGIN)],
)
async def sign_up(
    payload: SignUpRequest, auth_service: AuthServiceDep, response: Response
) -> TokenPair:
    """Đăng ký xong đăng nhập luôn — mật khẩu đã là bằng chứng sở hữu tài khoản."""
    try:
        result = await auth_service.sign_up(
            name=payload.name, email=payload.email, password=payload.password
        )
    except EmailAlreadyRegistered as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Email đã có tài khoản — đăng nhập thay vì đăng ký"
        ) from exc
    res = _to_token_pair(result)
    _set_refresh_cookie(response, result.refresh_token)
    return res


@router.post(
    "/login/email",
    response_model=TokenPair,
    dependencies=[limit_by_ip("auth_login", rate_limits.AUTH_LOGIN)],
)
async def login_email(
    payload: EmailLoginRequest, auth_service: AuthServiceDep, response: Response
) -> TokenPair:
    try:
        result = await auth_service.login_with_email(email=payload.email, password=payload.password)
    except InvalidCredentials as exc:
        # Không phân biệt "email không tồn tại" và "sai mật khẩu" — tránh để
        # người ngoài dò xem email nào đã đăng ký.
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email hoặc mật khẩu không đúng") from exc
    res = _to_token_pair(result)
    _set_refresh_cookie(response, result.refresh_token)
    return res


@router.post(
    "/password-reset/request",
    response_model=OtpChallenge,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[limit_by_ip("auth_reset", rate_limits.AUTH_PASSWORD_RESET)],
)
async def request_password_reset(
    payload: PasswordResetRequest, auth_service: AuthServiceDep
) -> OtpChallenge:
    """Gửi mã 6 số qua email. Email chưa đăng ký cũng trả 202 (không tiết lộ)."""
    try:
        result = await auth_service.request_password_reset(email=payload.email)
    except OtpRateLimited as exc:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Vui lòng chờ {exc.retry_after_seconds}s trước khi gửi lại mã",
        ) from exc
    return OtpChallenge(
        resend_after_seconds=result.resend_after_seconds,
        expires_in_seconds=result.expires_in_seconds,
        debug_code=result.debug_code,
    )


@router.post(
    "/password-reset/confirm",
    response_model=TokenPair,
    dependencies=[limit_by_ip("auth_reset", rate_limits.AUTH_PASSWORD_RESET)],
)
async def confirm_password_reset(
    payload: PasswordResetConfirm, auth_service: AuthServiceDep, response: Response
) -> TokenPair:
    """Đặt mật khẩu mới rồi đăng nhập luôn — khỏi bắt user nhập lại."""
    try:
        result = await auth_service.confirm_password_reset(
            email=payload.email, code=payload.code, new_password=payload.new_password
        )
    except OtpTooManyAttempts as exc:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS, "Nhập sai quá nhiều lần — vui lòng gửi lại mã mới"
        ) from exc
    except OtpInvalidOrExpired as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Mã không đúng hoặc đã hết hạn") from exc
    res = _to_token_pair(result)
    _set_refresh_cookie(response, result.refresh_token)
    return res


@router.put("/phone", response_model=CurrentUser)
async def set_phone(
    payload: PhoneUpdateRequest, auth: AuthDep, auth_service: AuthServiceDep
) -> CurrentUser:
    """Thêm/đổi SĐT để nhận bản nháp qua Zalo OA — không phải kênh đăng nhập."""
    try:
        user = await auth_service.set_phone(user_id=auth.user_id, phone=payload.phone)
    except InvalidPhoneFormat as exc:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Số điện thoại không hợp lệ — nhập dạng 0xxxxxxxxx"
        ) from exc
    except PhoneAlreadyUsed as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Số điện thoại này đã gắn với tài khoản khác"
        ) from exc
    return CurrentUser.model_validate(user)


@router.post("/refresh", response_model=TokenPair)
async def refresh(
    request: Request,
    response: Response,
    auth_service: AuthServiceDep,
    payload: RefreshRequest | None = None,
) -> TokenPair:
    token = (
        payload.refresh_token if payload and payload.refresh_token else None
    ) or request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Refresh token không hợp lệ hoặc đã hết hạn"
        )
    try:
        result = await auth_service.refresh(refresh_token=token)
    except RefreshTokenInvalid as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Refresh token không hợp lệ hoặc đã hết hạn"
        ) from exc
    res = _to_token_pair(result)
    _set_refresh_cookie(response, result.refresh_token)
    return res


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    auth_service: AuthServiceDep,
    payload: RefreshRequest | None = None,
) -> None:
    token = (
        payload.refresh_token if payload and payload.refresh_token else None
    ) or request.cookies.get(COOKIE_NAME)
    if token:
        await auth_service.logout(refresh_token=token)
    _clear_refresh_cookie(response)


@router.get("/me", response_model=CurrentUser)
async def me(auth: AuthDep, auth_service: AuthServiceDep) -> CurrentUser:
    user = await auth_service.get_user_by_id(auth.user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy user")
    return CurrentUser.model_validate(user)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(auth: AuthDep, auth_service: AuthServiceDep, response: Response) -> None:
    """Xoá vĩnh viễn tài khoản người dùng và thu hồi mọi phiên làm việc."""
    try:
        await auth_service.delete_user_account(user_id=auth.user_id)
    except CannotDeleteUserWithOwnedWorkspaces as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Tài khoản đang là owner của workspace có thành viên khác. "
            "Vui lòng chuyển quyền owner hoặc xoá workspace trước.",
        ) from exc
    _clear_refresh_cookie(response)
