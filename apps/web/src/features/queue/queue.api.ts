import { NETWORK_ERROR_MESSAGE, detailToMessage } from "@/features/auth/auth.api";
import { apiClient } from "@/lib/api-client/client";
import type { components } from "@/lib/api-client/schema";

export type WorkItem = components["schemas"]["WorkItem"];
export type WorkQueue = components["schemas"]["WorkQueue"];
export type ResponseMetrics = components["schemas"]["ResponseMetrics"];
export type MorningBrief = components["schemas"]["MorningBrief"];
export type Result<T> = { ok: true; data: T } | { ok: false; message: string };

export async function fetchQueue(): Promise<Result<WorkQueue>> {
  try {
    const { data, error } = await apiClient.GET("/queue");
    if (error || !data) {
      return { ok: false, message: detailToMessage(error, "Chưa tải được danh sách việc") };
    }
    return { ok: true, data };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

/** Nhận việc, hoặc trả lại hàng đợi khi `userId` là `null`. */
export async function assignInboxItem(
  itemId: string,
  userId: string | null,
): Promise<Result<WorkItem>> {
  try {
    const { data, error } = await apiClient.POST("/queue/inbox/{item_id}/assign", {
      params: { path: { item_id: itemId } },
      body: { user_id: userId },
    });
    if (error || !data) {
      return { ok: false, message: detailToMessage(error, "Chưa nhận được việc này") };
    }
    return { ok: true, data };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

export async function fetchResponseMetrics(
  start: string,
  end: string,
): Promise<Result<ResponseMetrics>> {
  try {
    const { data, error } = await apiClient.GET("/queue/response-metrics", {
      params: { query: { start, end } },
    });
    if (error || !data) {
      return { ok: false, message: detailToMessage(error, "Chưa tải được số liệu phản hồi") };
    }
    return { ok: true, data };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

export async function fetchBrief(): Promise<Result<MorningBrief>> {
  try {
    const { data, error } = await apiClient.GET("/queue/brief");
    if (error || !data) {
      return { ok: false, message: detailToMessage(error, "Chưa tải được bản tin") };
    }
    return { ok: true, data };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

/**
 * "6 giờ 42 phút" — phút thô không đọc được ở con số lớn.
 *
 * Dưới một giờ thì nói bằng phút chứ không "0 giờ 40 phút": người đọc phải hiểu
 * ngay, không phải trừ trong đầu.
 */
export function formatMinutes(minutes: number): string {
  if (minutes < 60) return `${minutes} phút`;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return rest ? `${hours} giờ ${rest} phút` : `${hours} giờ`;
}

/** Nhãn tiếng Việt cho loại việc. */
export const KIND_LABELS: Record<string, string> = {
  connection: "Kênh kết nối",
  inbox: "Khách nhắn",
  publish_failure: "Bài đăng lỗi",
  approval: "Chờ duyệt",
};

/**
 * Nhãn loại việc trong hộp thư.
 *
 * `other` cố ý **không có nhãn**: hiện chữ "Khác" cạnh mọi tin không phân loại
 * được chỉ thêm nhiễu, trong khi nó không nói thêm gì cho người trực ca.
 */
export const CATEGORY_LABELS: Record<string, string> = {
  price: "Hỏi giá",
  booking: "Đặt lịch",
  complaint: "Khiếu nại",
  info: "Hỏi thông tin",
};

/** Nhãn nền tảng — dùng chung với các màn khác. */
export const CHANNEL_LABELS: Record<string, string> = {
  facebook: "Facebook",
  facebook_page: "Facebook",
  reels: "Facebook Reels",
  tiktok: "TikTok",
  youtube: "YouTube",
  google_business: "Google Business",
  zalo_oa: "Zalo OA",
};

/**
 * "Chờ 3 giờ", "Chờ 2 ngày" — thời gian tương đối, vì con số tuyệt đối không
 * trả lời được câu hỏi người trực ca đang hỏi: *"cái này để lâu chưa?"*
 */
export function waitedFor(iso: string, now: Date = new Date()): string {
  const minutes = Math.max(0, Math.round((now.getTime() - new Date(iso).getTime()) / 60000));
  if (minutes < 1) return "vừa xong";
  if (minutes < 60) return `${minutes} phút`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} giờ`;
  return `${Math.round(hours / 24)} ngày`;
}

/**
 * Việc chờ quá lâu thì tô cảnh báo.
 *
 * Ngưỡng theo mức thiệt hại, không theo một con số chung: khách hỏi giá chờ một
 * giờ đã là lâu, còn một bản nháp chờ duyệt một ngày thì vẫn bình thường.
 */
export function isOverdue(item: WorkItem, now: Date = new Date()): boolean {
  const minutes = (now.getTime() - new Date(item.waiting_since).getTime()) / 60000;
  if (item.kind === "connection") return true;
  if (item.kind === "approval") return minutes > 60 * 24;
  if (item.kind === "publish_failure") return minutes > 60 * 4;
  if (item.category === "complaint" || item.category === "price") return minutes > 60;
  return minutes > 60 * 4;
}
