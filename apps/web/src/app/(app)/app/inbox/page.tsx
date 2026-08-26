// i18n-exempt: `metadata` dựng ở server, còn lựa chọn ngôn ngữ nằm trong localStorage của trình duyệt — server không đọc được. Dịch được tiêu đề tab đòi chuyển lựa chọn ngôn ngữ sang cookie rồi đổi sang `generateMetadata()`; xem ROADMAP
import { InboxScreen } from "@/features/inbox/inbox-screen";

export const metadata = {
  title: "Hộp Thư — Havi",
};

export default function InboxPage() {
  return <InboxScreen />;
}
