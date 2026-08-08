import type { Metadata } from "next";
import { LegalPage } from "@/features/legal/legal-page";
import { termsSections } from "@/features/legal/legal.content";

export const metadata: Metadata = {
  title: "Điều khoản sử dụng — Havi",
  description: "Điều khoản sử dụng dịch vụ Havi.",
};

export default function Page() {
  return (
    <LegalPage
      title="Điều khoản sử dụng"
      intro="Đây là thoả thuận giữa bạn và Havi khi bạn dùng dịch vụ. Chúng tôi viết ngắn gọn và bằng tiếng Việt đời thường để bạn đọc hết được."
      sections={termsSections}
    />
  );
}
