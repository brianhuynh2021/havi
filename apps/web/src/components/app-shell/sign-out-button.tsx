"use client";

import { useSession } from "@/lib/auth/session";
import { useLanguage } from "@/lib/i18n/language-context";
import styles from "./app-shell.module.css";

export function SignOutButton() {
  const { signOut } = useSession();
  const { t } = useLanguage();

  return (
    <button type="button" className={styles.signOut} onClick={() => void signOut()}>
      {t("shell.signOut", "Đăng xuất")}
    </button>
  );
}

