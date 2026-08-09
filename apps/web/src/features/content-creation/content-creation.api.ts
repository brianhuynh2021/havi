import { apiClient } from "@/lib/api-client/client";
import { NETWORK_ERROR_MESSAGE } from "@/features/auth/auth.api";
import type { components } from "@/lib/api-client/schema";

export type ContentItem = components["schemas"]["ContentItem"];
export type ContentJob = components["schemas"]["ContentJob"];
export type JobStatus = components["schemas"]["ContentJobStatus"];
export type RawInput = components["schemas"]["RawInput"];

export type Result<T> = { ok: true; data: T } | { ok: false; message: string };

const GENERIC_ERROR = "Có lỗi xảy ra, thử lại giúp chị nhé.";

/**
 * Upload ảnh: xin ticket → POST thẳng lên object storage → báo API đã xong.
 *
 * Ba lượt chứ không một, và bytes không đi qua API: presigned POST cho client
 * bắn thẳng lên storage, nên API không phải gánh băng thông ảnh và không giữ
 * file tạm (ROADMAP §3 "Không lưu file upload trong database hoặc filesystem
 * tạm của API"). Giới hạn dung lượng do storage tự chặn bằng
 * `content-length-range` trong ticket — không tin client tự khai.
 */
export async function uploadImage(file: File): Promise<Result<string>> {
  try {
    const ticket = await apiClient.POST("/media/upload-ticket", {
      body: {
        filename: file.name,
        content_type: file.type,
        type: "image",
      },
    });
    if (ticket.error || !ticket.data) {
      return {
        ok: false,
        message:
          ticket.response?.status === 415
            ? `Havi chưa nhận được định dạng ảnh này (${file.type || "không rõ"})`
            : "Chưa tải được ảnh lên, thử lại giúp chị nhé.",
      };
    }

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
    });
    if (!uploaded.ok) {
      return {
        ok: false,
        message:
          uploaded.status === 400
            ? "Ảnh quá nặng hoặc sai định dạng — chọn ảnh khác giúp chị nhé."
            : "Tải ảnh lên chưa xong, thử lại giúp chị nhé.",
      };
    }

    // Storage nhận rồi không có nghĩa là xong: phải để API xác nhận object có
    // thật (và đúng magic bytes) rồi mới chuyển pending → raw.
    const completed = await apiClient.POST("/media/{asset_id}/complete", {
      params: { path: { asset_id: ticket.data.asset_id } },
    });
    if (completed.error || !completed.data) {
      return { ok: false, message: "Ảnh tải lên chưa hợp lệ, thử ảnh khác nhé." };
    }

    return { ok: true, data: ticket.data.asset_id };
  } catch {
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
      headers: { "Idempotency-Key": idempotencyKey },
    });
    if (error || !data) {
      if (response?.status === 409) {
        return {
          ok: false,
          message: "Chưa hoàn thành onboarding nên chưa tạo bài được.",
        };
      }
      if (response?.status === 429) {
        // Backend dùng 429 cho hai thứ khác nhau và câu trả lời cho chủ tiệm cũng
        // khác: hết quota tháng thì chờ tới đầu tháng (hoặc nâng gói), còn bấm quá
        // nhanh thì chờ vài phút. Phân biệt bằng `detail` vì đó là thứ backend đã
        // viết sẵn bằng tiếng Việt cho từng trường hợp.
        const detail =
          typeof error === "object" && error && "detail" in error
            ? String((error as { detail?: unknown }).detail ?? "")
            : "";
        return {
          ok: false,
          message: detail || "Chị thao tác hơi nhanh — đợi một chút rồi thử lại nhé.",
        };
      }
      return { ok: false, message: GENERIC_ERROR };
    }
    return { ok: true, data };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
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

export async function approveItem(itemId: string): Promise<Result<ContentItem>> {
  try {
    const { data, error, response } = await apiClient.POST(
      "/content/{content_id}/approve",
      { params: { path: { content_id: itemId } }, body: {} },
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
