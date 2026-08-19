import type { Metadata } from "next";
import { AboutScreen } from "@/features/about/about-screen";

export const metadata: Metadata = {
  title: "Về Havi — Câu chuyện thương hiệu & Sứ mệnh",
  description:
    "Havi (Harry + Vietnam) ra đời với sứ mệnh bình dân hoá AI marketing đa kênh cho hàng triệu chủ tiệm và hộ kinh doanh Việt Nam.",
};

export default function Page() {
  return <AboutScreen />;
}
