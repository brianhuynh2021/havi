import type { Metadata } from "next";
import { LandingScreen } from "@/features/landing/landing-screen";

export const metadata: Metadata = {
  title: "Havi — Nhân viên AI Marketing & Trực tiệm đa kênh cho chủ tiệm nhỏ",
  description:
    "Tải ảnh tiệm lên, bài đăng & video TikTok 9:16 có Hook 3s sẵn sàng. Duyệt 1-chạm trước khi đăng, trực Inbox bắt số điện thoại 24/7 chỉ từ 6.000 đ/ngày.",
};

export default function Page() {
  return <LandingScreen />;
}
