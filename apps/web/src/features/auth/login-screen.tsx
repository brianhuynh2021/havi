"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useSession } from "@/lib/auth/session";
import { login } from "./auth.api";
import { isValidEmail } from "./auth.constants";
import styles from "./auth.module.css";

export function LoginScreen() {
  const router = useRouter();
  const { signIn } = useSession();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function submit() {
    if (!isValidEmail(email)) {
      setError("Email chưa đúng — kiểm tra lại giúp chị nhé");
      return;
    }
    if (!password) {
      setError("Nhập mật khẩu để đăng nhập");
      return;
    }
    setError(null);
    setSubmitting(true);
    const result = await login(email.trim(), password);
    if (!result.ok) {
      setError(result.message);
      setSubmitting(false);
      return;
    }
    signIn(result.tokens);
    // Chưa có workspace thì phải đi onboarding trước, không thì app rỗng.
    router.replace(result.tokens.needsOnboarding ? "/onboarding" : "/");
  }

  return (
    <>
      <h1 className={styles.title}>Chào bạn trở lại</h1>
      <p className={styles.subtitle}>Đăng nhập để tiếp tục với Havi.</p>

      <div className={styles.form}>
        <label className={styles.field}>
          <span className={styles.label}>Email</span>
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

        <label className={styles.field}>
          <span className={styles.label}>Mật khẩu</span>
          <Input
            scale="large"
            type="password"
            autoComplete="current-password"
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>

        <Link href="/quen-mat-khau" className={styles.inlineLink}>
          Quên mật khẩu?
        </Link>

        {error ? (
          <p className={styles.error} role="alert">
            {error}
          </p>
        ) : null}

        <Button
          variant="primary"
          scale="large"
          onClick={submit}
          disabled={submitting}
        >
          {submitting ? "Đang đăng nhập…" : "Đăng nhập"}
        </Button>
      </div>

      {/* Prototype có "Tiếp tục với Google" nhưng đăng nhập Google là P1 chưa
          làm (ROADMAP §4). Không dựng nút bấm vào không chạy — thà thiếu còn
          hơn hứa capability chưa có (§2). */}

      <div className={styles.footerBlock}>
        <p>
          Lần đầu dùng Havi?{" "}
          <Link href="/dang-ky">Tạo tài khoản miễn phí</Link>
        </p>
      </div>
    </>
  );
}
