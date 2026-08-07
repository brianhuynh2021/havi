"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { navItems } from "./nav-items";
import styles from "./app-shell.module.css";

function isActive(pathname: string, href: string) {
  if (href === "/") return pathname === "/";
  return pathname.startsWith(href);
}

export function AppNav() {
  const pathname = usePathname();

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
              <span>{item.label}</span>
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
              {item.label}
            </Link>
          );
        })}
      </div>
    </>
  );
}
