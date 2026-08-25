import { apiClient } from "@/lib/api-client/client";
import { NETWORK_ERROR_MESSAGE } from "@/features/auth/auth.api";
import type { components } from "@/lib/api-client/schema";

export type PublishJob = components["schemas"]["PublishJob"];
export type PublishFailureKind = components["schemas"]["PublishFailureKind"];

export type Result<T> = { ok: true; data: T } | { ok: false; message: string };

const GENERIC_ERROR = "Có lỗi xảy ra, thử lại giúp bạn nhé.";

/** Bài đã dừng hẳn sau nhiều lần đăng lỗi — cần chủ tiệm xử lý. */
export async function listDeadLetterJobs(): Promise<Result<PublishJob[]>> {
  try {
    const { data, error } = await apiClient.GET("/content/publish-jobs", {
      params: { query: { status: "dead_letter" } },
    });
    if (error || !data) return { ok: false, message: GENERIC_ERROR };
    // Không tin kiểu của generated client: kiểu mô tả hợp đồng, không phải thứ
    // đã về trên dây.
    if (!Array.isArray(data)) return { ok: false, message: GENERIC_ERROR };
    return { ok: true, data };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

/**
 * Bấm "Thử lại" một lượt đăng đã dừng hẳn.
 *
 * Backend chạy đồng bộ và trả kết quả thật, nên `data.status` sau lời gọi này
 * đã là kết quả của lần thử vừa rồi (`succeeded` hoặc lại `dead_letter`) — UI
 * không phải poll.
 */
export async function retryPublishJob(jobId: string): Promise<Result<PublishJob>> {
  try {
    const { data, error, response } = await apiClient.POST(
      "/content/publish-jobs/{job_id}/retry",
      { params: { path: { job_id: jobId } } },
    );
    if (error || !data) {
      return {
        ok: false,
        message:
          response?.status === 409
            ? // 409 = bài này vừa đổi trạng thái ở nơi khác (scheduler đã nhận,
              // hoặc đã đăng xong). Nói theo hướng "tải lại" chứ không "thử
              // lại" để chủ tiệm không bấm mãi một nút không còn hợp lệ.
              "Bài này vừa đổi trạng thái — tải lại danh sách giúp bạn nhé."
            : response?.status === 404
              ? "Không tìm thấy lượt đăng này."
              : GENERIC_ERROR,
      };
    }
    return { ok: true, data };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

/**
 * Ba loại lỗi cần ba cách xử lý khác nhau — nói rõ để chủ tiệm biết phải làm gì
 * thay vì chỉ thấy "đăng lỗi" rồi bấm thử lại vô nghĩa.
 *
 * `auth_permission` cố ý KHÔNG có nút thử lại: token đã hỏng thì thử lại vẫn
 * hỏng y hệt cho tới khi nối lại kênh. Đưa nút vào đó là mời người ta bấm mười
 * lần rồi kết luận Havi hỏng.
 */
export function failureCopy(kind: PublishFailureKind | null | undefined): {
  title: string;
  hint: string;
  canRetry: boolean;
  needsReconnect: boolean;
} {
  switch (kind) {
    case "auth_permission":
      return {
        title: "Mất quyền đăng bài",
        hint: "Havi không còn quyền đăng lên Page. Bạn nối lại kênh ở Cài đặt rồi bài sẽ đăng được.",
        canRetry: false,
        needsReconnect: true,
      };
    case "validation_permanent":
      return {
        title: "Nền tảng từ chối nội dung",
        hint: "Facebook không nhận bài này. Bạn sửa nội dung ở tab Tạo nội dung rồi bấm thử lại.",
        // Vẫn cho thử lại: `run_job` đọc lại `content_item` mỗi lượt, nên sau khi
        // sửa text thì lần thử sau gửi bản mới. Ẩn nút ở đây là chặn đúng con
        // đường khắc phục duy nhất có tác dụng.
        canRetry: true,
        needsReconnect: false,
      };
    case "temporary":
      return {
        title: "Lỗi tạm thời",
        hint: "Havi đã thử lại vài lần nhưng chưa được. Bạn bấm thử lại nhé.",
        canRetry: true,
        needsReconnect: false,
      };
    default:
      // Job dead-letter mà không có `failure_kind` là chuyện không nên xảy ra,
      // nhưng cho bấm thử lại vẫn tốt hơn là một thẻ chết không có hành động nào.
      return {
        title: "Đăng chưa được",
        hint: "Bạn bấm thử lại nhé.",
        canRetry: true,
        needsReconnect: false,
      };
  }
}
