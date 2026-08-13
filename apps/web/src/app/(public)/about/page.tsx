import type { Metadata } from "next";
import { LandingScreen } from "@/features/landing/landing-screen";

export const metadata: Metadata = {
  title: "Havi — Trợ lý marketing AI cho tiệm nhỏ",
  description:
    "Nạp vài tấm ảnh hoặc ba gạch đầu dòng, Havi viết bài riêng cho Facebook, Zalo OA và Google Business. Bạn duyệt rồi mới đăng.",
};

export default function Page() {
  return <LandingScreen />;
}
