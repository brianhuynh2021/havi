/**
 * Nội dung Landing Page Havi - Phiên bản CRO & Tăng trưởng Thương mại.
 *
 * 4 Trụ cột siêu năng lực tạo doanh thu:
 * 1. Facebook & Instagram Post (Tự động hóa lịch đăng)
 * 2. TikTok / Reels / YouTube Shorts Video Studio (Hook 3s giật tít)
 * 3. Google Business Profile & Google Maps SEO (Kéo khách quanh khu vực)
 * 4. 24/7 Lead Care & Unified Inbox (Trực page, báo giá, xin SĐT trong 5s)
 */

export type Step = { n: string; title: string; desc: string };

export const heroStats = [
  { v: "4 Kênh Tăng Trưởng", l: "Facebook · Google Maps SEO · TikTok · YouTube Shorts", icon: "🌐" },
  { v: "Chỉ từ 6.000 đ/ngày", l: "Rẻ hơn 1 ly trà sữa mỗi tuần (189.000 đ/tháng)", icon: "💰" },
  { v: "Phản hồi < 5 Giây", l: "Trực Inbox 24/7 không để rơi mất khách nửa đêm", icon: "⚡" },
];

/** Các kênh siêu năng lực hỗ trợ. */
export const heroChannels = [
  { n: "Facebook Fanpage", b: "f", c: "#1877F2" },
  { n: "Google Maps SEO", b: "📍", c: "#16A34A" },
  { n: "TikTok Video", b: "🎵", c: "#FE2C55" },
  { n: "YouTube Shorts", b: "▶", c: "#FF0000" },
];

export const steps: Step[] = [
  {
    n: "1",
    title: "30s Chụp ảnh hoặc Ghi âm",
    desc: "Chụp 1 tấm ảnh tiệm hoặc ghi âm 15s giọng nói. Không cần biết viết prompt hay am hiểu công nghệ.",
  },
  {
    n: "2",
    title: "Havi tự làm bài & Video đa kênh",
    desc: "Tự sinh bài viết Facebook, tối ưu Google Maps SEO, kịch bản Video TikTok & YouTube Shorts 9:16 có Hook 3s và câu trả lời Inbox.",
  },
  {
    n: "3",
    title: "Duyệt 1-Chạm an tâm 100%",
    desc: "Bài chỉ đăng khi bạn bấm duyệt. Bạn nắm toàn quyền kiểm soát thông điệp và uy tín tiệm.",
  },
  {
    n: "4",
    title: "Tự động chốt đơn & Bắt SĐT 24/7",
    desc: "Khách nhắn tin lúc nửa đêm, Havi tự động đối chiếu bảng giá tiệm, tư vấn và xin số điện thoại về app.",
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
    maps: { title: string; content: string; badge: string };
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
      maps: {
        title: "Bài đăng & Tối ưu Google Maps SEO",
        badge: "Google Business Top 3",
        content: "📍 Viện Chăm Sóc Da & Trị Mụn Uy Tín Khu Vực — Giảm ngay 20% cho khách hàng tìm thấy và đặt lịch trực tiếp qua Google Maps tuần này!",
      },
      inbox: {
        title: "Trực Inbox 24/7 & Bắt Số Điện Thoại",
        badge: "Auto Lead Care",
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
      maps: {
        title: "Tối ưu Google Business Địa phương",
        badge: "Google Business Top 3",
        content: "📍 Văn Phòng Ký Gửi Nhà Đất & Định Giá BĐS Uy Tín — Hỗ trợ pháp lý, kiểm tra quy hoạch và tư vấn vay ngân hàng miễn phí 100%.",
      },
      inbox: {
        title: "Trực Inbox 24/7 & Bắt Số Điện Thoại",
        badge: "Auto Lead Care",
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
      maps: {
        title: "Bài đăng Google Maps & Menu",
        badge: "Google Business Top 3",
        content: "📍 Quán Cà Phê & Bánh Ngọt Check-in Đẹp Nhất Khu Vực — Không gian máy lạnh thoáng mát, wifi tốc độ cao, chỗ đậu xe máy ô tô rộng rãi.",
      },
      inbox: {
        title: "Trực Inbox 24/7 & Bắt Số Điện Thoại",
        badge: "Auto Lead Care",
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
    rawInput: "Ảnh học viên thực hành lập trình Web và ráp mạch thực chiến",
    tabs: {
      facebook: {
        title: "Bài đăng Tuyển sinh & Khóa học",
        badge: "Facebook Feed",
        content: "💡 Học nghề không lý thuyết suông — 100% học viên tại Trung Tâm Công Nghệ Nhật Minh được tự tay thực hành trên dự án thực tế ngay trong khóa học. Đăng ký nhận lộ trình học 1 kèm 1 và ưu đãi học phí tháng này nhé!",
      },
      video: {
        title: "Kịch bản Video Review TikTok (Hook 3s)",
        badge: "Short-form Video 9:16",
        hook: "💻 Đừng học lý thuyết suông nữa! Đây là cách học viên tự tay làm ra website bán hàng chỉ sau 2 tuần...",
        script: "1. Học thực hành 1 kèm 1 trên dự án thật.\n2. Tự tay làm web, gắn tính năng thanh toán online.\n3. Hỗ trợ việc làm ngay sau khi hoàn thành khóa học.\n👉 Đăng ký học thử 1 buổi miễn phí tại Nhật Minh Tech ngay hôm nay!",
      },
      maps: {
        title: "Google Business & Đào tạo Nghề",
        badge: "Google Business Top 3",
        content: "📍 Trung Tâm Đào Tạo Công Nghệ Nhật Minh — Cơ sở đào tạo Lập trình & Kỹ thuật số thực chiến hàng đầu. Giảng viên tận tâm, cam kết đầu ra có sản phẩm chạy thật.",
      },
      inbox: {
        title: "Trực Inbox 24/7 & Bắt Số Điện Thoại",
        badge: "Auto Lead Care",
        customerMsg: "Khóa Lập trình Web cho người mới bắt đầu học phí thế nào và học mấy tháng ạ?",
        haviReply: "Dạ chào bạn! Khóa Lập trình Web Khởi động tại Nhật Minh Tech kéo dài 3 tháng, đào tạo 1 kèm 1 trên dự án thật. Bạn cho mình xin SĐT hoặc Zalo để thầy giáo tư vấn chi tiết lộ trình và ưu đãi học phí tháng này nhé!",
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
    title: "Tuyệt đối an toàn cho Fanpage",
    desc: "Nói không với tool lậu hay spam vi phạm chính sách. Giữ Fanpage và các kênh mạng xã hội của tiệm luôn an toàn, uy tín và bền vững.",
  },
  {
    title: "Văn phong thuần Việt, chốt đơn khéo",
    desc: "Hiểu đúng cách xưng hô anh/chị gần gũi, giọng điệu tự nhiên như người thật — tư vấn duyên dáng và khéo léo xin số điện thoại khách hàng.",
  },
];

