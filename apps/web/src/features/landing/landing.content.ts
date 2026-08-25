/**
 * Nội dung landing theo năng lực đã có bằng chứng trong sản phẩm.
 * Kênh chưa được duyệt hoặc tính năng roadmap phải được ghi rõ là Beta/roadmap.
 */

export type Step = { n: string; title: string; desc: string };

export const heroStats = [
  { v: "Facebook Beta", l: "Xuất bản qua API chính thức khi đủ quyền Meta", icon: "🌐" },
  { v: "7 ngày", l: "Dùng thử có hạn mức, không cần thẻ", icon: "💳" },
  { v: "Duyệt trước", l: "Không gì lên kênh khi bạn chưa bấm duyệt", icon: "✓" },
];




/** Các kênh siêu năng lực hỗ trợ. */
export const heroChannels = [
  { n: "Facebook Beta", b: "f", c: "#1877F2" },
  { n: "Lịch đăng", b: "📅", c: "#16A34A" },
  { n: "Hội thoại", b: "💬", c: "#7C3AED" },
  { n: "Đội ngũ & phân quyền", b: "👥", c: "#EA580C" },
];

export const steps: Step[] = [
  {
    n: "1",
    title: "Chụp ảnh, ghi âm, hoặc tải clip lên",
    desc: "Ảnh và ghi chú để Havi soạn bài; clip bạn đã quay sẵn thì tải thẳng lên — Havi không sửa video.",
  },
  {
    n: "2",
    title: "Havi soạn bản nháp",
    desc: "AI gợi ý bài Facebook và câu trả lời cho khách, để bạn kiểm tra trước khi đăng.",
  },
  {
    n: "3",
    title: "Kiểm tra và duyệt",
    desc: "Bài chỉ đăng khi bạn bấm duyệt. Bạn nắm toàn quyền kiểm soát thông điệp và uy tín tiệm.",
  },
  {
    n: "4",
    title: "Theo dõi hội thoại và trạng thái",
    desc: "Havi lưu inquiry nhận được, gợi ý phản hồi và chỉ tự gửi FAQ đã được duyệt trước.",
  },
];

export interface IndustryScenario {
  name: string;
  badge: string;
  color: string;
  image: string;
  rawInput: string;
  tabs: {
    facebook: { title: string; content: string; badge: string };
    video: { title: string; hook: string; script: string; badge: string };
    inbox: { title?: string; customerMsg: string; haviReply: string; badge: string };
  };
}

/** Kịch bản Demo thực chiến theo 4 ngành nghề mũi nhọn */

/** Nguyên tắc sản phẩm */
export const principles = [
  {
    title: "Bạn duyệt trước, luôn luôn",
    desc: "Không bao giờ tự ý đăng bài khi bạn chưa xem qua. Bạn nắm trọn 100% quyền kiểm soát nội dung và hình ảnh của tiệm.",
  },
  {
    title: "API chính thức, trạng thái trung thực",
    desc: "Không dùng tool lậu hoặc báo thành công khi nền tảng chưa xác nhận. Quyền truy cập vẫn phụ thuộc chính sách của từng nền tảng.",
  },
  {
    title: "Bản nháp hữu ích, người thật quyết định",
    desc: "Havi có thể gợi ý nội dung và câu trả lời; người dùng chịu trách nhiệm kiểm tra sự thật, cách xưng hô và bấm gửi.",
  },
];

export interface FAQItem {
  question: string;
  answer: string;
}

export const faqs: FAQItem[] = [
  {
    question: "Tôi không rành máy tính hay công nghệ thì có dùng được Havi không?",
    answer:
      "Havi hướng tới thao tác đơn giản trên điện thoại. Bạn có thể nạp tư liệu để nhận bản nháp bài viết và kịch bản; hãy luôn kiểm tra thông tin trước khi duyệt.",
  },
  {
    question: "Havi có tự động đăng bài lên mạng xã hội của tôi không?",
    answer:
      "Tuyệt đối KHÔNG. Nguyên tắc cốt lõi số 1 của Havi là 'Bạn duyệt trước, luôn luôn'. Havi chỉ tạo sẵn bản nháp chất lượng cao, bài chỉ được phát hành khi bạn vào kiểm tra và nhấn nút 'Duyệt & Đăng'. Bạn luôn nắm 100% quyền kiểm soát uy tín thương hiệu.",
  },
  {
    question: "Có cần nhập thẻ tín dụng hay thẻ Visa để dùng thử 7 ngày không?",
    answer:
      "Không. Workspace mới có 7 ngày dùng thử với hạn mức token. Sau đó bạn có thể chủ động tạo checkout VietQR nếu muốn nâng cấp.",
  },
  {
    question: "Havi quản lý hội thoại từ các kênh như thế nào?",
    answer:
      "Havi đưa tin nhắn, bình luận và đánh giá từ kênh được hỗ trợ vào một hộp thư chung. Bản nháp phản hồi luôn chờ người dùng kiểm tra và gửi; chỉ FAQ khớp chính xác và đã duyệt mới có thể tự trả lời.",
  },
  {
    question: "Tôi có được đội ngũ kỹ sư Havi hỗ trợ cài đặt ban đầu không?",
    answer:
      "Có! Đội ngũ Havi và Founder luôn đồng hành hỗ trợ 1 kèm 1 qua Hotline & Zalo: 0984 883 750. Chúng tôi hỗ trợ bạn nối Fanpage, cài đặt thông điệp tiệm và hướng dẫn vận hành trọn đời.",
  },
];
