"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { navItems } from "./nav-items";
import styles from "./app-shell.module.css";
import { useLanguage } from "@/lib/i18n/language-context";
import { fetchDashboardSummary, type DashboardContentSummary } from "@/features/dashboard/dashboard.api";

function isActive(pathname: string, href: string) {
  if (href === "/app" || href === "/") return pathname === "/app" || pathname === "/";
  return pathname.startsWith(href);
}

type AppNavProps = {
  variant: "desktop" | "mobile";
};

export function AppNav({ variant }: AppNavProps) {
  const pathname = usePathname();
  const { t } = useLanguage();
  const [summary, setSummary] = useState<DashboardContentSummary | null>(null);
  const [isMoreOpen, setIsMoreOpen] = useState(false);

  useEffect(() => {
    fetchDashboardSummary().then((res) => {
      if (res.ok) setSummary(res.data);
    });
    // Đóng menu "Thêm" khi chuyển trang
    setIsMoreOpen(false);
  }, [pathname]);

  const itemsWithCounts = navItems.map((item) => {
    let count: number | undefined = undefined;
    if (summary) {
      if (item.href === "/app/content") count = summary.pending_approval;
      if (item.href === "/app/inbox") count = summary.unhandled_inbox;
      if (item.href === "/app/connections") count = summary.broken_connections;
      if (item.href === "/app/calendar") count = summary.failed;
    }
    return { ...item, count };
  });

  const mobileMainItems = itemsWithCounts.filter((i) =>
    ["/app", "/app/content", "/app/calendar", "/app/inbox"].includes(i.href)
  );

  const mobileMoreItems = itemsWithCounts.filter(
    (i) => !["/app", "/app/content", "/app/calendar", "/app/inbox"].includes(i.href)
  );

  if (variant === "desktop") {
    return (
      <nav className={styles.nav} aria-label={t("Điều hướng chính")}>
        {itemsWithCounts.map((item) => {
          const active = isActive(pathname, item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`${styles.navItem} ${active ? styles.navItemActive : ""}`}
              aria-current={active ? "page" : undefined}
            >
              <span className={styles.navIcon} aria-hidden="true">{item.icon}</span>
              <span className={styles.navLabel}>{t(item.label)}</span>
              {(item.count ?? 0) > 0 ? (
                <span className={styles.navBadge}>{item.count}</span>
              ) : null}
            </Link>
          );
        })}
      </nav>
    );
  }

  return (
    <div className={styles.mobileNavShell}>
      <nav className={styles.mobileNav} aria-label={t("Điều hướng mobile")}>
        {mobileMainItems.map((item) => {
          const active = isActive(pathname, item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`${styles.mobileNavItem} ${active ? styles.mobileNavItemActive : ""}`}
              aria-current={active ? "page" : undefined}
            >
              <span className={styles.mobileNavIcon}>
                {item.icon}
                {(item.count ?? 0) > 0 && <span className={styles.mobileNavBadge}>{item.count}</span>}
              </span>
              <span className={styles.mobileNavLabel}>{t(item.label)}</span>
            </Link>
          );
        })}
        
        <button
          type="button"
          className={`${styles.mobileNavItem} ${isMoreOpen ? styles.mobileNavItemActive : ""}`}
          onClick={() => setIsMoreOpen(!isMoreOpen)}
          aria-expanded={isMoreOpen}
        >
          <span className={styles.mobileNavIcon}>
            ☰
            {mobileMoreItems.some(i => (i.count ?? 0) > 0) && (
              <span className={styles.mobileNavBadge}>!</span>
            )}
          </span>
          <span className={styles.mobileNavLabel}>{t("Thêm")}</span>
        </button>
      </nav>

      {isMoreOpen && (
        <div className={styles.mobileMoreMenu}>
          {mobileMoreItems.map((item) => {
            const active = isActive(pathname, item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`${styles.mobileMoreItem} ${active ? styles.mobileMoreItemActive : ""}`}
              >
                <span style={{ marginRight: "12px" }}>{item.icon}</span>
                {t(item.label)}
                {(item.count ?? 0) > 0 && <span className={styles.mobileMoreBadge}>{item.count}</span>}
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
