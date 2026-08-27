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
  { label: "Việc cần làm", href: "/app", icon: "✅" },
  { label: "Nội dung", href: "/app/content", icon: "✍️" },
  { label: "Lịch đăng", href: "/app/calendar", icon: "📅" },
  { label: "Hội thoại", href: "/app/inbox", icon: "💬" },
];

/**
 * 7 mục quản trị hệ thống, gom lại dưới nhóm Quản trị.
 */
export const adminNavItems: NavItem[] = [
  { label: "Thư viện media", href: "/app/media", icon: "🖼️" },
  { label: "Kênh kết nối", href: "/app/connections", icon: "🔗" },
  { label: "Đội ngũ", href: "/app/team", icon: "👥" },
  { label: "Lịch sử", href: "/app/activity", icon: "🧾" },
  { label: "Báo cáo", href: "/app/reports", icon: "📊" },
  { label: "Gói cước", href: "/app/billing", icon: "💳" },
  { label: "Cài đặt", href: "/app/settings", icon: "⚙️" },
];

/**
 * Danh sách toàn bộ nav items cho backward compatibility.
 */
export const navItems: NavItem[] = [...primaryNavItems, ...adminNavItems];

