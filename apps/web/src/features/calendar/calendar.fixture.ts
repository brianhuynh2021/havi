import type { components } from "@/lib/api-client/schema";

export type PublishStatus = components["schemas"]["ContentStatus"];

/** Nhãn tiếng Việt cho trạng thái bài. Bao đủ mọi giá trị `ContentStatus` của
 * backend — thiếu một cái là UI hiện enum thô cho chủ tiệm đọc. */
export const statusLabel: Record<PublishStatus, string> = {
  draft: "Bản nháp",
  pending_approval: "Chờ duyệt",
  approved: "Đã duyệt",
  scheduled: "Đã lên lịch",
  publishing: "Đang đăng",
  published: "Đã đăng",
  failed: "Đăng lỗi",
  dead_letter: "Cần xem lại",
  dismissed: "Đã huỷ",
};

export const statusTone: Record<
  PublishStatus,
  "success" | "info" | "warning" | "neutral"
> = {
  draft: "neutral",
  pending_approval: "neutral",
  approved: "info",
  scheduled: "info",
  publishing: "neutral",
  published: "success",
  failed: "warning",
  dead_letter: "warning",
  dismissed: "neutral",
};

export const weekdayLabels = ["Th 2", "Th 3", "Th 4", "Th 5", "Th 6", "Th 7", "CN"];
