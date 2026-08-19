import type { Metadata } from "next";
import { LandingScreen } from "@/features/landing/landing-screen";

export const metadata: Metadata = {
  title: "Havi — Chỉ 1 chạm tiếp cận khách hàng đa nền tảng",
  description:
    "Không còn mất hàng giờ nghĩ ý tưởng. Chỉ cần gửi ảnh, Havi tự động sinh bài, dựng video bắt trend và trực inbox kéo khách.",
};

export default function Page() {
  return <LandingScreen />;
}
