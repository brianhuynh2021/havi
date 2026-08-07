export const reportsFixture = {
  insight:
    "Tuần này Havi đã đăng đều 5/7 ngày, bài về gội đầu thảo dược kéo khách nhiều nhất. Khách từ Google Maps đang tăng — chị có thể mời thêm khách cũ đánh giá 5★ để giữ đà này.",
  stats: [
    { label: "Bài đã đăng", value: "8" },
    { label: "Khách mới liên hệ", value: "12" },
    { label: "Lượt tiếp cận", value: "3.240" },
  ],
  attribution: [
    { source: "Fanpage", percent: 52 },
    { source: "Google Maps", percent: 31 },
    { source: "Nhóm", percent: 17 },
  ],
  weeklyPosts: [
    { day: "Th 2", count: 1 },
    { day: "Th 3", count: 2 },
    { day: "Th 4", count: 0 },
    { day: "Th 5", count: 2 },
    { day: "Th 6", count: 1 },
    { day: "Th 7", count: 0 },
    { day: "CN", count: 2 },
  ],
} as const;
