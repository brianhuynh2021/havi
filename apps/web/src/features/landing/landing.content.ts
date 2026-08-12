/**
 * Nội dung Landing Page.
 *
 * Mọi câu chữ ở đây là claim công khai, nên phải bám capability THẬT chứ không
 * bám prototype (ROADMAP §2: "Những claim chưa có production capability không
 * được đưa lên landing page public"; §10 xếp "landing hứa nhiều hơn sản phẩm"
 * là rủi ro mất niềm tin + pháp lý).
 */

export type Step = { n: string; title: string; desc: string };

export const heroStats = [
  { v: "Đa kênh", l: "Facebook, Zalo OA, Google Business & Email" },
  { v: "< 90 giây", l: "từ ý tưởng đến bài nháp hoàn chỉnh" },
  { v: "100%", l: "nội dung và email đều chờ bạn duyệt" },
];

/** Các kênh hỗ trợ bài đăng & email chăm sóc. */
export const heroChannels = [
  { n: "Facebook", b: "f", c: "#1877F2" },
  { n: "Zalo OA", b: "Z", c: "#0068FF" },
  { n: "Google Business", b: "G", c: "#16A34A" },
  { n: "Bản tin Email", b: "@", c: "#EA4335" },
];

export const steps: Step[] = [
  {
    n: "1",
    title: "Ý tưởng siêu tốc",
    desc: "Vài tấm ảnh chụp bằng điện thoại, đoạn ghi âm ngắn hay ba gạch đầu dòng. Không cần vắt óc nghĩ câu chữ hay am hiểu công nghệ.",
  },
  {
    n: "2",
    title: "Nội dung & Email sẵn sàng",
    desc: "Havi biên soạn nội dung đúng giọng cho Facebook, Zalo, Google & Email chăm sóc — bạn chỉ đọc lướt rồi sửa nếu muốn.",
  },
  {
    n: "3",
    title: "Duyệt bài an tâm 100%",
    desc: "Không có bài hay email nào ra ngoài khi bạn chưa bấm duyệt. Bạn hoàn toàn làm chủ uy tín tiệm của mình.",
  },
  {
    n: "4",
    title: "Thu hút & Chăm sóc khách",
    desc: "Bài đã duyệt tự xếp vào lịch tuần theo giờ Việt Nam, giữ nhịp tương tác liên tục để kéo khách hàng thật về tiệm và shop của bạn.",
  },
];

/** Các nhóm ngành & người kinh doanh thu hút traffic. */
export const industries = [
  {
    name: "Spa / Tiệm làm đẹp & Clinic",
    badge: "SP",
    color: "linear-gradient(135deg,#D97736,#A85324)",
    image: "/images/spa_photo.jpg",
    rows: [
      { k: "Hình ảnh", t: "Chụp một tấm ảnh khách trước/sau khi làm liệu trình" },
      { k: "Bài viết", t: "Havi viết bài Facebook thu hút và email nhắc lịch chăm sóc da chuẩn vị" },
      { k: "Duyệt bài", t: "Bạn đọc lướt, sửa vài chữ rồi bấm duyệt 1 chạm" },
    ],
  },
  {
    name: "Môi giới BĐS & Dự án",
    badge: "BĐS",
    color: "linear-gradient(135deg,#0068FF,#0041A8)",
    image: "/images/bds_photo.jpg",
    rows: [
      { k: "Thông tin", t: "Ảnh nhà đất thực tế và thông tin pháp lý ngắn gọn" },
      { k: "Bài viết", t: "Havi soạn bài đăng bán nhà chuẩn vị & email báo giá gửi khách nét" },
      { k: "Duyệt bài", t: "Xem lại lịch sử mọi lần sửa, giữ trọn uy tín" },
    ],
  },
  {
    name: "Quán ăn / Cà phê / F&B",
    badge: "CF",
    color: "linear-gradient(135deg,#E65100,#EF6C00)",
    image: "/images/cafe_photo.jpg",
    rows: [
      { k: "Món mới", t: "Ảnh món mới hoặc vài dòng về ưu đãi trong tuần" },
      { k: "Bài viết", t: "Havi tạo bài đăng kéo khách ghé quán & bản tin email ưu đãi hội viên" },
      { k: "Duyệt bài", t: "Duyệt từng bài hoặc duyệt cả loạt chỉ với 1 chạm" },
    ],
  },
  {
    name: "Shop Online & Traffic Builder",
    badge: "TF",
    color: "linear-gradient(135deg,#7C3AED,#5B21B6)",
    image: "/images/hero_photo.jpg",
    rows: [
      { k: "Sản phẩm", t: "Ảnh sản phẩm mới về hoặc chia sẻ giá trị kinh nghiệm" },
      { k: "Bài viết", t: "Havi tạo chuỗi nội dung kéo traffic đa kênh & email chào hàng tự động" },
      { k: "Duyệt bài", t: "Kiểm soát 100% thông điệp trước khi chạm tới khách hàng" },
    ],
  },
];

/** Nguyên tắc sản phẩm */
export const principles = [
  {
    title: "Bạn duyệt trước, luôn luôn",
    desc: "Mặc định không có bài đăng hay email nào gửi đi khi bạn chưa duyệt. Đây là quy tắc cố định trong hệ thống.",
  },
  {
    title: "Chỉ dùng API chính thức",
    desc: "Havi không crawl hội nhóm, không giả danh khách hàng, không làm gì trái điều khoản nền tảng.",
  },
  {
    title: "Tiếng Việt là gốc",
    desc: "Viết như người chủ tiệm hay môi giới tự viết — xưng hô chị/anh đúng cách, sang trọng mà gần gũi.",
  },
];
