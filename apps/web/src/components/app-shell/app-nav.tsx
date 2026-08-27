"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { primaryNavItems, adminNavItems, type NavItem } from "./nav-items";
import { NavIcon, IconAdmin, IconChevronDown } from "./nav-icons";
import styles from "./app-shell.module.css";
import { useLanguage } from "@/lib/i18n/language-context";
import { fetchDashboardSummary, type DashboardContentSummary } from "@/features/dashboard/dashboard.api";

const ADMIN_STORAGE_KEY = "havi_admin_nav_expanded";

/**
 * Kiểm tra trạng thái active của một link điều hướng.
 * - `/app`: chỉ active khi ở đúng `/app` hoặc `/`.
 * - `/app/content`: active khi ở `/app/content` hoặc `/app/media` (vì Thư viện media thuộc luồng Nội dung).
 * - Các route khác: active khi pathname khớp hoặc là đường dẫn con.
 */
export function isActive(pathname: string, href: string): boolean {
  if (href === "/app" || href === "/") {
    return pathname === "/app" || pathname === "/";
  }
  if (href === "/app/content") {
    return (
      pathname === "/app/content" ||
      pathname.startsWith("/app/content/") ||
      pathname === "/app/media" ||
      pathname.startsWith("/app/media/")
    );
  }
  return pathname === href || pathname.startsWith(`${href}/`);
}

function isAdminRoute(pathname: string): boolean {
  return adminNavItems.some(
    (item) => pathname === item.href || pathname.startsWith(`${item.href}/`),
  );
}

type AppNavProps = {
  variant: "desktop" | "mobile";
};

export function AppNav({ variant }: AppNavProps) {
  const pathname = usePathname();
  const { t } = useLanguage();
  const [summary, setSummary] = useState<DashboardContentSummary | null>(null);
  const [isAdminExpanded, setIsAdminExpanded] = useState(false);

  useEffect(() => {
    fetchDashboardSummary().then((res) => {
      if (res.ok) setSummary(res.data);
    });
  }, [pathname]);

  // Khởi tạo và đồng bộ trạng thái mở/thu gọn nhóm Quản trị
  useEffect(() => {
    if (isAdminRoute(pathname)) {
      setIsAdminExpanded(true);
    } else {
      try {
        const saved = localStorage.getItem(ADMIN_STORAGE_KEY);
        if (saved !== null) {
          setIsAdminExpanded(saved === "true");
        }
      } catch {
        // Trình duyệt chặn localStorage hoặc môi trường test
      }
    }
  }, [pathname]);

  function handleToggleAdmin() {
    setIsAdminExpanded((prev) => {
      const next = !prev;
      try {
        localStorage.setItem(ADMIN_STORAGE_KEY, String(next));
      } catch {
        // Bỏ qua lỗi localStorage
      }
      return next;
    });
  }

  const primaryItemsWithCounts: NavItem[] = primaryNavItems.map((item) => {
    let count: number | undefined = undefined;
    if (summary) {
      if (item.href === "/app/content") count = summary.pending_approval;
      if (item.href === "/app/calendar") count = summary.failed;
      if (item.href === "/app/inbox") count = summary.unhandled_inbox;
    }
    return { ...item, count };
  });

  const brokenCount = summary?.broken_connections ?? 0;
  const hasBrokenConnections = brokenCount > 0;

  const adminItemsWithCounts: NavItem[] = adminNavItems.map((item) => {
    let count: number | undefined = undefined;
    if (summary && item.href === "/app/connections" && brokenCount > 0) {
      count = brokenCount;
    }
    return { ...item, count, hasWarning: item.href === "/app/connections" && hasBrokenConnections };
  });

  const isCurrentInAdmin = isAdminRoute(pathname);

  if (variant === "desktop") {
    return (
      <nav className={styles.nav} aria-label={t("Điều hướng chính")}>
        {primaryItemsWithCounts.map((item) => {
          const active = isActive(pathname, item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`${styles.navItem} ${active ? styles.navItemActive : ""}`}
              aria-current={active ? "page" : undefined}
            >
              <span className={styles.navIcon} aria-hidden="true">
                <NavIcon icon={item.icon} size={18} />
              </span>
              <span className={styles.navLabel}>{t(item.label)}</span>
              {(item.count ?? 0) > 0 ? (
                <span className={styles.navBadge}>{item.count}</span>
              ) : null}
            </Link>
          );
        })}

        <div className={styles.adminDivider} role="separator" />

        <div className={styles.adminSection}>
          <button
            type="button"
            className={`${styles.adminToggleBtn} ${isCurrentInAdmin ? styles.adminToggleBtnActive : ""}`}
            onClick={handleToggleAdmin}
            aria-expanded={isAdminExpanded}
            aria-controls="admin-nav-list"
          >
            <span className={styles.navIcon} aria-hidden="true">
              <IconAdmin size={18} />
            </span>
            <span className={styles.navLabel}>{t("Quản trị")}</span>
            {hasBrokenConnections ? (
              <span className={styles.warningBadge} title={t("Có kết nối hỏng")}>!</span>
            ) : null}
            <IconChevronDown
              size={13}
              className={`${styles.adminChevron} ${isAdminExpanded ? styles.adminChevronOpen : ""}`}
              aria-hidden="true"
            />
          </button>

          {isAdminExpanded && (
            <div id="admin-nav-list" className={styles.adminList} role="group" aria-label={t("Quản trị")}>
              {adminItemsWithCounts.map((item) => {
                const active = item.href === "/app/media"
                  ? (pathname === "/app/media" || pathname.startsWith("/app/media/"))
                  : (pathname === item.href || pathname.startsWith(`${item.href}/`));
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`${styles.adminNavItem} ${active ? styles.adminNavItemActive : ""}`}
                    aria-current={active ? "page" : undefined}
                  >
                    <span className={styles.adminNavIcon} aria-hidden="true">
                      <NavIcon icon={item.icon} size={16} />
                    </span>
                    <span className={styles.navLabel}>{t(item.label)}</span>
                    {(item.count ?? 0) > 0 ? (
                      <span className={styles.warningBadge}>{item.count}</span>
                    ) : null}
                  </Link>
                );
              })}
            </div>
          )}
        </div>
      </nav>
    );
  }

  return (
    <div className={styles.mobileNavShell}>
      <nav className={styles.mobileNav} aria-label={t("Điều hướng mobile")}>
        {primaryItemsWithCounts.map((item) => {
          const active = isActive(pathname, item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`${styles.mobileNavItem} ${active ? styles.mobileNavItemActive : ""}`}
              aria-current={active ? "page" : undefined}
            >
              <span className={styles.mobileNavIcon}>
                <NavIcon icon={item.icon} size={20} />
                {(item.count ?? 0) > 0 && (
                  <span className={styles.mobileNavBadge}>{item.count}</span>
                )}
              </span>
              <span className={styles.mobileNavLabel}>{t(item.label)}</span>
            </Link>
          );
        })}
      </nav>
    </div>
  );
}


