"use client";

import { useState, useEffect, type ReactNode } from "react";
import { AppNav } from "./app-nav";
import { MobileAdminSheet } from "./mobile-admin-sheet";
import { IconAdmin } from "./nav-icons";
import styles from "./app-shell.module.css";
import { SignOutButton } from "./sign-out-button";
import { WorkspaceChannels } from "./workspace-channels";
import { WorkspaceName } from "./workspace-name";
import { Logo } from "@/components/ui/logo";
import { ThemeToggle } from "@/components/ui/theme-toggle";
import { PwaInstallModal } from "@/components/pwa/pwa-install-modal";
import { useLanguage } from "@/lib/i18n/language-context";
import { fetchDashboardSummary } from "@/features/dashboard/dashboard.api";

type AppShellProps = {
  children: ReactNode;
};

export function AppShell({ children }: AppShellProps) {
  const { t } = useLanguage();
  const [isMobileAdminOpen, setIsMobileAdminOpen] = useState(false);
  const [hasBrokenConnections, setHasBrokenConnections] = useState(false);

  useEffect(() => {
    fetchDashboardSummary().then((res) => {
      if (res.ok) {
        setHasBrokenConnections((res.data.broken_connections ?? 0) > 0);
      }
    });
  }, []);

  return (
    <div className={styles.shell}>
      <aside className={styles.sidebar}>
        <div className={styles.topSection}>
          <div className={styles.brand}>
            <Logo size={32} />
            <div className={styles.brandText}>Havi</div>
          </div>

          <div className={styles.workspaceSection}>
            <WorkspaceName />
          </div>
        </div>

        <div className={styles.navSection}>
          <AppNav variant="desktop" />
        </div>

        <section className={styles.bottomCard}>
          <WorkspaceChannels />
          <SignOutButton />
        </section>
      </aside>

      {/* Navigation mobile phải là anh em của sidebar, không phải con của nó:
          sidebar bị ẩn ở màn hình nhỏ. Đặt nav trong sidebar khiến người dùng
          đăng nhập được nhưng không thể rời màn hình hiện tại. */}
      <AppNav variant="mobile" />

      {/* Bottom Sheet Quản trị trên Mobile */}
      <MobileAdminSheet
        isOpen={isMobileAdminOpen}
        onClose={() => setIsMobileAdminOpen(false)}
      />

      <main className={styles.content}>
        {/* Header không lặp lại tên thương hiệu: sidebar ngay bên trái đã hiện
            nó kèm số thương hiệu. Hai nhãn cho cùng một thứ, cách nhau vài
            centimet, chỉ làm người đọc phải quyết định xem chúng có khác nhau
            không. */}
        <header className={styles.topHeader}>
          <div>
            <button
              type="button"
              className={styles.mobileHeaderAdminBtn}
              onClick={() => setIsMobileAdminOpen(true)}
              aria-label={t("Mở menu quản trị")}
              aria-expanded={isMobileAdminOpen}
              aria-haspopup="dialog"
              data-testid="mobile-header-admin-btn"
            >
              <span className={styles.mobileHeaderAdminIcon} aria-hidden="true">
                <IconAdmin size={16} />
              </span>
              <span>{t("Quản trị")}</span>
              {hasBrokenConnections ? (
                <span className={styles.warningBadge} title={t("Có kết nối hỏng")}>!</span>
              ) : null}
            </button>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <PwaInstallModal />
            <ThemeToggle />
          </div>
        </header>
        <div className={styles.pageBody}>{children}</div>
      </main>
    </div>
  );
}

