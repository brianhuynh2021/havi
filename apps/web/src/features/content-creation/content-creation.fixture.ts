export type PublishMode = "review_first" | "full_auto";

export type ChannelKey =
  | "facebook_page"
  | "zalo_oa"
  | "google_business"
  | "reels"
  | "tiktok"
  | "youtube";

/** Nhãn tiếng Việt cho `Channel` của backend. Không phải fixture dữ liệu —
 * đây là bảng dịch, màn nào hiện tên kênh cũng dùng chung. */
export const channelLabels: Record<ChannelKey, string> = {
  facebook_page: "Facebook",
  zalo_oa: "Zalo OA",
  google_business: "Google Business",
  reels: "Reels",
  tiktok: "TikTok",
  youtube: "YouTube",
};
