import type { ReactNode } from "react";
import { AppNav } from "./app-nav";
import styles from "./app-shell.module.css";
import { SignOutButton } from "./sign-out-button";
import { WorkspaceChannels } from "./workspace-channels";
import { WorkspaceName } from "./workspace-name";
import { Logo } from "@/components/ui/logo";
import { NotificationBell } from "@/components/notifications/notification-bell";

type AppShellProps = {
  children: ReactNode;
};

export function AppShell({ children }: AppShellProps) {
  return (
    <div className={styles.shell}>
      <aside className={styles.sidebar}>
        <div className={styles.brand}>
          <Logo size={36} />
          <div className={styles.brandText}>Havi</div>
        </div>

        <AppNav />

        <section className={styles.workspaceCard}>
          <p className={styles.workspaceLabel}>Không gian làm việc</p>
          <WorkspaceName />
          <WorkspaceChannels />
          <SignOutButton />
        </section>
      </aside>

      <main className={styles.content}>
        <header className={styles.topHeader}>
          <div className={styles.topHeaderTitle}>Trợ lý Havi</div>
          <NotificationBell />
        </header>
        <div className={styles.pageBody}>{children}</div>
      </main>
    </div>
  );
}
