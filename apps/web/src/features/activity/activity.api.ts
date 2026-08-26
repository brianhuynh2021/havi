// i18n-data: hai cơ chế, mỗi cái cho một loại chuỗi.
//
// Câu **hằng** (`"Chưa tải được lịch, thử lại giúp bạn nhé."`) để nguyên tiếng
// Việt: nó chính là khoá, và màn hình hiện nó bằng `t(error)` — tra động vẫn
// đúng vì khoá là câu tiếng Việt. Bọc `t()` ngay tại hằng số cấp module sẽ
// **đóng băng ngôn ngữ lúc import**, đổi ngôn ngữ sau đó không có tác dụng.
//
// Câu **có chèn giá trị** thì phải dịch tại lúc dựng, bằng `translateNow`: sau
// khi đã ghép số vào thì không còn khoá nào để tra ở chỗ render nữa.
//
// Câu do backend trả về không có trong từ điển; `t()` giữ nguyên tiếng Việt.
/**
 * Lịch sử hoạt động — ai đã làm gì, lúc nào.
 *
 * Đọc từ `event_log`, bảng vốn dựng để support debug. Vì vậy mỗi dòng có
 * `input_summary` / `output_summary` chứa dữ liệu kỹ thuật thô — **không hiện
 * nguyên văn ra cho người dùng**: ở đó có thể là nội dung bài, id nền tảng, hay
 * mẩu payload webhook. Màn hình dịch `job_kind` sang tiếng người và bỏ phần thô.
 */

import { apiClient } from "@/lib/api-client/client";
import { NETWORK_ERROR_MESSAGE, detailToMessage } from "@/features/auth/auth.api";
import type { components } from "@/lib/api-client/schema";

export type ActivityEvent = components["schemas"]["EventLogRecord"];

export type Result<T> = { ok: true; data: T } | { ok: false; message: string };

export type ActivityPage = { items: ActivityEvent[]; total: number };

export async function listActivity(
  params: { errorOnly?: boolean; limit?: number; offset?: number } = {},
): Promise<Result<ActivityPage>> {
  try {
    const { data, error, response } = await apiClient.GET("/analytics/events", {
      params: {
        query: {
          error_only: params.errorOnly ?? false,
          limit: params.limit ?? 50,
          offset: params.offset ?? 0,
        },
      },
    });
    if (error || !data) {
      // 403 = vai không được xem lịch sử. Nói thẳng thay vì hiện danh sách rỗng,
      // vì rỗng trông như "chưa có hoạt động nào" — sai hẳn ý nghĩa.
      if (response?.status === 403) {
        return {
          ok: false,
          message: "Vai của bạn không xem được lịch sử hoạt động. Cần vai Người duyệt hoặc Chủ workspace.",
        };
      }
      return { ok: false, message: detailToMessage(error, "Không tải được lịch sử") };
    }
    return { ok: true, data: { items: data.items ?? [], total: data.total ?? 0 } };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}
