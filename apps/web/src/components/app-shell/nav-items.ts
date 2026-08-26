import type { TranslationKey } from "@/lib/i18n/translations";

export type NavItem = {
  key: TranslationKey;
  label: string;
  href: string;
  icon: string;
  count?: number;
};

/**
 * Điều hướng chính — chín khu vực quản trị, đúng phạm vi sản phẩm.
 *
 * Havi quản trị **hệ thống social** của khách: kênh, nội dung, kho media, lịch
 * đăng, hội thoại, thành viên. Không quản trị mục tiêu kinh doanh của họ.
 *
 * Vì vậy ở đây **không có** Lộ trình, Bằng chứng hay Trợ lý gợi ý tăng trưởng.
 * Chúng từng tồn tại và từng bị đẩy ra khỏi nav bởi chính người viết ra chúng —
 * một dấu hiệu rõ ràng rằng người dùng không mở app theo cách đó.
 */
export const navItems: NavItem[] = [
  { key: "nav.dashboard", label: "Việc cần làm", href: "/app", icon: "✅" },
  { key: "nav.content", label: "Nội dung", href: "/app/content", icon: "✍️" },
  { key: "nav.media", label: "Thư viện media", href: "/app/media", icon: "🖼️" },
  { key: "nav.calendar", label: "Lịch đăng", href: "/app/calendar", icon: "📅" },
  { key: "nav.inbox", label: "Hội thoại", href: "/app/inbox", icon: "💬" },
  { key: "nav.connections", label: "Kênh kết nối", href: "/app/connections", icon: "🔗" },
  { key: "nav.team", label: "Đội ngũ", href: "/app/team", icon: "👥" },
  { key: "nav.activity", label: "Lịch sử", href: "/app/activity", icon: "🧾" },
  { key: "nav.reports", label: "Báo cáo", href: "/app/reports", icon: "📊" },
  // Gói cước phải có trong nav: trước đó chỉ vào được bằng cách gõ URL, nên
  // khách hàng không tìm được đường trả tiền. Đặt cạnh Cài đặt vì cả hai đều
  // là việc làm một lần rồi quên, không phải việc hằng ngày.
  { key: "nav.billing", label: "Gói cước", href: "/app/billing", icon: "💳" },
  { key: "nav.settings", label: "Cài đặt", href: "/app/settings", icon: "⚙️" },
];
