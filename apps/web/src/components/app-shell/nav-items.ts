import type { TranslationKey } from "@/lib/i18n/translations";

export type NavItem = {
  key: TranslationKey;
  label: string;
  href: string;
  icon: string;
  count?: number;
};

/**
 * Điều hướng chính — mỗi mục là một việc chủ tiệm thật sự làm, gọi bằng tên họ
 * dùng khi nói chuyện.
 *
 * Danh sách này cố tình ngắn. Bản trước có 8 mục cho 14 route, nghĩa là một nửa
 * số màn chỉ vào được qua link rải rác trong nội dung — người dùng không dựng
 * nổi bản đồ trong đầu về app. Màn phụ (Lead, Lộ trình, Kết nối, Thanh toán)
 * vào từ đúng chỗ cần chúng: Tổng quan và Cài đặt.
 *
 * Bài viết và video **chung một mục**. Chủ tiệm không nghĩ theo loại nội dung;
 * họ nghĩ "tối nay ngồi chuẩn bị nội dung cho tuần sau", trong đó có cả hai xen
 * kẽ. Việc rẽ nhánh nằm ở bước đầu của luồng, không nằm ở thanh điều hướng.
 */
export const navItems: NavItem[] = [
  { key: "nav.dashboard", label: "Tổng quan", href: "/app", icon: "🏠" },
  { key: "nav.content", label: "Đăng bài", href: "/app/content", icon: "✍️" },
  { key: "nav.calendar", label: "Lịch đăng", href: "/app/calendar", icon: "📅" },
  { key: "nav.inbox", label: "Tin nhắn", href: "/app/inbox", icon: "💬" },
  { key: "nav.reports", label: "Báo cáo", href: "/app/reports", icon: "📊" },
  { key: "nav.settings", label: "Cài đặt", href: "/app/settings", icon: "⚙️" },
];
