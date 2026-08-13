"use client";

import { useLanguage } from "@/lib/i18n/language-context";

type LanguageSwitcherProps = {
  variant?: "pill" | "compact" | "subtle";
  className?: string;
};

export function LanguageSwitcher({
  variant = "pill",
  className = "",
}: LanguageSwitcherProps) {
  const { lang, toggleLang } = useLanguage();

  if (variant === "compact") {
    return (
      <button
        type="button"
        onClick={toggleLang}
        className={className}
        title={lang === "VN" ? "Chuyển sang Tiếng Anh" : "Switch to Vietnamese"}
        style={{
          background: "var(--color-surface)",
          border: "1px solid var(--color-border)",
          borderRadius: "8px",
          padding: "5px 11px",
          color: "var(--color-ink)",
          fontSize: "12.5px",
          fontWeight: 700,
          cursor: "pointer",
          display: "inline-flex",
          alignItems: "center",
          gap: "6px",
          transition: "all 0.2s ease",
          boxShadow: "0 1px 3px rgba(0, 0, 0, 0.05)",
        }}
      >
        <span>{lang === "VN" ? "🇻🇳 VN" : "🇬🇧 EN"}</span>
      </button>
    );
  }

  if (variant === "subtle") {
    return (
      <button
        type="button"
        onClick={toggleLang}
        className={className}
        style={{
          background: "transparent",
          border: "none",
          color: "var(--color-muted)",
          fontSize: "13px",
          fontWeight: 600,
          cursor: "pointer",
          display: "inline-flex",
          alignItems: "center",
          gap: "6px",
          padding: "4px 8px",
          borderRadius: "6px",
          transition: "all 0.2s ease",
        }}
      >
        <span>{lang === "VN" ? "🇻🇳 Tiếng Việt" : "🇬🇧 English"}</span>
      </button>
    );
  }

  // Default: Pill variant — Tương phản cao, không có mũi tên tam giác thừa
  return (
    <button
      type="button"
      onClick={toggleLang}
      className={className}
      title={lang === "VN" ? "Chuyển sang Tiếng Anh (English)" : "Chuyển sang Tiếng Việt"}
      style={{
        background: "var(--color-surface)",
        border: "1px solid var(--color-border)",
        borderRadius: "999px",
        padding: "6px 14px",
        color: "var(--color-ink)",
        fontSize: "13px",
        fontWeight: 700,
        cursor: "pointer",
        display: "inline-flex",
        alignItems: "center",
        gap: "6px",
        transition: "all 0.2s ease",
        boxShadow: "0 2px 8px rgba(0, 0, 0, 0.06)",
      }}
    >
      <span>{lang === "VN" ? "🇻🇳 VN" : "🇬🇧 EN"}</span>
    </button>
  );
}
