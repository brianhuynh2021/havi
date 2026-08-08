/**
 * Nội dung Landing Page.
 *
 * Mọi câu chữ ở đây là claim công khai, nên phải bám capability THẬT chứ không
 * bám prototype (ROADMAP §2: "Những claim chưa có production capability không
 * được đưa lên landing page public"; §10 xếp "landing hứa nhiều hơn sản phẩm"
 * là rủi ro mất niềm tin + pháp lý).
 *
 * Khác prototype ở những chỗ sau, đều là cố ý:
 * - Prototype nói "tự đăng đa kênh" / "4 kênh". Pilot chưa publish được kênh
 *   nào (adapter Facebook là Tuần 7), nên đổi thành "chuẩn bị sẵn theo từng
 *   kênh" và đánh dấu việc đăng là sắp có.
 * - Bỏ "săn khách hội nhóm" và "CRM tự nhắc": P2, và §4 cấm crawl group.
 * - Bỏ "làm đẹp ảnh, gắn logo": chưa có, vision là P1/P2.
 * - Bỏ Google Maps / LinkedIn / YouTube / trang rao vặt khỏi danh sách kênh.
 * - Giá 299K/599K và "dùng thử 14 ngày" chưa public (§12: chỉ public sau khi đo
 *   được cost trên khách Việt thật) — thay bằng lời mời tham gia beta.
 */

export type Step = { n: string; title: string; desc: string };

export const heroStats = [
  { v: "3 kênh", l: "Facebook, Zalo OA, Google Business" },
  { v: "< 90 giây", l: "từ liệu thô tới bản nháp" },
  { v: "100%", l: "bài đều chờ bạn duyệt" },
];

/** Chỉ 3 kênh pilot — đúng `PILOT_CHANNELS` mà Content Engine sinh nội dung. */
export const heroChannels = [
  { n: "Facebook", b: "f", c: "#1877F2" },
  { n: "Zalo OA", b: "Z", c: "#0068FF" },
  { n: "Google Business", b: "G", c: "#5FA76F" },
];

export const steps: Step[] = [
  {
    n: "1",
    title: "Đưa nguyên liệu thô",
    desc: "Vài tấm ảnh chụp bằng điện thoại hoặc ba gạch đầu dòng. Không cần viết prompt, không cần học gì.",
  },
  {
    n: "2",
    title: "Nhận bài viết sẵn sàng",
    desc: "Havi hiểu ngành của bạn và viết đúng giọng cho từng kênh — bạn chỉ đọc lướt rồi sửa nếu muốn.",
  },
  {
    n: "3",
    title: "Bạn duyệt, không ai đăng thay",
    desc: "Không có bài nào lên mạng khi bạn chưa bấm duyệt. Sửa lại bao nhiêu lần cũng được, Havi giữ đủ lịch sử.",
  },
  {
    n: "4",
    title: "Lên lịch đúng giờ vàng",
    desc: "Bài đã duyệt tự xếp vào lịch tuần theo giờ Việt Nam, để bạn nhìn một chỗ là biết tuần này tiệm đăng gì.",
  },
];

/** Ngành pilot. Mỗi dòng mô tả đúng việc Havi làm được hôm nay, không thêm
 * bước "săn khách" như prototype. */
export const industries = [
  {
    name: "Spa / Tiệm làm đẹp",
    badge: "SP",
    color: "#D4956F",
    rows: [
      { k: "Nạp", t: "Chụp một tấm ảnh khách trước/sau khi làm dịch vụ" },
      { k: "Viết", t: "Havi viết bài giới thiệu đúng giọng tiệm, tránh những câu cam kết quá đà" },
      { k: "Duyệt", t: "Bạn đọc lướt, sửa vài chữ rồi bấm duyệt" },
    ],
  },
  {
    name: "Quán ăn / Cà phê",
    badge: "AU",
    color: "#B8744D",
    rows: [
      { k: "Nạp", t: "Ảnh món mới hoặc vài dòng về ưu đãi trong tuần" },
      { k: "Viết", t: "Havi viết riêng cho Facebook, Zalo và Google Business — không copy y nguyên" },
      { k: "Duyệt", t: "Duyệt từng bài hoặc duyệt cả loạt một lần" },
    ],
  },
  {
    name: "Bán hàng online",
    badge: "OS",
    color: "#3B6B9F",
    rows: [
      { k: "Nạp", t: "Ảnh sản phẩm và giá, gõ ngắn gọn cũng được" },
      { k: "Viết", t: "Havi viết bài bán hàng bằng tiếng Việt đời thường, không sáo rỗng" },
      { k: "Duyệt", t: "Xem lại lịch sử mọi lần sửa, biết ai đổi gì lúc nào" },
    ],
  },
];

/** Nguyên tắc sản phẩm — phần này Havi làm thật nên nói chắc được. */
export const principles = [
  {
    title: "Bạn duyệt trước, luôn luôn",
    desc: "Mặc định không có bài nào lên mạng khi bạn chưa duyệt. Đây là quy tắc trong hệ thống, không phải tuỳ chọn để quên.",
  },
  {
    title: "Chỉ dùng API chính thức",
    desc: "Havi không crawl hội nhóm, không giả danh khách hàng, không làm gì trái điều khoản nền tảng.",
  },
  {
    title: "Tiếng Việt là gốc",
    desc: "Viết như người chủ tiệm tự viết — xưng hô chị/anh đúng cách, không dùng từ marketing sáo rỗng.",
  },
];
