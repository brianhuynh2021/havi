import type { TranslationKey } from "@/lib/i18n/translations";

export type NavItem = {
  key: TranslationKey;
  label: string;
  href: string;
  count?: number;
};

// count là số việc "chờ chị" trên mỗi tab — khớp fixture của từng feature.
// Tuần 5 nối API thật thì đổi sang lấy từ dashboard summary.
export const navItems: NavItem[] = [
  { key: "nav.dashboard", label: "Tổng quan", href: "/app" },
  { key: "nav.content", label: "Tạo nội dung", href: "/app/content" },
  { key: "nav.calendar", label: "Lịch đăng", href: "/app/calendar", count: 3 },
  { key: "nav.leads", label: "Khách tiềm năng", href: "/app/leads", count: 2 },
  { key: "nav.reports", label: "Báo cáo", href: "/app/reports" },
  { key: "nav.settings", label: "Cài đặt", href: "/app/settings" },
];

