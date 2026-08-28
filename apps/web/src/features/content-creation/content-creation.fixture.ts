export type PublishMode = "review_first";

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
  facebook_page: "Facebook Post",
  zalo_oa: "Zalo OA",
  google_business: "Google Maps SEO",
  reels: "Facebook Reels",
  tiktok: "TikTok",
  youtube: "YouTube Shorts",
};

/**
 * Bộ lọc kênh — **chỉ kênh đã chạy thật**, không phải mọi kênh `ChannelKey` có
 * tên trong bảng dịch ở trên.
 *
 * Một chip "TikTok" khi TikTok chưa được duyệt là một lời hứa: người dùng bấm,
 * thấy rỗng, và không phân biệt được "tuần này chưa có bài TikTok" với "Havi
 * chưa đăng TikTok được". Kênh nào cũng phải qua audit của nền tảng trước khi
 * xuất hiện ở đây.
 *
 * Thứ tự bật kênh: `docs/product/ROADMAP.md` §Phase C — Facebook → TikTok →
 * YouTube Shorts → Google Business Profile. Bật kênh mới thì thêm đúng ở đây.
 *
 * `facebook_page` gộp luôn Reels: cùng một Trang, và chủ Trang không nghĩ theo
 * "bài này của mình là Post hay Reels".
 */
export const CHANNEL_FILTERS: Array<{ key: ChannelKey; label: string }> = [
  { key: "facebook_page", label: "Facebook" },
];
