"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { navItems } from "./nav-items";
import styles from "./app-shell.module.css";
import { useLanguage } from "@/lib/i18n/language-context";

function isActive(pathname: string, href: string) {
  if (href === "/app" || href === "/") return pathname === "/app" || pathname === "/";
  return pathname.startsWith(href);
}

export function AppNav() {
  const pathname = usePathname();
  const { t } = useLanguage();

  return (
    <>
      <nav className={styles.nav} aria-label="Điều hướng chính">
        {navItems.map((item) => {
          const active = isActive(pathname, item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`${styles.navItem} ${
                active ? styles.navItemActive : ""
              }`}
              aria-current={active ? "page" : undefined}
            >
              <span className={styles.navDot} aria-hidden="true" />
              <span>{t(item.key, item.label)}</span>
              {typeof item.count === "number" ? (
                <span className={styles.navBadge}>{item.count}</span>
              ) : null}
            </Link>
          );
        })}
      </nav>

      <div className={styles.mobileNav} aria-label="Điều hướng mobile">
        {navItems.map((item) => {
          const active = isActive(pathname, item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`${styles.mobileNavItem} ${
                active ? styles.mobileNavItemActive : ""
              }`}
              aria-current={active ? "page" : undefined}
            >
              {t(item.key, item.label)}
            </Link>
          );
        })}
      </div>
    </>
  );
}

