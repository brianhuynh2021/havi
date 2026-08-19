"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useSession } from "@/lib/auth/session";
import { useLanguage } from "@/lib/i18n/language-context";
import { signUp } from "./auth.api";
import { SocialAuthButtons } from "./social-auth-buttons";
import { MIN_PASSWORD_LENGTH, isValidEmail } from "./auth.constants";
import styles from "./auth.module.css";

export function SignupScreen() {
  const router = useRouter();
  const { signIn } = useSession();
  const { t } = useLanguage();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function submit() {
    if (!name.trim()) {
      setError(t({ vi: "Nhập tên tiệm hoặc tên của bạn", en: "Please enter your name or business name" }));
      return;
    }
    if (!isValidEmail(email)) {
      setError(t({ vi: "Email chưa đúng — kiểm tra lại giúp nhé", en: "Invalid email — please check again" }));
      return;
    }
    if (password.length < MIN_PASSWORD_LENGTH) {
      setError(t({ vi: `Mật khẩu cần ít nhất ${MIN_PASSWORD_LENGTH} ký tự`, en: `Password must be at least ${MIN_PASSWORD_LENGTH} characters` }));
      return;
    }
    setError(null);
    setSubmitting(true);
    const result = await signUp(name.trim(), email.trim(), password);
    if (!result.ok) {
      setError(result.message);
      setSubmitting(false);
      return;
    }
    signIn(result.tokens);
    router.replace("/onboarding");
  }

  return (
    <>
      <h1 className={styles.title}>{t("auth.registerTitle", "Tạo tài khoản Havi")}</h1>
      <p className={styles.subtitle}>
        {t("auth.registerSubtitle", "Chỉ cần tên, email và mật khẩu — 30 giây là xong.")}
      </p>

      <SocialAuthButtons mode="signup" />

      <form
        className={styles.form}
        noValidate
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
      >
        <label className={styles.field} htmlFor="signup-name">
          <span className={styles.label}>{t("auth.fullName", "Họ và tên")}</span>
          <Input
            id="signup-name"
            name="name"
            scale="large"
            autoComplete="name"
            placeholder={t({ vi: "Ví dụ: Chị Hương", en: "e.g., Sarah Jenkins" })}
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
        </label>

        <label className={styles.field} htmlFor="signup-email">
          <span className={styles.label}>{t("auth.email", "Email")}</span>
          <Input
            id="signup-email"
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

        <label className={styles.field} htmlFor="signup-password">
          <span className={styles.label}>{t("auth.password", "Mật khẩu")}</span>
          <Input
            id="signup-password"
            name="password"
            scale="large"
            type="password"
            autoComplete="new-password"
            placeholder={t({ vi: `Ít nhất ${MIN_PASSWORD_LENGTH} ký tự`, en: `At least ${MIN_PASSWORD_LENGTH} characters` })}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </label>

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
            ? t({ vi: "Đang tạo tài khoản…", en: "Creating account…" })
            : t("auth.registerButton", "Tạo tài khoản")}
        </Button>

        <p className={styles.consentText}>
          {t({ vi: "Bấm nút là bạn đồng ý với ", en: "By continuing, you agree to Havi's " })}
          <Link href="/terms">{t("public.terms", "Điều khoản")}</Link> &amp;{" "}
          <Link href="/privacy">{t("public.privacy", "Bảo mật")}</Link>.
        </p>
      </form>

      <div className={styles.footerBlock}>
        <p>
          {t("auth.hasAccount", "Đã có tài khoản?")}{" "}
          <Link href="/login">{t("auth.loginButton", "Đăng nhập")}</Link>
        </p>
      </div>
    </>
  );
}

