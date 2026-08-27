"use client";

import type { ReactNode } from "react";
import styles from "./auth-shell.module.css";
import { Logo } from "@/components/ui/logo";
import { useLanguage } from "@/lib/i18n/language-context";

type AuthShellProps = {
  children: ReactNode;
};

export function AuthShell({ children }: AuthShellProps) {
  const { t } = useLanguage();

  return (
    <div className={styles.page}>
      <div className={styles.brand}>
        <Logo size={44} />
        <div className={styles.brandText}>Havi</div>
      </div>
      <div className={styles.card}>{children}</div>
      <p className={styles.tagline}>
        {t("Havi — quản trị mạng xã hội nhẹ đầu hơn")}
      </p>
    </div>
  );
}
