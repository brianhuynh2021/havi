// Khớp mặc định core.config.Settings (HAVI_OTP_RESEND_COOLDOWN_SECONDS /
// HAVI_OTP_TTL_SECONDS) — đổi một nơi khi backend đổi cấu hình thật.
export const OTP_RESEND_COOLDOWN_SECONDS = 30;
export const OTP_LENGTH = 6;

export const PHONE_PATTERN = /^0\d{9}$/;

export function isValidVietnamesePhone(value: string): boolean {
  return PHONE_PATTERN.test(value.trim());
}
