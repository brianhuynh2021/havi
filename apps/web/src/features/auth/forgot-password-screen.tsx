"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
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

type Step = "phone" | "otp" | "reset" | "success";

export function ForgotPasswordScreen() {
  const router = useRouter();
  const [step, setStep] = useState<Step>("phone");
  const [phone, setPhone] = useState("");
  const [otp, setOtp] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const { secondsLeft, start, canResend } = useCountdown(OTP_RESEND_COOLDOWN_SECONDS);

  function requestOtp() {
    if (!isValidVietnamesePhone(phone)) {
      setError("Số điện thoại chưa đúng — nhập dạng 0xxxxxxxxx");
      return;
    }
    setError(null);
    setStep("otp");
    start();
  }

  function submitNewPassword() {
    if (newPassword.length < 6) {
      setError("Mật khẩu mới cần ít nhất 6 ký tự");
      return;
    }
    setError(null);
    setStep("success");
  }

  return (
    <>
      <h1 className={styles.title}>Quên mật khẩu</h1>
      <p className={styles.subtitle}>Havi giúp chị/anh đặt lại mật khẩu mới.</p>

      {step === "phone" ? (
        <div className={styles.form}>
          <label className={styles.label} htmlFor="fp-phone">
            Số điện thoại đã đăng ký
          </label>
          <Input
            id="fp-phone"
            inputMode="tel"
            placeholder="0912345678"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
          />
          {error ? <p className={styles.error}>{error}</p> : null}

          <Button variant="primary" onClick={requestOtp}>
            Gửi mã xác nhận
          </Button>

          <p className={styles.footerText}>
            <Link href="/dang-nhap">← Về đăng nhập</Link>
          </p>
        </div>
      ) : step === "otp" ? (
        <div className={styles.form}>
          <p className={styles.otpHint}>
            Havi đã gửi mã {OTP_LENGTH} số tới <strong>{phone}</strong>
          </p>
          <OtpInput value={otp} onChange={setOtp} />

          <Button
            variant="primary"
            disabled={otp.length !== OTP_LENGTH}
            onClick={() => setStep("reset")}
          >
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
        </div>
      ) : step === "reset" ? (
        <div className={styles.form}>
          <label className={styles.label} htmlFor="new-password">
            Mật khẩu mới
          </label>
          <Input
            id="new-password"
            type="password"
            placeholder="Ít nhất 6 ký tự"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
          />
          {error ? <p className={styles.error}>{error}</p> : null}

          <Button variant="primary" onClick={submitNewPassword}>
            Đặt lại mật khẩu
          </Button>
        </div>
      ) : (
        <div className={styles.form}>
          <p className={styles.successText}>
            Mật khẩu đã đổi thành công. Chị/anh đăng nhập lại bằng mật khẩu mới.
          </p>
          <Button variant="primary" onClick={() => router.push("/dang-nhap")}>
            Về đăng nhập
          </Button>
        </div>
      )}
    </>
  );
}
