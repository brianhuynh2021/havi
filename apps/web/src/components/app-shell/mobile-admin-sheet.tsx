"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { adminNavItems, type NavItem } from "./nav-items";
import { NavIcon, IconAdmin } from "./nav-icons";
import styles from "./app-shell.module.css";
import { useLanguage } from "@/lib/i18n/language-context";
import { fetchDashboardSummary, type DashboardContentSummary } from "@/features/dashboard/dashboard.api";

type MobileAdminSheetProps = {
  isOpen: boolean;
  onClose: () => void;
};

export function MobileAdminSheet({ isOpen, onClose }: MobileAdminSheetProps) {
  const pathname = usePathname();
  const { t } = useLanguage();
  const [summary, setSummary] = useState<DashboardContentSummary | null>(null);
  const closeBtnRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!isOpen) return;
    fetchDashboardSummary().then((res) => {
      if (res.ok) setSummary(res.data);
    });
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;

    // Focus nút đóng khi mở
    const timer = setTimeout(() => {
      closeBtnRef.current?.focus();
    }, 50);

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      clearTimeout(timer);
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const brokenCount = summary?.broken_connections ?? 0;
  const hasBrokenConnections = brokenCount > 0;

  const adminItemsWithCounts: NavItem[] = adminNavItems.map((item) => {
    let count: number | undefined = undefined;
    if (summary && item.href === "/app/connections" && brokenCount > 0) {
      count = brokenCount;
    }
    return { ...item, count, hasWarning: item.href === "/app/connections" && hasBrokenConnections };
  });

  return (
    <>
      <div
        className={styles.mobileSheetBackdrop}
        onClick={onClose}
        aria-hidden="true"
        data-testid="mobile-admin-backdrop"
      />
      <div
        className={styles.mobileSheet}
        role="dialog"
        aria-modal="true"
        aria-label={t("Quản trị")}
        data-testid="mobile-admin-sheet"
      >
        <div className={styles.mobileSheetHeader}>
          <h2 className={styles.mobileSheetTitle}>
            <IconAdmin size={20} aria-hidden="true" />
            {t("Quản trị")}
          </h2>
          <button
            ref={closeBtnRef}
            type="button"
            className={styles.mobileSheetCloseBtn}
            onClick={onClose}
            aria-label={t("Đóng menu quản trị")}
          >
            ✕
          </button>
        </div>

        <div className={styles.mobileSheetList}>
          {adminItemsWithCounts.map((item) => {
            const active =
              item.href === "/app/media"
                ? pathname === "/app/media" || pathname.startsWith("/app/media/")
                : pathname === item.href || pathname.startsWith(`${item.href}/`);

            return (
              <Link
                key={item.href}
                href={item.href}
                className={`${styles.mobileSheetItem} ${active ? styles.mobileSheetItemActive : ""}`}
                aria-current={active ? "page" : undefined}
                onClick={onClose}
              >
                <span className={styles.adminNavIcon} aria-hidden="true">
                  <NavIcon icon={item.icon} size={18} />
                </span>
                <span className={styles.navLabel}>{t(item.label)}</span>
                {(item.count ?? 0) > 0 ? (
                  <span className={styles.mobileSheetBadge}>{item.count}</span>
                ) : null}
              </Link>
            );
          })}
        </div>
      </div>
    </>
  );
}

