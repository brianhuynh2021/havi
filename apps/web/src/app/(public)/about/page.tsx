import type { Metadata } from "next";
import { AboutScreen } from "@/features/about/about-screen";

export const metadata: Metadata = {
  title: "Về Havi — Câu chuyện thương hiệu & Sứ mệnh",
  description:
    "Havi (Harry + Vietnam) giúp doanh nghiệp Việt quản trị nội dung, lịch đăng, hội thoại và đội ngũ social media trong một nơi.",
};

export default function Page() {
  return <AboutScreen />;
}
