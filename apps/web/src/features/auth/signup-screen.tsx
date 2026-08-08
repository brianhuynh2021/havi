"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useSession } from "@/lib/auth/session";
import { signUp } from "./auth.api";
import { MIN_PASSWORD_LENGTH, isValidEmail } from "./auth.constants";
import styles from "./auth.module.css";

export function SignupScreen() {
  const router = useRouter();
  const { signIn } = useSession();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function submit() {
    if (!name.trim()) {
      setError("Nhập tên tiệm hoặc tên chị/anh để Havi xưng hô đúng");
      return;
    }
    if (!isValidEmail(email)) {
      setError("Email chưa đúng — kiểm tra lại giúp chị nhé");
      return;
    }
    if (password.length < MIN_PASSWORD_LENGTH) {
      setError(`Mật khẩu cần ít nhất ${MIN_PASSWORD_LENGTH} ký tự`);
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
    // Đăng ký xong là đã đăng nhập luôn (backend trả token) — không bắt nhập lại.
    signIn(result.tokens);
    router.replace("/onboarding");
  }

  return (
    <>
      <h1 className={styles.title}>Tạo tài khoản Havi</h1>
      <p className={styles.subtitle}>
        Chỉ cần tên, email và mật khẩu — 30 giây là xong.
      </p>

      <div className={styles.form}>
        <label className={styles.field}>
          <span className={styles.label}>Tên của bạn</span>
          <Input
            scale="large"
            placeholder="Ví dụ: Chị Hương"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </label>

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
            autoComplete="new-password"
            placeholder={`Ít nhất ${MIN_PASSWORD_LENGTH} ký tự`}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>

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
          {submitting ? "Đang tạo tài khoản…" : "Tạo tài khoản"}
        </Button>

        <p className={styles.consentText}>
          Bấm nút là chị/anh đồng ý với Điều khoản &amp; Bảo mật của Havi. Số
          điện thoại thêm sau trong Cài đặt nếu muốn nhận bản nháp qua Zalo.
        </p>
      </div>

      <div className={styles.footerBlock}>
        <p>
          Đã có tài khoản? <Link href="/dang-nhap">Đăng nhập</Link>
        </p>
      </div>
    </>
  );
}
