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
