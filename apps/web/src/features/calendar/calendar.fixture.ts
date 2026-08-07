export type PublishStatus = "scheduled" | "publishing" | "published" | "failed";

export type ScheduledPost = {
  id: string;
  time: string;
  channel: "Facebook" | "Zalo OA" | "Google Business" | "Reels" | "TikTok";
  excerpt: string;
  status: PublishStatus;
};

export type CalendarDay = {
  label: string;
  dateLine: string;
  isToday?: boolean;
  posts: ScheduledPost[];
};

// Đồng bộ từ content_item.scheduled_at của các bài đã duyệt (roadmap §5, Tuần 6).
export const calendarFixture: CalendarDay[] = [
  { label: "Th 2", dateLine: "27/07", posts: [] },
  {
    label: "Th 3",
    dateLine: "28/07",
    posts: [
      {
        id: "post-1",
        time: "09:00",
        channel: "Facebook",
        excerpt: "Ưu đãi gội đầu thảo dược cuối tuần",
        status: "published",
      },
    ],
  },
  { label: "Th 4", dateLine: "29/07", posts: [] },
  {
    label: "Th 5",
    dateLine: "30/07",
    isToday: true,
    posts: [
      {
        id: "post-2",
        time: "10:30",
        channel: "Zalo OA",
        excerpt: "Nhắc khách quen đặt lịch tuần này",
        status: "scheduled",
      },
      {
        id: "post-3",
        time: "19:30",
        channel: "Facebook",
        excerpt: "Bài chăm sóc da mùa ẩm",
        status: "scheduled",
      },
    ],
  },
  {
    label: "Th 6",
    dateLine: "31/07",
    posts: [
      {
        id: "post-4",
        time: "08:00",
        channel: "Google Business",
        excerpt: "Cập nhật giờ mở cửa mới",
        status: "failed",
      },
    ],
  },
  { label: "Th 7", dateLine: "01/08", posts: [] },
  {
    label: "CN",
    dateLine: "02/08",
    posts: [
      {
        id: "post-5",
        time: "17:00",
        channel: "Reels",
        excerpt: "Video before/after gội đầu thảo dược",
        status: "scheduled",
      },
    ],
  },
];
