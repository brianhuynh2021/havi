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
      <h1 className={styles.title}>Đăng ký</h1>
      <p className={styles.subtitle}>Havi cần vài thông tin để bắt đầu.</p>

      <div className={styles.form}>
        <label className={styles.label} htmlFor="name">
          Tên chị/anh hoặc tên tiệm
        </label>
        <Input
          scale="large"
          id="name"
          placeholder="Chị Hương / Spa An Nhiên"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />

        <label className={styles.label} htmlFor="signup-email">
          Email
        </label>
        <Input
          scale="large"
          id="signup-email"
          type="email"
          inputMode="email"
          autoComplete="email"
          placeholder="huong@spaannhien.vn"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />

        <label className={styles.label} htmlFor="signup-password">
          Mật khẩu
        </label>
        <Input
          scale="large"
          id="signup-password"
          type="password"
          autoComplete="new-password"
          placeholder={`Ít nhất ${MIN_PASSWORD_LENGTH} ký tự`}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        {error ? (
          <p className={styles.error} role="alert">
            {error}
          </p>
        ) : null}

        <p className={styles.consentText}>
          Bấm tiếp tục là chị/anh đồng ý với Điều khoản sử dụng và Chính sách
          bảo mật của Havi. Số điện thoại thêm sau trong Cài đặt nếu chị/anh muốn
          nhận bản nháp qua Zalo.
        </p>

        <Button variant="primary" onClick={submit} disabled={submitting}>
          {submitting ? "Đang tạo tài khoản…" : "Tiếp tục"}
        </Button>

        <p className={styles.footerText}>
          Đã có tài khoản? <Link href="/dang-nhap">Đăng nhập</Link>
        </p>
      </div>
    </>
  );
}
