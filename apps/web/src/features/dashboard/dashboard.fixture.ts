export const dashboardFixture = {
  greeting: "Chào buổi sáng, chị Hương",
  dateLine:
    "Thứ Bảy, 1 tháng 8 — hôm nay Havi có vài việc đã lo sẵn cho chị.",
  stats: [
    { value: "3", label: "bài chờ đăng tuần này" },
    { value: "2", label: "khách mới đang hỏi giá" },
    { value: "12", label: "khách đến tiệm nhờ kênh online tuần này" },
  ],
  suggestions: [
    {
      tag: "Từ kho ảnh cũ",
      text: "Ảnh gội đầu thảo dược đăng tháng trước vẫn đang có lượt lưu. Havi đã biến thành bài gọi lại khách cũ cho chiều nay.",
      done: false,
      time: "",
    },
    {
      tag: "Theo trend",
      text: "Trời mưa dễ mệt mỏi. Havi đã soạn sẵn một bài chăm sóc da mùa ẩm và lên lịch đăng lúc 19:30.",
      done: true,
      time: "19:30",
    },
  ],
  activities: [
    {
      time: "14:20",
      text: "Ca chăm da của chị Hằng vừa xong — đã nhắn Zalo nhắc chị chụp 1 tấm trước/sau (khách đã đồng ý)",
      tag: "Nguyên liệu",
    },
    {
      time: "08:30",
      text: "Chị Mai hỏi giá combo trên Fanpage — Havi đã soạn sẵn câu trả lời, chờ chị bấm gửi",
      tag: "Khách",
    },
    {
      time: "21:04",
      text: "Khách hỏi giờ mở cửa lúc 21:04 — Havi trả lời ngay bằng câu FAQ đã duyệt, khách chốt lịch CN 14:00",
      tag: "Trực đêm",
    },
    {
      time: "08:00",
      text: "Đã gửi voucher giảm 20% cho chị Ngọc Anh (chị duyệt hôm qua) — khách cũ 15 ngày",
      tag: "Chăm sóc",
    },
    {
      time: "Hôm qua",
      text: "Đã mời 3 khách vừa làm xong đánh giá 5★ trên Google Maps — 2 người đã viết",
      tag: "Đánh giá",
    },
    {
      time: "Hôm qua",
      text: "Bài ảnh Before/After đạt 480 lượt tiếp cận, 12 lượt chia sẻ",
      tag: "Bài đăng",
    },
    {
      time: "Hôm qua",
      text: "Đã cập nhật giờ mở cửa mới lên Google Maps",
      tag: "Maps",
    },
  ],
} as const;
