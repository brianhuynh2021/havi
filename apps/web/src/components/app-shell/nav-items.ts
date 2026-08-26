// i18n-data: `label` là nhãn nav, `app-nav.tsx` dịch bằng `t(item.label)` khi render
export type NavItem = {
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
  { label: "Việc cần làm", href: "/app", icon: "✅" },
  { label: "Nội dung", href: "/app/content", icon: "✍️" },
  { label: "Thư viện media", href: "/app/media", icon: "🖼️" },
  { label: "Lịch đăng", href: "/app/calendar", icon: "📅" },
  { label: "Hội thoại", href: "/app/inbox", icon: "💬" },
  { label: "Kênh kết nối", href: "/app/connections", icon: "🔗" },
  { label: "Đội ngũ", href: "/app/team", icon: "👥" },
  { label: "Lịch sử", href: "/app/activity", icon: "🧾" },
  { label: "Báo cáo", href: "/app/reports", icon: "📊" },
  // Gói cước phải có trong nav: trước đó chỉ vào được bằng cách gõ URL, nên
  // khách hàng không tìm được đường trả tiền. Đặt cạnh Cài đặt vì cả hai đều
  // là việc làm một lần rồi quên, không phải việc hằng ngày.
  { label: "Gói cước", href: "/app/billing", icon: "💳" },
  { label: "Cài đặt", href: "/app/settings", icon: "⚙️" },
];
