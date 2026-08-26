// i18n-exempt: văn bản pháp lý — bản dịch Chính sách bảo mật phải do luật sư soạn, không phải codemod
import type { Metadata } from "next";
import { LegalPage } from "@/features/legal/legal-page";
import { privacySections } from "@/features/legal/legal.content";

export const metadata: Metadata = {
  title: "Chính sách bảo mật — Havi",
  description:
    "Havi thu thập dữ liệu gì, dùng để làm gì, chia sẻ với ai và bạn có quyền gì.",
};

export default function Page() {
  return (
    <LegalPage
      title="Chính sách bảo mật"
      intro="Trang này nói rõ Havi thu thập dữ liệu gì của bạn, dùng để làm gì, gửi đi đâu, giữ bao lâu, và bạn có quyền gì với dữ liệu đó."
      sections={privacySections}
    />
  );
}
