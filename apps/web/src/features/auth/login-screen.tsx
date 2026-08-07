"use client";

import Link from "next/link";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { isValidEmail } from "./auth.constants";
import styles from "./auth.module.css";

export function LoginScreen() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  function submit() {
    if (!isValidEmail(email)) {
      setError("Email chưa đúng — kiểm tra lại giúp chị nhé");
      return;
    }
    if (!password) {
      setError("Nhập mật khẩu để đăng nhập");
      return;
    }
    setError(null);
  }

  return (
    <>
      <h1 className={styles.title}>Đăng nhập</h1>
      <p className={styles.subtitle}>Vào Havi bằng email của chị/anh.</p>

      <div className={styles.form}>
        <label className={styles.label} htmlFor="email">
          Email
        </label>
        <Input
          id="email"
          type="email"
          inputMode="email"
          autoComplete="email"
          placeholder="huong@spaannhien.vn"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />

        <label className={styles.label} htmlFor="password">
          Mật khẩu
        </label>
        <Input
          id="password"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        {error ? <p className={styles.error}>{error}</p> : null}

        <Button variant="primary" onClick={submit}>
          Đăng nhập
        </Button>

        <p className={styles.footerText}>
          Chưa có tài khoản? <Link href="/dang-ky">Đăng ký</Link>
        </p>
      </div>

      <p className={styles.footerText}>
        <Link href="/quen-mat-khau">Quên mật khẩu?</Link>
      </p>
    </>
  );
}
