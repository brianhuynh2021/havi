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

type Step = "info" | "otp" | "success";

export function SignupScreen() {
  const router = useRouter();
  const [step, setStep] = useState<Step>("info");
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [otp, setOtp] = useState("");
  const [error, setError] = useState<string | null>(null);
  const { secondsLeft, start, canResend } = useCountdown(OTP_RESEND_COOLDOWN_SECONDS);

  function submitInfo() {
    if (!name.trim()) {
      setError("Nhập tên tiệm hoặc tên chị/anh để Havi xưng hô đúng");
      return;
    }
    if (!isValidVietnamesePhone(phone)) {
      setError("Số điện thoại chưa đúng — nhập dạng 0xxxxxxxxx");
      return;
    }
    setError(null);
    setStep("otp");
    start();
  }

  return (
    <>
      <h1 className={styles.title}>Đăng ký</h1>
      <p className={styles.subtitle}>Havi cần vài thông tin để bắt đầu.</p>

      {step === "info" ? (
        <div className={styles.form}>
          <label className={styles.label} htmlFor="name">
            Tên chị/anh hoặc tên tiệm
          </label>
          <Input
            id="name"
            placeholder="Chị Hương / Spa An Nhiên"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />

          <label className={styles.label} htmlFor="signup-phone">
            Số điện thoại
          </label>
          <Input
            id="signup-phone"
            inputMode="tel"
            placeholder="0912345678"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
          />
          {error ? <p className={styles.error}>{error}</p> : null}

          <p className={styles.consentText}>
            Bấm tiếp tục là chị/anh đồng ý với Điều khoản sử dụng và Chính sách
            bảo mật của Havi.
          </p>

          <Button variant="primary" onClick={submitInfo}>
            Tiếp tục
          </Button>

          <p className={styles.footerText}>
            Đã có tài khoản? <Link href="/dang-nhap">Đăng nhập</Link>
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
            onClick={() => setStep("success")}
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
      ) : (
        <div className={styles.form}>
          <p className={styles.successText}>
            Xác nhận thành công! Havi sẽ hỏi vài câu ngắn để hiểu tiệm của
            chị/anh hơn.
          </p>
          <Button variant="primary" onClick={() => router.push("/onboarding")}>
            Bắt đầu onboarding
          </Button>
        </div>
      )}
    </>
  );
}
