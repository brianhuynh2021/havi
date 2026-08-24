/**
 * Nội dung landing theo năng lực đã có bằng chứng trong sản phẩm.
 * Kênh chưa được duyệt hoặc tính năng roadmap phải được ghi rõ là Beta/roadmap.
 */

export type Step = { n: string; title: string; desc: string };

export const heroStats = [
  { v: "Facebook Beta", l: "Xuất bản qua API khi đủ quyền Meta", icon: "🌐" },
  { v: "7 ngày", l: "Dùng thử có hạn mức, không cần thẻ", icon: "💳" },
  { v: "Duyệt trước", l: "Người dùng kiểm soát nội dung phát hành", icon: "✓" },
];




/** Các kênh siêu năng lực hỗ trợ. */
export const heroChannels = [
  { n: "Facebook Beta", b: "f", c: "#1877F2" },
  { n: "Bản nháp nội dung", b: "✍", c: "#16A34A" },
  { n: "Kịch bản video", b: "🎬", c: "#FE2C55" },
  { n: "Inbox & CRM", b: "💬", c: "#FF0000" },
];

export const steps: Step[] = [
  {
    n: "1",
    title: "30s Chụp ảnh hoặc Ghi âm",
    desc: "Chụp 1 tấm ảnh tiệm hoặc ghi âm 15s giọng nói. Không cần biết viết prompt hay am hiểu công nghệ.",
  },
  {
    n: "2",
    title: "Havi tạo bản nháp và kịch bản",
    desc: "AI gợi ý bài Facebook, kịch bản video 9:16 và câu trả lời để bạn kiểm tra trước.",
  },
  {
    n: "3",
    title: "Kiểm tra và duyệt",
    desc: "Bài chỉ đăng khi bạn bấm duyệt. Bạn nắm toàn quyền kiểm soát thông điệp và uy tín tiệm.",
  },
  {
    n: "4",
    title: "Theo dõi inbox và kết quả",
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
    inbox: { title?: string; customerMsg: string; haviReply: string; capturedPhone: string; badge: string };
  };
}

/** Kịch bản Demo thực chiến theo 4 ngành nghề mũi nhọn */
export const industryScenarios: IndustryScenario[] = [
  {
    name: "Spa & Thẩm mỹ viện",
    badge: "SPA",
    color: "linear-gradient(135deg,#6366F1,#8B5CF6)",
    image: "/images/spa_photo_hq.jpg",
    rawInput: "Chụp 1 tấm ảnh khách làm liệu trình vi kim trị mụn sáng nay",
    tabs: {
      facebook: {
        title: "Bài đăng Fanpage Facebook",
        badge: "Facebook Feed",
        content: "🎉 Da căng bóng, sạch mụn chỉ sau 1 liệu trình vi kim tảo biển tại tiệm! Chị em nào đang bị thâm mụn, lỗ chân lông to nhắn tin ngay để nhận 1 trong 30 suất soi da & tặng serum phục hồi cao cấp tuần này nha! ✨",
      },
      video: {
        title: "Kịch bản Video TikTok / Reels (Hook 3s)",
        badge: "Short-form Video 9:16",
        hook: "🚨 3 sai lầm rửa mặt khiến mụn ẩn cứ tái đi tái lại mà 90% chị em không ngờ tới...",
        script: "1. Dùng khăn bông ẩm lau mặt ➔ Ổ vi khuẩn sinh mụn.\n2. Bỏ qua bước cấp ẩm sau khi rửa ➔ Da tiết dầu nhiều hơn.\n3. Nặn mụn bằng tay không vô trùng ➔ Thâm sẹo vĩnh viễn.\n👉 Muốn da sạch mịn đón Tết? Bấm link bio đặt lịch soi da miễn phí hôm nay!",
      },
      inbox: {
        title: "Mẫu FAQ chờ xác minh",
        badge: "Minh hoạ Inbox",
        customerMsg: "Liệu trình vi kim bên mình giá bao nhiêu vậy shop? Trị thâm tốt không?",
        haviReply: "Dạ em chào chị! Gói vi kim tảo biển bên em trọn gói 450k đang được tặng kèm 1 chai serum phục hồi B5 trị giá 250k trong tuần này ạ. Chị cho em xin Tên & SĐT để chuyên viên xếp lịch soi da và giữ suất ưu đãi cho chị nhé!",
        capturedPhone: "0912.345.678 (Khách cần trị mụn thâm)",
      },
    },
  },
  {
    name: "Môi giới Bất động sản",
    badge: "BĐS",
    color: "linear-gradient(135deg,#0068FF,#0041A8)",
    image: "/images/bds_photo_hq.jpg",
    rawInput: "Chụp 1 ảnh sổ đỏ và mặt tiền căn nhà phố Quận 7 chính chủ",
    tabs: {
      facebook: {
        title: "Bài đăng Bán Nhà Fanpage",
        badge: "Facebook Feed",
        content: "🔥 [CHÍNH CHỦ GỬI BÁN] Nhà phố Quận 7 diện tích 85m² (5x17m), đúc 3 tầng kiên cố, đường nhựa 8m ô tô tránh nhau thoải mái. Khu dân trí cao, sổ hồng riêng công chứng trong ngày. Giá đầu tư cực tốt: 4.2 tỷ (thương lượng chính chủ).",
      },
      video: {
        title: "Kịch bản Video TikTok BĐS (Hook 3s)",
        badge: "Short-form Video 9:16",
        hook: "🏡 Cầm 4 tỷ mua nhà Quận 7 liệu có căn nào đường ô tô đỗ cửa, đúc 3 tầng? Xem ngay căn này!",
        script: "Mặt tiền 5m cực thoáng, phòng khách rộng thênh thang, 4 phòng ngủ khép kín. Vị trí chỉ 5 phút ra Phú Mỹ Hưng. Sổ hồng trao tay, pháp lý sạch 100%. Anh/chị xem nhà liên hệ em ngay!",
      },
      inbox: {
        title: "Mẫu FAQ chờ xác minh",
        badge: "Minh hoạ Inbox",
        customerMsg: "Căn nhà Quận 7 này còn không em? Có hỗ trợ vay ngân hàng không?",
        haviReply: "Dạ căn này chính chủ gửi em bán độc quyền, hiện vẫn còn ạ! Nhà sổ hồng riêng nên ngân hàng hỗ trợ vay tối đa 70% lãi suất ưu đãi. Anh/chị cho em xin SĐT và thời gian tiện nhất để em dẫn anh/chị xem nhà thực tế nhé!",
        capturedPhone: "0988.765.432 (Khách xem nhà Q7 cuối tuần)",
      },
    },
  },
  {
    name: "Quán ăn & Cafe",
    badge: "F&B",
    color: "linear-gradient(135deg,#E65100,#EF6C00)",
    image: "/images/cafe_photo_hq.jpg",
    rawInput: "Ảnh món mới Cà Phê Muối & Bánh nướng phô mai giòn rụm",
    tabs: {
      facebook: {
        title: "Bài đăng Kéo Khách Fanpage",
        badge: "Facebook Feed",
        content: "☕ Món mới toanh đã có mặt tại quán: Cà phê muối béo ngậy kèm bánh nướng phô mai thơm phức! Rủ ngay cạ cứng ghé quán hôm nay: Áp dụng MUA 2 TẶNG 1 cho toàn bộ menu đồ uống mới từ 14h – 18h hàng ngày.",
      },
      video: {
        title: "Kịch bản Video Review TikTok (Hook 3s)",
        badge: "Short-form Video 9:16",
        hook: "🤫 Tiết lộ quán cafe bí mật view ngắm hoàng hôn cực chill đồ uống chỉ từ 25k ít người biết...",
        script: "Không gian mở ngập tràn cây xanh, góc nào cũng có ảnh đẹp sống ảo. Đặc biệt món cafe muối kem béo ở đây uống 1 lần là ghiền. Tag ngay bạn thân vào set kèo đi thôi!",
      },
      inbox: {
        title: "Mẫu FAQ chờ xác minh",
        badge: "Minh hoạ Inbox",
        customerMsg: "Quán có nhận đặt bàn tiệc sinh nhật 12 người tối nay không bạn?",
        haviReply: "Dạ quán em còn khu vực bàn dài view kính tầng 2 cực đẹp cho nhóm 12 người tối nay ạ! Em hỗ trợ giữ bàn và trang trí sẵn cho mình nhé, anh/chị cho em xin Tên & SĐT để nhân viên chuẩn bị chu đáo nha!",
        capturedPhone: "0903.112.233 (Đặt bàn sinh nhật 12 người)",
      },
    },
  },
  {
    name: "Đào tạo & Dịch vụ nghề",
    badge: "DẠY NGHỀ",
    color: "linear-gradient(135deg,#7C3AED,#5B21B6)",
    image: "/images/hero_ai_studio_hq.jpg",
    rawInput: "Ảnh học viên thực hành kỹ thuật số và tay nghề thực chiến",
    tabs: {
      facebook: {
        title: "Bài đăng Tuyển sinh & Khóa học",
        badge: "Facebook Feed",
        content: "💡 Học nghề không lý thuyết suông: 100% học viên được tự tay thực hành trên dự án thực tế ngay trong khóa học. Đăng ký nhận lộ trình học 1 kèm 1 và ưu đãi học phí tháng này nhé!",
      },
      video: {
        title: "Kịch bản Video Review TikTok (Hook 3s)",
        badge: "Short-form Video 9:16",
        hook: "💻 Đừng học lý thuyết suông nữa! Đây là cách học viên tự tay làm ra website bán hàng chỉ sau 2 tuần...",
        script: "1. Học thực hành 1 kèm 1 trên dự án thật.\n2. Tự tay làm web, gắn tính năng thanh toán online.\n3. Hỗ trợ việc làm ngay sau khi hoàn thành khóa học.\n👉 Đăng ký học thử 1 buổi miễn phí tại Học Viện ngay hôm nay!",
      },
      inbox: {
        title: "Mẫu FAQ chờ xác minh",
        badge: "Minh hoạ Inbox",
        customerMsg: "Khóa Lập trình Web cho người mới bắt đầu học phí thế nào và học mấy tháng ạ?",
        haviReply: "Dạ chào bạn! Khóa Lập trình Web Khởi động kéo dài 3 tháng, đào tạo 1 kèm 1 trên dự án thật. Bạn cho mình xin SĐT hoặc Zalo để thầy giáo tư vấn chi tiết lộ trình và ưu đãi học phí tháng này nhé!",
        capturedPhone: "0971.888.999 (Học viên tìm hiểu khóa Web)",
      },
    },
  },
];

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
    title: "Văn phong thuần Việt, chốt đơn khéo",
    desc: "Hiểu đúng cách xưng hô anh/chị gần gũi, giọng điệu tự nhiên như người thật, tư vấn duyên dáng và khéo léo xin số điện thoại khách hàng.",
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
    question: "Tính năng Hot Lead Radar và chuông báo Telegram hoạt động thế nào?",
    answer:
      "Khi Havi nhận được inquiry chứa số điện thoại từ một nguồn được hỗ trợ, hệ thống có thể lưu lead và gửi cảnh báo Telegram nếu workspace đã cấu hình notifier. Thời gian nhận phụ thuộc webhook và nhà cung cấp.",
  },
  {
    question: "Tôi có được đội ngũ kỹ sư Havi hỗ trợ cài đặt ban đầu không?",
    answer:
      "Có! Đội ngũ Havi và Founder luôn đồng hành hỗ trợ 1 kèm 1 qua Hotline & Zalo: 0984 883 750. Chúng tôi hỗ trợ bạn nối Fanpage, cài đặt thông điệp tiệm và hướng dẫn vận hành trọn đời.",
  },
];
