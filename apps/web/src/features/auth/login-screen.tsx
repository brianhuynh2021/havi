"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useSession } from "@/lib/auth/session";
import { useLanguage } from "@/lib/i18n/language-context";
import { login } from "./auth.api";
import { isValidEmail } from "./auth.constants";
import styles from "./auth.module.css";

export function LoginScreen() {
  const router = useRouter();
  const { signIn } = useSession();
  const { t } = useLanguage();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function submit() {
    if (!isValidEmail(email)) {
      setError(t({ vi: "Email chưa đúng — kiểm tra lại giúp chị nhé", en: "Invalid email — please check again" }));
      return;
    }
    if (!password) {
      setError(t({ vi: "Nhập mật khẩu để đăng nhập", en: "Please enter your password to sign in" }));
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
    router.replace(result.tokens.needsOnboarding ? "/onboarding" : "/app");
  }

  return (
    <>
      <h1 className={styles.title}>{t("auth.loginTitle", "Đăng nhập Havi")}</h1>
      <p className={styles.subtitle}>{t("auth.loginSubtitle", "Chào mừng trở lại! Vui lòng nhập thông tin để truy cập.")}</p>

      <form
        className={styles.form}
        noValidate
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
      >
        <label className={styles.field} htmlFor="email">
          <span className={styles.label}>{t("auth.email", "Email")}</span>
          <Input
            id="email"
            name="email"
            scale="large"
            type="email"
            inputMode="email"
            autoComplete="username email"
            placeholder="tencuaban@gmail.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </label>

        <label className={styles.field} htmlFor="password">
          <span className={styles.label}>{t("auth.password", "Mật khẩu")}</span>
          <Input
            id="password"
            name="password"
            scale="large"
            type="password"
            autoComplete="current-password"
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </label>

        <Link href="/quen-mat-khau" className={styles.inlineLink}>
          {t("auth.forgotPassword", "Quên mật khẩu?")}
        </Link>

        {error ? (
          <p className={styles.error} role="alert">
            {error}
          </p>
        ) : null}

        <Button
          type="submit"
          variant="primary"
          scale="large"
          disabled={submitting}
        >
          {submitting
            ? t({ vi: "Đang đăng nhập…", en: "Signing in…" })
            : t("auth.loginButton", "Đăng nhập")}
        </Button>
      </form>

      <div className={styles.footerBlock}>
        <p>
          {t({ vi: "Lần đầu dùng Havi? ", en: "First time using Havi? " })}
          <Link href="/signup">
            {t("auth.registerButton", "Tạo tài khoản miễn phí")}
          </Link>
        </p>
      </div>
    </>
  );
}

