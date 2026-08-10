"use client";

import { useSession } from "@/lib/auth/session";
import styles from "./app-shell.module.css";

export function SignOutButton() {
  const { signOut } = useSession();

  return (
    <button type="button" className={styles.signOut} onClick={() => void signOut()}>
      Đăng xuất
    </button>
  );
}
