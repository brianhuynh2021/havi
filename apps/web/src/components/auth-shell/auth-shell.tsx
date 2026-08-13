"use client";

import type { ReactNode } from "react";
import styles from "./auth-shell.module.css";
import { Logo } from "@/components/ui/logo";
import { LanguageSwitcher } from "@/components/ui/language-switcher";
import { useLanguage } from "@/lib/i18n/language-context";

type AuthShellProps = {
  children: ReactNode;
};

export function AuthShell({ children }: AuthShellProps) {
  const { t } = useLanguage();

  return (
    <div className={styles.page}>
      <div style={{ position: "absolute", top: "24px", right: "24px" }}>
        <LanguageSwitcher variant="pill" />
      </div>

      <div className={styles.brand}>
        <Logo size={44} />
        <div className={styles.brandText}>Havi</div>
      </div>
      <div className={styles.card}>{children}</div>
      <p className={styles.tagline}>
        {t({
          vi: "Havi — trợ lý marketing cho tiệm của bạn",
          en: "Havi — AI marketing assistant for your store",
        })}
      </p>
    </div>
  );
}

