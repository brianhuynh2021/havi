"""/auth/* — SĐT + OTP là kênh chính, email + mật khẩu là phụ.

Màn Đăng Nhập: 1 ô SĐT → "Nhận mã đăng nhập" → 6 ô OTP, đếm ngược 30s mới cho gửi lại.
Đăng ký chỉ cần tên + SĐT → OTP → dẫn vào Onboarding (`needs_onboarding=true`).
"""

from fastapi import APIRouter, HTTPException, status

from api.deps import AuthDep, AuthServiceDep
from api.errors import NotImplementedEndpoint
from application.services.auth_service import (
    InvalidPhoneFormat,
    OtpInvalidOrExpired,
    OtpRateLimited,
    OtpTooManyAttempts,
    PhoneAlreadyRegistered,
    PhoneNotRegistered,
    RefreshTokenInvalid,
)
from core.schemas import (
    CurrentUser,
    EmailLoginRequest,
    HaviModel,
    OtpRequest,
    OtpVerify,
    RefreshRequest,
    SignUpRequest,
    TokenPair,
)

router = APIRouter(prefix="/auth", tags=["auth"])


class OtpChallenge(HaviModel):
    """Frontend dùng `resend_after_seconds` để chạy đồng hồ đếm ngược trên màn OTP.

    `debug_code` chỉ có giá trị khi `HAVI_DEBUG=true` (chưa có provider SMS/Zalo
    thật — xem ROADMAP.md "Quyết định cần chốt"). Không log OTP ra bất kỳ đâu.
    """

    resend_after_seconds: int
    expires_in_seconds: int
    debug_code: str | None = None


@router.post(
    "/otp/request",
    response_model=OtpChallenge,
    status_code=status.HTTP_202_ACCEPTED,
)
async def request_otp(payload: OtpRequest, auth_service: AuthServiceDep) -> OtpChallenge:
    """Gửi OTP qua Zalo/SMS. Trả về số giây phải chờ trước khi cho gửi lại."""
    try:
        result = await auth_service.request_otp(phone=payload.phone)
    except InvalidPhoneFormat as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Số điện thoại không hợp lệ") from exc
    except PhoneNotRegistered as exc:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Số điện thoại chưa có tài khoản — vui lòng đăng ký"
        ) from exc
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


@router.post("/otp/verify", response_model=TokenPair)
async def verify_otp(payload: OtpVerify, auth_service: AuthServiceDep) -> TokenPair:
    try:
        result = await auth_service.verify_otp(phone=payload.phone, code=payload.code)
    except InvalidPhoneFormat as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Số điện thoại không hợp lệ") from exc
    except OtpTooManyAttempts as exc:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS, "Nhập sai quá nhiều lần — vui lòng gửi lại mã mới"
        ) from exc
    except OtpInvalidOrExpired as exc:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Mã OTP không đúng hoặc đã hết hạn"
        ) from exc
    except PhoneNotRegistered as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Số điện thoại chưa có tài khoản") from exc
    return TokenPair(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        active_workspace_id=result.active_workspace_id,
        needs_onboarding=result.needs_onboarding,
    )


@router.post("/sign-up", response_model=OtpChallenge, status_code=status.HTTP_202_ACCEPTED)
async def sign_up(payload: SignUpRequest, auth_service: AuthServiceDep) -> OtpChallenge:
    """Tạo user + gửi OTP. Xác nhận OTP ở `/auth/otp/verify` mới nhận được token.

    (Trả `TokenPair` ngay ở bước này là sai — sẽ cấp token cho số điện thoại
    chưa được xác minh sở hữu.)
    """
    try:
        result = await auth_service.sign_up(name=payload.name, phone=payload.phone)
    except InvalidPhoneFormat as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Số điện thoại không hợp lệ") from exc
    except PhoneAlreadyRegistered as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Số điện thoại đã có tài khoản — đăng nhập thay vì đăng ký"
        ) from exc
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


@router.post("/login/email", response_model=TokenPair)
def login_email(payload: EmailLoginRequest) -> TokenPair:
    """Đường phụ — chỉ dùng khi user đã thêm email/mật khẩu trong Cài đặt."""
    del payload
    raise NotImplementedEndpoint()


@router.post("/refresh", response_model=TokenPair)
async def refresh(payload: RefreshRequest, auth_service: AuthServiceDep) -> TokenPair:
    try:
        result = await auth_service.refresh(refresh_token=payload.refresh_token)
    except RefreshTokenInvalid as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Refresh token không hợp lệ hoặc đã hết hạn"
        ) from exc
    return TokenPair(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        active_workspace_id=result.active_workspace_id,
        needs_onboarding=result.needs_onboarding,
    )


@router.get("/me", response_model=CurrentUser)
async def me(auth: AuthDep, auth_service: AuthServiceDep) -> CurrentUser:
    user = await auth_service.get_user_by_id(auth.user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy user")
    return CurrentUser(
        id=user.id,
        name=user.name,
        phone=user.phone,
        email=user.email,
        active_workspace_id=user.active_workspace_id,
    )
