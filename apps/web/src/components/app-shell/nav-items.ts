import type { TranslationKey } from "@/lib/i18n/translations";

export type NavItem = {
  key: TranslationKey;
  label: string;
  href: string;
  count?: number;
};

// Havi 3.0 Unified Execution Spaces (Tối giản chuẩn mực 5 không gian)
export const navItems: NavItem[] = [
  { key: "nav.today", label: "Hôm nay", href: "/app" },
  { key: "nav.content", label: "Studio Sáng tạo", href: "/app/content" },
  { key: "nav.calendar", label: "Lịch & Kế hoạch", href: "/app/calendar" },
  { key: "nav.inbox", label: "Hộp thư & Khách hàng", href: "/app/inbox" },
  { key: "nav.roadmap", label: "Lộ trình & Báo cáo", href: "/app/roadmap" },
  { key: "nav.settings", label: "Cài đặt", href: "/app/settings" },
];



