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
      setError(t("Email chưa đúng — kiểm tra lại giúp nhé"));
      return;
    }
    setError(null);
    setStep("otp");
    start();
  }

  function submitNewPassword() {
    if (code.length !== OTP_LENGTH) {
      setError(t("Nhập đủ {n} số trong email", { n: OTP_LENGTH }));
      return;
    }
    if (newPassword.length < MIN_PASSWORD_LENGTH) {
      setError(t("Mật khẩu mới cần ít nhất {n} ký tự", { n: MIN_PASSWORD_LENGTH }));
      return;
    }
    setError(null);
    setStep("success");
  }

  return (
    <>
      <h1 className={styles.title}>{t("Khôi phục mật khẩu")}</h1>
      <p className={styles.subtitle}>
        {t("Nhập email của bạn để nhận liên kết khôi phục.")}
      </p>

      {step === "email" ? (
        <div className={styles.form}>
          <label className={styles.field}>
            <span className={styles.label}>{t("Email đã đăng ký")}</span>
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
              {t(error)}
            </p>
          ) : null}

          <Button variant="primary" scale="large" onClick={requestCode}>
            {t("Gửi liên kết khôi phục")}
          </Button>

          <p className={styles.footerText}>
            <Link href="/login">← {t("Quay lại đăng nhập")}</Link>
          </p>
        </div>
      ) : step === "otp" ? (
        <div className={styles.form}>
          <p className={styles.otpHint}>
            {t("Havi đã gửi mã {n} số tới ", { n: OTP_LENGTH })}
            <strong>{email}</strong>
          </p>
          <OtpInput value={code} onChange={setCode} />

          <label className={styles.field}>
            <span className={styles.label}>{t("Mật khẩu mới")}</span>
            <Input
              scale="large"
              type="password"
              autoComplete="new-password"
              placeholder={t("Ít nhất {n} ký tự", { n: MIN_PASSWORD_LENGTH })}
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
            />
          </label>
          {error ? (
            <p className={styles.error} role="alert">
              {t(error)}
            </p>
          ) : null}

          <Button variant="primary" scale="large" onClick={submitNewPassword}>
            {t("Lưu & đăng nhập")}
          </Button>

          <button
            type="button"
            className={styles.resendLink}
            disabled={!canResend}
            onClick={start}
          >
            {canResend
              ? t("Gửi lại mã")
              : t("Gửi lại mã sau {seconds}s", { seconds: secondsLeft })}
          </button>
        </div>
      ) : (
        <div className={styles.form}>
          <p className={styles.successText}>
            {t("Mật khẩu đã đổi thành công. Bạn có thể đăng nhập lại bằng mật khẩu mới.")}
          </p>
          <Button
            variant="primary"
            scale="large"
            onClick={() => router.push("/login")}
          >
            {t("Quay lại đăng nhập")}
          </Button>
        </div>
      )}
    </>
  );
}

