"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { OtpInput } from "@/components/ui/otp-input";
import { useCountdown } from "@/lib/hooks/use-countdown";
import { useLanguage } from "@/lib/i18n/language-context";
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
  const { t } = useLanguage();
  const [step, setStep] = useState<Step>("email");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const { secondsLeft, start, canResend } = useCountdown(OTP_RESEND_COOLDOWN_SECONDS);

  function requestCode() {
    if (!isValidEmail(email)) {
      setError(t({ vi: "Email chưa đúng — kiểm tra lại giúp nhé", en: "Invalid email — please check again" }));
      return;
    }
    setError(null);
    setStep("otp");
    start();
  }

  function submitNewPassword() {
    if (code.length !== OTP_LENGTH) {
      setError(t({ vi: `Nhập đủ ${OTP_LENGTH} số trong email`, en: `Enter all ${OTP_LENGTH} digits sent to your email` }));
      return;
    }
    if (newPassword.length < MIN_PASSWORD_LENGTH) {
      setError(t({ vi: `Mật khẩu mới cần ít nhất ${MIN_PASSWORD_LENGTH} ký tự`, en: `New password must be at least ${MIN_PASSWORD_LENGTH} characters` }));
      return;
    }
    setError(null);
    setStep("success");
  }

  return (
    <>
      <h1 className={styles.title}>{t("auth.forgotTitle", "Quên mật khẩu")}</h1>
      <p className={styles.subtitle}>
        {t("auth.forgotSubtitle", "Nhập email của bạn để nhận liên kết khôi phục.")}
      </p>

      {step === "email" ? (
        <div className={styles.form}>
          <label className={styles.field}>
            <span className={styles.label}>{t({ vi: "Email đã đăng ký", en: "Registered Email Address" })}</span>
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
            {t("auth.sendResetLink", "Gửi mã đặt lại")}
          </Button>

          <p className={styles.footerText}>
            <Link href="/dang-nhap">← {t("auth.backToLogin", "Quay lại đăng nhập")}</Link>
          </p>
        </div>
      ) : step === "otp" ? (
        <div className={styles.form}>
          <p className={styles.otpHint}>
            {t({ vi: `Havi đã gửi mã ${OTP_LENGTH} số tới `, en: `Havi sent a ${OTP_LENGTH}-digit code to ` })}
            <strong>{email}</strong>
          </p>
          <OtpInput value={code} onChange={setCode} />

          <label className={styles.field}>
            <span className={styles.label}>{t({ vi: "Mật khẩu mới", en: "New Password" })}</span>
            <Input
              scale="large"
              type="password"
              autoComplete="new-password"
              placeholder={t({ vi: `Ít nhất ${MIN_PASSWORD_LENGTH} ký tự`, en: `At least ${MIN_PASSWORD_LENGTH} characters` })}
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
            {t({ vi: "Lưu & đăng nhập", en: "Save & Sign In" })}
          </Button>

          <button
            type="button"
            className={styles.resendLink}
            disabled={!canResend}
            onClick={start}
          >
            {canResend
              ? t({ vi: "Gửi lại mã", en: "Resend code" })
              : t({ vi: `Gửi lại mã sau ${secondsLeft}s`, en: `Resend code in ${secondsLeft}s` })}
          </button>
        </div>
      ) : (
        <div className={styles.form}>
          <p className={styles.successText}>
            {t({ vi: "Mật khẩu đã đổi thành công. Bạn có thể đăng nhập lại bằng mật khẩu mới.", en: "Password changed successfully. You can now log in with your new password." })}
          </p>
          <Button
            variant="primary"
            scale="large"
            onClick={() => router.push("/login")}
          >
            {t("auth.backToLogin", "Về đăng nhập")}
          </Button>
        </div>
      )}
    </>
  );
}

