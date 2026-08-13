import { apiClient } from "@/lib/api-client/client";
import { NETWORK_ERROR_MESSAGE, detailToMessage } from "@/features/auth/auth.api";
import type { components } from "@/lib/api-client/schema";

export type ContentItem = components["schemas"]["ContentItem"];
export type ContentJob = components["schemas"]["ContentJob"];
export type JobStatus = components["schemas"]["ContentJobStatus"];
export type RawInput = components["schemas"]["RawInput"];
export type MediaAsset = components["schemas"]["MediaAsset"];
export type Channel = components["schemas"]["Channel"];

export type Result<T> = { ok: true; data: T } | { ok: false; message: string };

const GENERIC_ERROR = "Có lỗi xảy ra, thử lại giúp chị nhé.";

type UploadImageOptions = {
  signal?: AbortSignal;
  onProgress?: (percent: number) => void;
};

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}

/** `video/*` → media type `video`, còn lại coi là ảnh. Backend whitelist content
 * type chặt hơn thế và trả 415 nếu lệch — đây chỉ là chọn đúng nhánh để hỏi. */
export function mediaTypeOf(file: File): "image" | "video" {
  return file.type.startsWith("video/") ? "video" : "image";
}

/**
 * Upload ảnh hoặc clip: xin ticket → POST thẳng lên object storage → báo API đã xong.
 *
 * Ba lượt chứ không một, và bytes không đi qua API: presigned POST cho client
 * bắn thẳng lên storage, nên API không phải gánh băng thông ảnh và không giữ
 * file tạm (ROADMAP §3 "Không lưu file upload trong database hoặc filesystem
 * tạm của API"). Giới hạn dung lượng do storage tự chặn bằng
 * `content-length-range` trong ticket — không tin client tự khai.
 *
 * Trả về cả asset chứ không chỉ id: với video, lượt `complete` là nơi backend
 * probe clip xong và trả về `eligible_channels`. Chủ tiệm phải thấy "clip này
 * đăng được Reels nhưng không đăng được Shorts" ngay bây giờ — lúc còn quay lại
 * được, chứ không phải lúc scheduler gọi API nền tảng và đã lỡ giờ đăng.
 */
export async function uploadMedia(
  file: File,
  options: UploadImageOptions = {},
): Promise<Result<MediaAsset>> {
  const mediaType = mediaTypeOf(file);
  const noun = mediaType === "video" ? "clip" : "ảnh";
  try {
    options.onProgress?.(5);
    const ticket = await apiClient.POST("/media/upload-ticket", {
      body: {
        filename: file.name,
        content_type: file.type,
        type: mediaType,
      },
    });
    if (ticket.error || !ticket.data) {
      return {
        ok: false,
        message:
          ticket.response?.status === 415
            ? `Havi chưa nhận được định dạng ${noun} này (${file.type || "không rõ"})`
            : `Chưa tải được ${noun} lên, thử lại giúp chị nhé.`,
      };
    }
    options.onProgress?.(20);

    // Presigned POST: mọi field trong ticket phải đi kèm và `file` phải nằm
    // CUỐI form — S3/MinIO bỏ qua mọi field đứng sau phần file.
    const form = new FormData();
    for (const [key, value] of Object.entries(ticket.data.fields ?? {})) {
      form.append(key, value);
    }
    form.append("file", file);

    const uploaded = await fetch(ticket.data.upload_url, {
      method: "POST",
      body: form,
      signal: options.signal,
    });
    if (!uploaded.ok) {
      return {
        ok: false,
        message:
          uploaded.status === 400
            ? `${noun === "clip" ? "Clip" : "Ảnh"} quá nặng hoặc sai định dạng — chọn ${noun} khác giúp chị nhé.`
            : `Tải ${noun} lên chưa xong, thử lại giúp chị nhé.`,
      };
    }
    options.onProgress?.(85);

    // Storage nhận rồi không có nghĩa là xong: phải để API xác nhận object có
    // thật (và đúng magic bytes) rồi mới chuyển pending → raw. Với video, đây
    // cũng là lượt backend probe clip và trả về `eligible_channels`.
    const completed = await apiClient.POST("/media/{asset_id}/complete", {
      params: { path: { asset_id: ticket.data.asset_id } },
    });
    if (completed.error || !completed.data) {
      return {
        ok: false,
        message: `${noun === "clip" ? "Clip" : "Ảnh"} tải lên chưa hợp lệ, thử ${noun} khác nhé.`,
      };
    }
    options.onProgress?.(100);

    return { ok: true, data: completed.data };
  } catch (error) {
    if (isAbortError(error)) {
      return { ok: false, message: `Đã huỷ tải ${noun}.` };
    }
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

/**
 * Tạo content job.
 *
 * `Idempotency-Key` là bắt buộc chứ không tuỳ chọn: mỗi job là một lần gọi LLM
 * tốn tiền thật, và mạng 4G chập chờn khiến "bấm lại vì tưởng chưa ăn" là
 * chuyện thường. Cùng key trong cùng workspace luôn trả về job đầu tiên.
 */
export async function createJob(
  rawInputs: RawInput[],
  idempotencyKey: string,
): Promise<Result<ContentJob>> {
  try {
    const { data, error, response } = await apiClient.POST("/content/jobs", {
      body: { raw_inputs: rawInputs },
      headers: { "Idempotency-Key": encodeURIComponent(idempotencyKey) },
    });
    if (error || !data) {
      const detailObj = (error as { detail?: unknown } | undefined)?.detail;
      if (response?.status === 401) {
        return {
          ok: false,
          message: detailToMessage(detailObj, "Phiên đăng nhập đã hết hạn. Chị đăng nhập lại hoặc F5 tải lại trang giúp em nhé."),
        };
      }
      if (response?.status === 409) {
        return {
          ok: false,
          message: detailToMessage(detailObj, "Chưa hoàn thành onboarding nên chưa tạo bài được."),
        };
      }
      if (response?.status === 429) {
        return {
          ok: false,
          message: detailToMessage(detailObj, "Chị thao tác hơi nhanh — đợi một chút rồi thử lại nhé."),
        };
      }
      return {
        ok: false,
        message: detailToMessage(detailObj, GENERIC_ERROR),
      };
    }
    return { ok: true, data };
  } catch (err) {
    if (process.env.NODE_ENV !== "production") {
      console.error("[Havi API createJob error]:", err);
    }
    const errDetail = err instanceof Error ? err.message : String(err);
    return {
      ok: false,
      message: errDetail
        ? `Không kết nối được với Havi (${errDetail}). Kiểm tra kết nối mạng hoặc server giúp em nhé.`
        : NETWORK_ERROR_MESSAGE,
    };
  }
}

export type TokenQuota = components["schemas"]["TokenQuota"];

/** Token đã dùng / trần tháng này.
 *
 * Đo bằng token, không bằng tiền — mỗi provider một đơn giá và giá LLM đổi liên
 * tục, nên quy ra tiền ở đây là hiện một con số nhìn như đúng mà sai. */
export async function fetchQuota(): Promise<Result<TokenQuota>> {
  try {
    const { data, error } = await apiClient.GET("/content/quota");
    if (error || !data) return { ok: false, message: GENERIC_ERROR };
    return { ok: true, data };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

export async function getJob(jobId: string): Promise<Result<ContentJob>> {
  try {
    const { data, error } = await apiClient.GET("/content/jobs/{job_id}", {
      params: { path: { job_id: jobId } },
    });
    if (error || !data) return { ok: false, message: GENERIC_ERROR };
    return { ok: true, data };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

/** Bản nháp chờ duyệt — màn này mở ra là thấy ngay, không cần vừa tạo job. */
export async function listPendingItems(): Promise<Result<ContentItem[]>> {
  try {
    const { data, error } = await apiClient.GET("/content", {
      params: { query: { status: "pending_approval" } },
    });
    if (error || !data) return { ok: false, message: GENERIC_ERROR };
    return { ok: true, data: data.items };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

export async function approveItem(
  itemId: string,
  scheduledAt?: string,
): Promise<Result<ContentItem>> {
  try {
    const { data, error, response } = await apiClient.POST(
      "/content/{content_id}/approve",
      {
        params: { path: { content_id: itemId } },
        body: { scheduled_at: scheduledAt || null },
      },
    );
    if (error || !data) {
      return {
        ok: false,
        message:
          response?.status === 409
            ? "Bài này vừa đổi trạng thái ở nơi khác — tải lại giúp chị nhé."
            : GENERIC_ERROR,
      };
    }
    return { ok: true, data };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

export async function rejectItem(itemId: string): Promise<Result<ContentItem>> {
  try {
    const { data, error, response } = await apiClient.POST(
      "/content/{content_id}/reject",
      { params: { path: { content_id: itemId } } },
    );
    if (error || !data) {
      return {
        ok: false,
        message:
          response?.status === 409
            ? "Bài này vừa đổi trạng thái ở nơi khác — tải lại giúp chị nhé."
            : GENERIC_ERROR,
      };
    }
    return { ok: true, data };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

export type ContentItemVersion = components["schemas"]["ContentItemVersion"];

/** Sửa text bài. Backend tạo version mới thay vì ghi đè, và chỉ tăng
 * `version_no` khi text thật sự đổi — bấm Lưu mà không sửa gì không tạo rác. */
export async function updateItemText(
  itemId: string,
  text: string,
): Promise<Result<ContentItem>> {
  try {
    const { data, error, response } = await apiClient.PATCH(
      "/content/{content_id}",
      { params: { path: { content_id: itemId } }, body: { text } },
    );
    if (error || !data) {
      return {
        ok: false,
        message:
          response?.status === 409
            ? "Bài đang đăng hoặc đã đăng rồi nên không sửa được nữa."
            : "Chưa lưu được, thử lại giúp chị nhé.",
      };
    }
    return { ok: true, data };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

/** Lịch sử phiên bản — trả lời "ai sửa gì, lúc nào" (ROADMAP §5 Tuần 6). */
export async function listVersions(
  itemId: string,
): Promise<Result<ContentItemVersion[]>> {
  try {
    const { data, error } = await apiClient.GET("/content/{content_id}/versions", {
      params: { path: { content_id: itemId } },
    });
    if (error || !data) return { ok: false, message: GENERIC_ERROR };
    return { ok: true, data };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

export type BulkApproveOutcome = {
  approved: string[];
  rejected: { content_item_id: string; reason: string }[];
};

/** "Duyệt & đăng hết". Backend không fail cả lô khi một bài hỏng — nó trả về
 * danh sách bài không duyệt được kèm lý do, và UI phải nói ra điều đó. */
export async function approveAll(
  itemIds: string[],
): Promise<Result<BulkApproveOutcome>> {
  try {
    const { data, error } = await apiClient.POST("/content/approve-all", {
      body: { content_item_ids: itemIds },
    });
    if (error || !data) return { ok: false, message: GENERIC_ERROR };
    return {
      ok: true,
      data: { approved: data.approved ?? [], rejected: data.rejected ?? [] },
    };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}
