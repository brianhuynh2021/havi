"use client";

import { useTheme } from "next-themes";
import { useEffect, useState } from "react";
import { useLanguage } from "@/lib/i18n/language-context";
import styles from "./theme-toggle.module.css";

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const { t } = useLanguage();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return <div className={styles.placeholder} />;
  }

  return (
    <button
      className={styles.button}
      onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
      aria-label={t("Đổi nền sáng/tối")}
    >
      {t(theme === "dark" ? "☀️ Sáng" : "🌙 Tối")}
    </button>
  );
}
