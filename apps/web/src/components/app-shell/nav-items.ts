import type { TranslationKey } from "@/lib/i18n/translations";

export type NavItem = {
  key: TranslationKey;
  label: string;
  href: string;
  icon: string;
  count?: number;
};

// Havi Unified Execution Spaces
export const navItems: NavItem[] = [
  { key: "nav.today", label: "Hôm nay", href: "/app", icon: "⚡" },
  { key: "nav.content", label: "Studio Sáng tạo", href: "/app/content", icon: "✨" },
  { key: "nav.calendar", label: "Lịch & Kế hoạch", href: "/app/calendar", icon: "📅" },
  { key: "nav.inbox", label: "Hộp thư & Khách hàng", href: "/app/inbox", icon: "💬" },
  { key: "nav.roadmap", label: "Lộ trình chiến lược", href: "/app/roadmap", icon: "📈" },
  { key: "nav.evidence", label: "Bằng chứng khách đến", href: "/app/evidence", icon: "🎯" },
  { key: "nav.reports", label: "Báo cáo doanh thu", href: "/app/reports", icon: "📊" },
  { key: "nav.coach", label: "Hướng dẫn nhanh", href: "/app/coach", icon: "💡" },
  { key: "nav.settings", label: "Cài đặt", href: "/app/settings", icon: "⚙️" },
];



