"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { MIN_PASSWORD_LENGTH, isValidEmail } from "./auth.constants";
import styles from "./auth.module.css";

export function SignupScreen() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  function submit() {
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
    router.push("/onboarding");
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
          id="name"
          placeholder="Chị Hương / Spa An Nhiên"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />

        <label className={styles.label} htmlFor="signup-email">
          Email
        </label>
        <Input
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
          id="signup-password"
          type="password"
          autoComplete="new-password"
          placeholder={`Ít nhất ${MIN_PASSWORD_LENGTH} ký tự`}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        {error ? <p className={styles.error}>{error}</p> : null}

        <p className={styles.consentText}>
          Bấm tiếp tục là chị/anh đồng ý với Điều khoản sử dụng và Chính sách
          bảo mật của Havi. Số điện thoại thêm sau trong Cài đặt nếu chị/anh muốn
          nhận bản nháp qua Zalo.
        </p>

        <Button variant="primary" onClick={submit}>
          Tiếp tục
        </Button>

        <p className={styles.footerText}>
          Đã có tài khoản? <Link href="/dang-nhap">Đăng nhập</Link>
        </p>
      </div>
    </>
  );
}
