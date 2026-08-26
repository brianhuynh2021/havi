"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useSession } from "@/lib/auth/session";
import { useLanguage } from "@/lib/i18n/language-context";
import { signUp } from "./auth.api";
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
      setError(t("Nhập tên tiệm hoặc tên của bạn"));
      return;
    }
    if (!isValidEmail(email)) {
      setError(t("Email chưa đúng — kiểm tra lại giúp nhé"));
      return;
    }
    if (password.length < MIN_PASSWORD_LENGTH) {
      setError(t("Mật khẩu cần ít nhất {n} ký tự", { n: MIN_PASSWORD_LENGTH }));
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
      <h1 className={styles.title}>{t("Tạo tài khoản Havi")}</h1>
      <p className={styles.subtitle}>
        {t("Quản lý nội dung, lịch đăng và hội thoại đa kênh trong một nơi.")}
      </p>

      <form
        className={styles.form}
        noValidate
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
      >
        <label className={styles.field} htmlFor="signup-name">
          <span className={styles.label}>{t("Họ và tên")}</span>
          <Input
            id="signup-name"
            name="name"
            scale="large"
            autoComplete="name"
            placeholder={t("Ví dụ: Nguyễn Thu Hương")}
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
        </label>

        <label className={styles.field} htmlFor="signup-email">
          <span className={styles.label}>{t("Email")}</span>
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
          <span className={styles.label}>{t("Mật khẩu")}</span>
          <Input
            id="signup-password"
            name="password"
            scale="large"
            type="password"
            autoComplete="new-password"
            placeholder={t("Ít nhất {n} ký tự", { n: MIN_PASSWORD_LENGTH })}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </label>

        {error ? (
          <p className={styles.error} role="alert">
            {t(error)}
          </p>
        ) : null}

        <Button
          type="submit"
          variant="primary"
          scale="large"
          disabled={submitting}
        >
          {submitting
            ? t("Đang tạo tài khoản…")
            : t("Tạo tài khoản miễn phí")}
        </Button>

        <p className={styles.consentText}>
          {t("Bấm nút là bạn đồng ý với ")}
          <Link href="/terms">{t("Điều Khoản Dịch Vụ")}</Link> &amp;{" "}
          <Link href="/privacy">{t("Chính Sách Bảo Mật")}</Link>.
        </p>
      </form>

      <div className={styles.footerBlock}>
        <p>
          {t("Đã có tài khoản?")}{" "}
          <Link href="/login">{t("Đăng nhập")}</Link>
        </p>
      </div>
    </>
  );
}

