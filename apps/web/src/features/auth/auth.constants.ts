// Khớp mặc định core.config.Settings (HAVI_OTP_RESEND_COOLDOWN_SECONDS /
// HAVI_OTP_TTL_SECONDS) — đổi một nơi khi backend đổi cấu hình thật.
export const OTP_RESEND_COOLDOWN_SECONDS = 30;
export const OTP_LENGTH = 6;

// Khớp core.schemas.MIN_PASSWORD_LENGTH — backend trả 422 nếu ngắn hơn.
export const MIN_PASSWORD_LENGTH = 8;

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function isValidEmail(value: string): boolean {
  return EMAIL_PATTERN.test(value.trim());
}

const PHONE_PATTERN = /^0\d{9}$/;

// SĐT chỉ dùng cho Zalo OA (thêm trong Cài đặt), không phải kênh đăng nhập.
export function isValidVietnamesePhone(value: string): boolean {
  return PHONE_PATTERN.test(value.trim());
}
