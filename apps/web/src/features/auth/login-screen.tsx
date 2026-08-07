"use client";

import Link from "next/link";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { OtpInput } from "@/components/ui/otp-input";
import { useCountdown } from "@/lib/hooks/use-countdown";
import {
  OTP_LENGTH,
  OTP_RESEND_COOLDOWN_SECONDS,
  isValidVietnamesePhone,
} from "./auth.constants";
import styles from "./auth.module.css";

type Step = "phone" | "otp";

export function LoginScreen() {
  const [step, setStep] = useState<Step>("phone");
  const [phone, setPhone] = useState("");
  const [otp, setOtp] = useState("");
  const [phoneError, setPhoneError] = useState<string | null>(null);
  const { secondsLeft, start, canResend } = useCountdown(OTP_RESEND_COOLDOWN_SECONDS);

  function requestOtp() {
    if (!isValidVietnamesePhone(phone)) {
      setPhoneError("Số điện thoại chưa đúng — nhập dạng 0xxxxxxxxx");
      return;
    }
    setPhoneError(null);
    setStep("otp");
    start();
  }

  return (
    <>
      <h1 className={styles.title}>Đăng nhập</h1>
      <p className={styles.subtitle}>Vào Havi bằng số điện thoại của tiệm.</p>

      {step === "phone" ? (
        <div className={styles.form}>
          <label className={styles.label} htmlFor="phone">
            Số điện thoại
          </label>
          <Input
            id="phone"
            inputMode="tel"
            placeholder="0912345678"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
          />
          {phoneError ? <p className={styles.error}>{phoneError}</p> : null}

          <Button variant="primary" onClick={requestOtp}>
            Gửi mã OTP
          </Button>

          <p className={styles.footerText}>
            Chưa có tài khoản? <Link href="/dang-ky">Đăng ký</Link>
          </p>
        </div>
      ) : (
        <div className={styles.form}>
          <p className={styles.otpHint}>
            Havi đã gửi mã {OTP_LENGTH} số tới <strong>{phone}</strong>
          </p>
          <OtpInput value={otp} onChange={setOtp} />

          <Button variant="primary" disabled={otp.length !== OTP_LENGTH}>
            Xác nhận
          </Button>

          <button
            type="button"
            className={styles.resendLink}
            disabled={!canResend}
            onClick={start}
          >
            {canResend ? "Gửi lại mã" : `Gửi lại mã sau ${secondsLeft}s`}
          </button>

          <button type="button" className={styles.backLink} onClick={() => setStep("phone")}>
            ← Đổi số điện thoại
          </button>
        </div>
      )}

      <p className={styles.footerText}>
        <Link href="/quen-mat-khau">Quên mật khẩu?</Link>
      </p>
    </>
  );
}
