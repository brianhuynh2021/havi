// i18n-exempt: nhãn ở đây **cố ý** viết bằng ngôn ngữ kia — đang tiếng Việt thì
// nút phải nói "Chuyển sang Tiếng Anh", đang tiếng Anh thì nói "Switch to
// Vietnamese". Bọc `t()` sẽ dịch nhãn về đúng ngôn ngữ hiện tại, tức là làm nút
// mất nghĩa: người đang ở giao diện tiếng Anh sẽ thấy nút mời họ chuyển sang
// tiếng Anh.
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

  // Default: pill — **điều khiển phụ trợ**, không phải hành động.
  //
  // Bản trước dùng nền trắng đặc + đậm 700 + đổ bóng, đặt trên header nền tối.
  // Đo ra thì nó nổi hơn cả nút "Đăng nhập": thứ bậc thị giác ngược với thứ bậc
  // quan trọng. Người dùng Việt vào trang tiếng Việt gần như không bao giờ bấm
  // nó, nhưng mắt phải xử lý nó mỗi lần nhìn lên header.
  //
  // Thứ tự đúng: hành động chính → hành động phụ → điều hướng → đổi ngôn ngữ.
  // Ở đây nó nhận trọng lượng của nhóm cuối, và chỉ rõ lên khi rê chuột.
  return (
    <button
      type="button"
      onClick={toggleLang}
      className={className}
      title={lang === "VN" ? "Chuyển sang Tiếng Anh (English)" : "Switch to Vietnamese"}
      style={{
        background: "transparent",
        border: "1px solid var(--color-border)",
        borderRadius: "999px",
        padding: "6px 13px",
        color: "var(--color-muted)",
        fontSize: "13px",
        fontWeight: 600,
        cursor: "pointer",
        display: "inline-flex",
        alignItems: "center",
        gap: "6px",
        transition: "color 0.18s ease, border-color 0.18s ease",
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.color = "var(--color-ink)";
        e.currentTarget.style.borderColor = "var(--color-primary-light)";
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.color = "var(--color-muted)";
        e.currentTarget.style.borderColor = "var(--color-border)";
      }}
    >
      <span>{lang === "VN" ? "🇻🇳 VN" : "🇬🇧 EN"}</span>
    </button>
  );
}
