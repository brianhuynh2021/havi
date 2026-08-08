import type { ReactNode } from "react";
import { AppNav } from "./app-nav";
import styles from "./app-shell.module.css";
import { SignOutButton } from "./sign-out-button";
import { Logo } from "@/components/ui/logo";

const connectedChannels = ["Facebook", "TikTok", "Zalo", "Maps"] as const;

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
          <p className={styles.workspaceName}>Spa An Nhiên</p>
          <div className={styles.workspaceChips}>
            {connectedChannels.map((channel) => (
              <span key={channel} className={styles.workspaceChip}>
                {channel}
              </span>
            ))}
          </div>
          <SignOutButton />
        </section>
      </aside>

      <main className={styles.content}>{children}</main>
    </div>
  );
}
