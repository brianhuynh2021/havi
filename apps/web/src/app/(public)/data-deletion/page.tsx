import type { Metadata } from "next";
import { LegalPage } from "@/features/legal/legal-page";
import type { Section } from "@/features/legal/legal.content";

export const metadata: Metadata = {
  title: "Hướng dẫn xóa dữ liệu Facebook — Havi",
  description:
    "Hướng dẫn cách ngắt kết nối Facebook Page và yêu cầu xóa toàn bộ dữ liệu ứng dụng Havi.",
};

const dataDeletionSections: Section[] = [
  {
    heading: "1. Ngắt kết nối Facebook trực tiếp trên Havi",
    paragraphs: [
      "Bạn có thể ngắt kết nối Trang Facebook khỏi Havi bất kỳ lúc nào ngay trong ứng dụng:",
      "1. Đăng nhập vào tài khoản Havi của bạn.",
      "2. Truy cập mục Cài đặt -> Kênh liên kết.",
      "3. Tại ô Trang Facebook, nhấn nút 'Ngắt kết nối'.",
      "Hệ thống Havi sẽ lập tức hủy và xóa vĩnh viễn access token đã mã hóa của Trang Facebook khỏi cơ sở dữ liệu.",
    ],
  },
  {
    heading: "2. Gỡ ứng dụng Havi trên Facebook (Facebook Apps & Websites)",
    paragraphs: [
      "Theo quy định của Meta, bạn cũng có thể gỡ quyền truy cập của Havi từ chính giao diện Facebook:",
      "1. Mở Facebook và vào phần Cài đặt & Quản lý quyền riêng tư -> Cài đặt.",
      "2. Chọn 'Ứng dụng và trang web' (Apps and Websites).",
      "3. Tìm ứng dụng 'Havi AI Marketing' và nhấn nút 'Gỡ' (Remove).",
      "Khi bạn thực hiện thao tác này, Facebook sẽ tự động gửi thông báo Hủy quyền (Data Deletion Request) đến máy chủ của Havi.",
    ],
  },
  {
    heading: "3. Xóa toàn bộ dữ liệu tài khoản & lịch sử bài đăng nháp",
    paragraphs: [
      "Nếu bạn muốn xóa toàn bộ tài khoản Havi, không gian làm việc và toàn bộ lịch sử bài viết:",
      "• Đăng nhập Havi -> Cài đặt -> Vùng nguy hiểm -> chọn 'Xóa tài khoản' hoặc 'Xóa không gian làm việc'.",
      "• Hoặc gửi email yêu cầu về: hotro@havi.vn kèm email đăng ký tài khoản.",
      "Hệ thống sẽ thực hiện xóa sạch toàn bộ dữ liệu cá nhân, token kết nối, ảnh tải lên và bài viết nháp trong vòng 30 ngày theo quy định bảo mật.",
    ],
  },
];

export default function Page() {
  return (
    <LegalPage
      title="Hướng dẫn xóa dữ liệu Facebook"
      intro="Havi tôn trọng quyền riêng tư và quyền kiểm soát dữ liệu của bạn. Trang này hướng dẫn cách ngắt kết nối Trang Facebook và xóa toàn bộ dữ liệu liên quan khỏi hệ thống Havi."
      sections={dataDeletionSections}
    />
  );
}
