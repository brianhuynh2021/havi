import type { TranslationKey } from "@/lib/i18n/translations";

export type NavItem = {
  key: TranslationKey;
  label: string;
  href: string;
  count?: number;
};

// `count` là số việc "chờ chị" trên mỗi tab. Bỏ trống cho tới khi có nguồn thật
// từ dashboard summary: số fixture cứng (3 và 2) từng chạy thẳng trong app thật,
// nên chủ tiệm thấy huy hiệu "3 việc cần làm" ở tab Lịch đăng kể cả khi lịch
// trống — đúng loại số giả mà §4 tuần 8 đã dọn khỏi Dashboard và Báo cáo.
export const navItems: NavItem[] = [
  { key: "nav.dashboard", label: "Tổng quan", href: "/app" },
  { key: "nav.content", label: "Tạo nội dung", href: "/app/content" },
  { key: "nav.videoStudio", label: "Studio Video", href: "/app/video-studio" },
  { key: "nav.calendar", label: "Lịch đăng", href: "/app/calendar" },
  { key: "nav.inbox", label: "Hộp thư & Khách hàng", href: "/app/inbox" },
  { key: "nav.reports", label: "Báo cáo", href: "/app/reports" },
  { key: "nav.billing", label: "Gói cước", href: "/app/billing" },
  { key: "nav.settings", label: "Cài đặt", href: "/app/settings" },
];

