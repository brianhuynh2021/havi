"""/auth/* — SĐT + OTP là kênh chính, email + mật khẩu là phụ.

Màn Đăng Nhập: 1 ô SĐT → "Nhận mã đăng nhập" → 6 ô OTP, đếm ngược 30s mới cho gửi lại.
Đăng ký chỉ cần tên + SĐT → OTP → dẫn vào Onboarding (`needs_onboarding=true`).
"""

from fastapi import APIRouter, status

from api.deps import AuthDep
from api.errors import NotImplementedEndpoint
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
    """Frontend dùng `resend_after_seconds` để chạy đồng hồ đếm ngược trên màn OTP."""

    resend_after_seconds: int
    expires_in_seconds: int


@router.post(
    "/otp/request",
    response_model=OtpChallenge,
    status_code=status.HTTP_202_ACCEPTED,
)
def request_otp(payload: OtpRequest) -> OtpChallenge:
    """Gửi OTP qua Zalo/SMS. Trả về số giây phải chờ trước khi cho gửi lại."""
    del payload
    raise NotImplementedEndpoint()


@router.post("/otp/verify", response_model=TokenPair)
def verify_otp(payload: OtpVerify) -> TokenPair:
    del payload
    raise NotImplementedEndpoint()


@router.post("/sign-up", response_model=TokenPair, status_code=status.HTTP_201_CREATED)
def sign_up(payload: SignUpRequest) -> TokenPair:
    """Tạo user + gửi OTP. Xác thực xong thì `needs_onboarding=true`."""
    del payload
    raise NotImplementedEndpoint()


@router.post("/login/email", response_model=TokenPair)
def login_email(payload: EmailLoginRequest) -> TokenPair:
    """Đường phụ — chỉ dùng khi user đã thêm email/mật khẩu trong Cài đặt."""
    del payload
    raise NotImplementedEndpoint()


@router.post("/refresh", response_model=TokenPair)
def refresh(payload: RefreshRequest) -> TokenPair:
    del payload
    raise NotImplementedEndpoint()


@router.get("/me", response_model=CurrentUser)
def me(auth: AuthDep) -> CurrentUser:
    del auth
    raise NotImplementedEndpoint()
