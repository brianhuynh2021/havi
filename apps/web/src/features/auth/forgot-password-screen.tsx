"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { OtpInput } from "@/components/ui/otp-input";
import { useCountdown } from "@/lib/hooks/use-countdown";
import {
  MIN_PASSWORD_LENGTH,
  OTP_LENGTH,
  OTP_RESEND_COOLDOWN_SECONDS,
  isValidEmail,
} from "./auth.constants";
import styles from "./auth.module.css";

type Step = "email" | "otp" | "success";

export function ForgotPasswordScreen() {
  const router = useRouter();
  const [step, setStep] = useState<Step>("email");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const { secondsLeft, start, canResend } = useCountdown(OTP_RESEND_COOLDOWN_SECONDS);

  function requestCode() {
    if (!isValidEmail(email)) {
      setError("Email chưa đúng — kiểm tra lại giúp chị nhé");
      return;
    }
    setError(null);
    setStep("otp");
    start();
  }

  function submitNewPassword() {
    if (code.length !== OTP_LENGTH) {
      setError(`Nhập đủ ${OTP_LENGTH} số trong email`);
      return;
    }
    if (newPassword.length < MIN_PASSWORD_LENGTH) {
      setError(`Mật khẩu mới cần ít nhất ${MIN_PASSWORD_LENGTH} ký tự`);
      return;
    }
    setError(null);
    setStep("success");
  }

  return (
    <>
      <h1 className={styles.title}>Quên mật khẩu</h1>
      <p className={styles.subtitle}>
        Không sao cả — nhập email, Havi gửi mã để chị/anh đặt lại.
      </p>

      {step === "email" ? (
        <div className={styles.form}>
          <label className={styles.field}>
            <span className={styles.label}>Email đã đăng ký</span>
            <Input
              scale="large"
              type="email"
              inputMode="email"
              autoComplete="email"
              placeholder="tencuaban@gmail.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </label>
          {error ? (
            <p className={styles.error} role="alert">
              {error}
            </p>
          ) : null}

          <Button variant="primary" scale="large" onClick={requestCode}>
            Gửi mã đặt lại
          </Button>

          <p className={styles.footerText}>
            <Link href="/dang-nhap">← Quay lại đăng nhập</Link>
          </p>
        </div>
      ) : step === "otp" ? (
        <div className={styles.form}>
          <p className={styles.otpHint}>
            Havi đã gửi mã {OTP_LENGTH} số tới <strong>{email}</strong>
          </p>
          <OtpInput value={code} onChange={setCode} />

          <label className={styles.field}>
            <span className={styles.label}>Mật khẩu mới</span>
            <Input
              scale="large"
              type="password"
              autoComplete="new-password"
              placeholder={`Ít nhất ${MIN_PASSWORD_LENGTH} ký tự`}
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
            />
          </label>
          {error ? (
            <p className={styles.error} role="alert">
              {error}
            </p>
          ) : null}

          <Button variant="primary" scale="large" onClick={submitNewPassword}>
            Lưu &amp; đăng nhập
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
      ) : (
        <div className={styles.form}>
          <p className={styles.successText}>
            Mật khẩu đã đổi thành công. Chị/anh đăng nhập lại bằng mật khẩu mới.
          </p>
          <Button
            variant="primary"
            scale="large"
            onClick={() => router.push("/dang-nhap")}
          >
            Về đăng nhập
          </Button>
        </div>
      )}
    </>
  );
}
