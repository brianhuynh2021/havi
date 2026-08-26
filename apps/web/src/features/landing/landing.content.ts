// i18n-data: nội dung landing là dữ liệu, `landing-screen.tsx` dịch bằng `t()`
// khi render — cùng cách tổ chức với `features/billing/billing.content.ts`.
/**
 * Nội dung landing — theo năng lực đã có bằng chứng trong sản phẩm.
 *
 * Havi bán **quyền kiểm soát vận hành**, không bán kết quả marketing. Vì vậy
 * mọi câu ở đây nói về *việc Havi làm được* (gom kênh về một nơi, chặn bài chưa
 * duyệt, giữ dấu vết), không nói về *kết quả kinh doanh của khách* (khách đến,
 * doanh thu, tăng trưởng).
 *
 * Kênh chưa được nền tảng duyệt hoặc tính năng còn trong lộ trình **phải** được
 * ghi rõ là Beta/lộ trình. Một dòng hứa sai ở đây đắt hơn một tính năng thiếu.
 */

export const heroStats = [
  { v: "Facebook Beta", l: "Xuất bản qua API chính thức khi đủ quyền Meta", icon: "🌐" },
  { v: "Một nơi", l: "Kênh, nội dung, lịch đăng, hội thoại và phân quyền", icon: "🎛️" },
  { v: "Duyệt trước", l: "Không gì lên kênh khi bạn chưa bấm duyệt", icon: "✓" },
];

/** Nguyên tắc sản phẩm */
export const principles = [
  {
    title: "Bạn duyệt trước, luôn luôn",
    desc: "Không nội dung nào ra kênh khi chưa có người bấm duyệt. Đây là ràng buộc của hệ thống, không phải một tuỳ chọn có thể tắt đi cho nhanh.",
  },
  {
    title: "API chính thức, trạng thái trung thực",
    desc: "Havi chỉ báo “đã đăng” sau khi nền tảng trả về mã bài thật. Gửi đi mà nền tảng chưa xác nhận thì ghi là chưa chắc chắn, chứ không tô xanh cho đẹp bảng điều khiển.",
  },
  {
    title: "Havi hỗ trợ, người thật quyết định",
    desc: "Havi soạn nháp, tóm tắt hội thoại và gợi ý câu trả lời. Havi không đặt mục tiêu, không chọn chiến lược và không bấm gửi thay bạn.",
  },
  {
    title: "Dấu vết ở lại, kể cả khi nền tảng đổi",
    desc: "Nội dung đã duyệt, lịch sử ai làm gì, hội thoại với từng khách và bộ quy tắc thương hiệu nằm trong workspace của bạn. Nền tảng đổi chính sách thì bạn đổi đường ra kênh, không mất phần đã tích luỹ.",
  },
];

export interface FAQItem {
  question: string;
  answer: string;
}

export const faqs: FAQItem[] = [
  {
    question: "Havi khác gì công cụ đăng bài hay công cụ viết nội dung bằng AI?",
    answer:
      "Havi hướng tới thao tác đơn giản trên điện thoại, nhưng việc chính của nó không phải là viết bài. Havi là nơi quản trị: kênh nào đang sống, ai được soạn, ai được duyệt, bài nào đã lên, bài nào hỏng và vì sao, hội thoại nào chưa ai trả lời. Soạn bài và lên lịch là một tính năng hỗ trợ nằm trong đó, không phải lý do tồn tại của sản phẩm.",
  },
  {
    question: "Havi có tự động đăng bài lên mạng xã hội của tôi không?",
    answer:
      "Tuyệt đối KHÔNG. Nguyên tắc cốt lõi số 1 của Havi là 'Bạn duyệt trước, luôn luôn'. Bài chỉ ra kênh sau khi có người vào kiểm tra và bấm duyệt. Quy trình soạn → duyệt → đăng là ràng buộc của hệ thống, không phải tuỳ chọn.",
  },
  {
    question: "Nếu Facebook đổi chính sách hoặc cắt quyền API thì tôi mất gì?",
    answer:
      "Bạn mất đường ra kênh đó cho tới khi nối lại được — điều này đúng với mọi công cụ dùng API chính thức, và Havi sẽ hiện rõ kênh đang hỏng thay vì im lặng. Thứ bạn không mất là phần nằm trong Havi: kho nội dung đã duyệt, lịch sử ai duyệt cái gì lúc nào, hội thoại đã lưu, cấu trúc thương hiệu và phân quyền. Đó là lý do Havi là nơi quản trị chứ không phải một đường ống đăng bài.",
  },
  {
    question: "Havi hiện chạy được những kênh nào?",
    answer:
      "Facebook (Trang, Reels và Messenger) đang ở giai đoạn Beta, xuất bản qua API chính thức khi workspace đủ quyền Meta. TikTok là kênh kế tiếp, sau đó tới YouTube Shorts rồi Google Business Profile. Mỗi kênh chỉ được bật sau khi nền tảng duyệt và Havi đọc lại được trạng thái thật — không có kênh nào được bật sớm để bảng tính năng trông dài hơn.",
  },
  {
    question: "Nhiều người cùng dùng thì kiểm soát thế nào?",
    answer:
      "Mỗi thành viên có một vai: chủ workspace, người soạn, người duyệt hoặc người trực hội thoại. Người soạn không thấy nút duyệt, và quyền được kiểm lại ở phía máy chủ chứ không chỉ ẩn nút trên giao diện. Mọi thao tác có ảnh hưởng ra ngoài đều được ghi lại: ai làm, lúc nào, kết quả ra sao.",
  },
  {
    question: "Có cần nhập thẻ tín dụng để dùng thử 7 ngày không?",
    answer:
      "Không. Workspace mới có 7 ngày dùng thử với hạn mức. Sau đó bạn chủ động tạo checkout VietQR nếu muốn nâng cấp — Havi không tự trừ tiền và không giữ thông tin thẻ.",
  },
  {
    question: "Tôi có được hỗ trợ khi nối kênh lần đầu không?",
    answer:
      "Có. Havi đang trong giai đoạn pilot nên đội ngũ hỗ trợ trực tiếp việc nối Fanpage và cấu hình ban đầu qua Hotline & Zalo: 0984 883 750. Đây là hỗ trợ triển khai của giai đoạn pilot, không phải cam kết dịch vụ trọn đời.",
  },
];
