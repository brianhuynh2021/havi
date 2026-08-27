// i18n-data: `label` là nhãn nav, `app-nav.tsx` dịch bằng `t(item.label)` khi render
export type NavItem = {
  label: string;
  href: string;
  icon: string;
  count?: number;
  hasWarning?: boolean;
};

/**
 * 4 khu vực làm việc chính hàng ngày của Havi.
 */
export const primaryNavItems: NavItem[] = [
  { label: "Việc cần làm", href: "/app", icon: "tasks" },
  { label: "Nội dung", href: "/app/content", icon: "content" },
  { label: "Lịch đăng", href: "/app/calendar", icon: "calendar" },
  { label: "Hội thoại", href: "/app/inbox", icon: "inbox" },
];

/**
 * 7 mục quản trị hệ thống, gom lại dưới nhóm Quản trị.
 */
export const adminNavItems: NavItem[] = [
  { label: "Thư viện media", href: "/app/media", icon: "media" },
  { label: "Kênh kết nối", href: "/app/connections", icon: "connections" },
  { label: "Đội ngũ", href: "/app/team", icon: "team" },
  { label: "Lịch sử", href: "/app/activity", icon: "activity" },
  { label: "Báo cáo", href: "/app/reports", icon: "reports" },
  { label: "Gói cước", href: "/app/billing", icon: "billing" },
  { label: "Cài đặt", href: "/app/settings", icon: "settings" },
];

/**
 * Danh sách toàn bộ nav items cho backward compatibility.
 */
export const navItems: NavItem[] = [...primaryNavItems, ...adminNavItems];


