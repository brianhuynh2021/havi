// i18n-exempt: `metadata` dựng ở server, còn lựa chọn ngôn ngữ nằm trong localStorage của trình duyệt — server không đọc được. Dịch được tiêu đề tab đòi chuyển lựa chọn ngôn ngữ sang cookie rồi đổi sang `generateMetadata()`; xem ROADMAP
import { BillingScreen } from "@/features/billing/billing-screen";

export const metadata = {
  title: "Gói Cước & Thanh Toán — Havi",
};

export default function BillingPage() {
  return <BillingScreen />;
}
