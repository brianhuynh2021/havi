// i18n-exempt: `metadata` dựng ở server, còn lựa chọn ngôn ngữ nằm trong localStorage của trình duyệt — server không đọc được. Dịch được tiêu đề tab đòi chuyển lựa chọn ngôn ngữ sang cookie rồi đổi sang `generateMetadata()`; xem ROADMAP
import { MediaScreen } from "@/features/media/media-screen";

export const metadata = { title: "Thư viện media — Havi" };

export default function Page() {
  return <MediaScreen />;
}
