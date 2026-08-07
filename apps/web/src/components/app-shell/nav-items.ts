export type NavItem = {
  label: string;
  href: string;
  count?: number;
};

// count là số việc "chờ chị" trên mỗi tab — khớp fixture của từng feature.
// Tuần 5 nối API thật thì đổi sang lấy từ dashboard summary.
export const navItems: NavItem[] = [
  { label: "Tổng quan", href: "/" },
  { label: "Tạo nội dung", href: "/noi-dung" },
  { label: "Lịch đăng", href: "/lich-dang", count: 3 },
  { label: "Khách tiềm năng", href: "/khach-tiem-nang", count: 2 },
  { label: "Báo cáo", href: "/bao-cao" },
];
