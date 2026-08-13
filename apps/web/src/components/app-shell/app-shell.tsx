"use client";

import type { ReactNode } from "react";
import { AppNav } from "./app-nav";
import styles from "./app-shell.module.css";
import { SignOutButton } from "./sign-out-button";
import { WorkspaceChannels } from "./workspace-channels";
import { WorkspaceName } from "./workspace-name";
import { Logo } from "@/components/ui/logo";
import { NotificationBell } from "@/components/notifications/notification-bell";
import { LanguageSwitcher } from "@/components/ui/language-switcher";
import { useLanguage } from "@/lib/i18n/language-context";

type AppShellProps = {
  children: ReactNode;
};

export function AppShell({ children }: AppShellProps) {
  const { t } = useLanguage();

  return (
    <div className={styles.shell}>
      <aside className={styles.sidebar}>
        <div className={styles.brand}>
          <Logo size={36} />
          <div className={styles.brandText}>Havi</div>
        </div>

        <AppNav />

        <section className={styles.workspaceCard}>
          <p className={styles.workspaceLabel}>{t("shell.workspace", "Không gian làm việc")}</p>
          <WorkspaceName />
          <WorkspaceChannels />
          <SignOutButton />
        </section>
      </aside>

      <main className={styles.content}>
        <header className={styles.topHeader}>
          <div className={styles.topHeaderTitle}>{t("shell.assistant", "Trợ lý Havi")}</div>
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <LanguageSwitcher variant="pill" />
            <NotificationBell />
          </div>
        </header>
        <div className={styles.pageBody}>{children}</div>
      </main>
    </div>
  );
}

