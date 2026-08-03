import type { ReactNode } from "react";
import styles from "./app-shell.module.css";

type NavItem = {
  label: string;
  active: boolean;
  count?: number;
};

const navItems: NavItem[] = [
  { label: "Tổng quan", active: true },
  { label: "Tạo nội dung", active: false },
  { label: "Lịch đăng", active: false, count: 3 },
  { label: "Khách tiềm năng", active: false, count: 2 },
  { label: "Báo cáo", active: false },
];

const connectedChannels = ["Facebook", "TikTok", "Zalo", "Maps"] as const;

type AppShellProps = {
  children: ReactNode;
};

export function AppShell({ children }: AppShellProps) {
  return (
    <div className={styles.shell}>
      <aside className={styles.sidebar}>
        <div className={styles.brand}>
          <div className={styles.brandMark}>Ha</div>
          <div className={styles.brandText}>Havi</div>
        </div>

        <nav className={styles.nav} aria-label="Điều hướng chính">
          {navItems.map((item) => (
            <button
              key={item.label}
              type="button"
              className={`${styles.navItem} ${
                item.active ? styles.navItemActive : ""
              }`}
            >
              <span className={styles.navDot} aria-hidden="true" />
              <span>{item.label}</span>
              {typeof item.count === "number" ? (
                <span className={styles.navBadge}>{item.count}</span>
              ) : null}
            </button>
          ))}
        </nav>

        <div className={styles.mobileNav} aria-label="Điều hướng mobile">
          {navItems.map((item) => (
            <div
              key={item.label}
              className={`${styles.mobileNavItem} ${
                item.active ? styles.mobileNavItemActive : ""
              }`}
            >
              {item.label}
            </div>
          ))}
        </div>

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
        </section>
      </aside>

      <main className={styles.content}>{children}</main>
    </div>
  );
}
