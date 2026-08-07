export type PublishMode = "review_first" | "full_auto";

export type DraftStatus = "pending_approval" | "approved";

export type ChannelKey =
  | "facebook_page"
  | "zalo_oa"
  | "google_business"
  | "reels"
  | "tiktok";

export const channelLabels: Record<ChannelKey, string> = {
  facebook_page: "Facebook",
  zalo_oa: "Zalo OA",
  google_business: "Google Business",
  reels: "Reels",
  tiktok: "TikTok",
};

export type RawInputChip = {
  id: string;
  kind: "photo" | "voice" | "text";
  label: string;
};

export type DraftCard = {
  id: string;
  channel: ChannelKey;
  kindLabel: string;
  body: string;
  status: DraftStatus;
};

export const rawInputsFixture: RawInputChip[] = [
  { id: "ri-1", kind: "photo", label: "3 ảnh gội đầu thảo dược" },
  { id: "ri-2", kind: "voice", label: "Ghi âm 48s — ưu đãi cuối tuần" },
  { id: "ri-3", kind: "text", label: "Ghi chú: khai trương chi nhánh 2" },
];

export const generatingJobFixture = {
  id: "job-processing",
  raw: rawInputsFixture.slice(0, 2),
  progressLabel: "Havi đang viết bài từ 3 ảnh vừa tải lên…",
};

export const draftsFixture: DraftCard[] = [
  {
    id: "draft-1",
    channel: "facebook_page",
    kindLabel: "Bài ảnh",
    body:
      "Gội đầu thảo dược cuối tuần này chị Hương có ưu đãi nhỏ cho khách quen — ghé tiệm để được chăm sóc da đầu bằng thảo dược tự nhiên nha mọi người 🌿",
    status: "pending_approval",
  },
  {
    id: "draft-2",
    channel: "zalo_oa",
    kindLabel: "Bài Zalo OA",
    body:
      "Chị/anh ơi, tiệm mới về lô thảo dược mới cho dịch vụ gội đầu — đặt lịch tuần này được giảm 10% ạ. Trả lời tin này để giữ giờ nha!",
    status: "pending_approval",
  },
  {
    id: "draft-3",
    channel: "google_business",
    kindLabel: "Cập nhật Google Business",
    body:
      "Spa An Nhiên vừa cập nhật dịch vụ gội đầu thảo dược — nguyên liệu 100% tự nhiên, phù hợp da đầu nhạy cảm. Đặt lịch ngay trong tuần.",
    status: "pending_approval",
  },
  {
    id: "draft-4",
    channel: "reels",
    kindLabel: "Video ngắn",
    body:
      "Script 20s: Cận cảnh quy trình gội đầu thảo dược — mở đầu bằng câu hỏi \"Da đầu chị có đang mệt không?\", chốt bằng ưu đãi cuối tuần.",
    status: "pending_approval",
  },
  {
    id: "draft-5",
    channel: "tiktok",
    kindLabel: "Video ngắn",
    body:
      "Script 15s theo trend \"before/after\" — ghép ảnh trước và sau khi gội đầu thảo dược, caption ngắn gọn kèm giá ưu đãi.",
    status: "pending_approval",
  },
];
