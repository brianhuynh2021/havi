// i18n-exempt: `metadata` dựng ở server, còn lựa chọn ngôn ngữ nằm trong localStorage của trình duyệt — server không đọc được. Dịch được tiêu đề tab đòi chuyển lựa chọn ngôn ngữ sang cookie rồi đổi sang `generateMetadata()`; xem ROADMAP
import type { Metadata } from "next";
import { LandingScreen } from "@/features/landing/landing-screen";

export const metadata: Metadata = {
  title: "Havi — Quản trị & vận hành mạng xã hội cho doanh nghiệp",
  description:
    "Quản lý kênh, nội dung, lịch đăng, hội thoại và thành viên tại một nơi. "
    + "Bạn duyệt trước, Havi đăng đúng giờ và xác nhận bài đã lên.",
};

export default function Page() {
  return <LandingScreen />;
}
