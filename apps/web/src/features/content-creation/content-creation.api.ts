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
// Dùng `translateNow` thay hook: module này không phải component nên không gọi
// `useLanguage()` được. Đặt bí danh `t` để chỉ có MỘT tên phải nhớ, và để
// `scripts/i18n-audit.mjs` đếm được như mọi chỗ gọi khác.
import { translateNow as t } from "@/lib/i18n/language-context";
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

const GENERIC_ERROR = "Có lỗi xảy ra, thử lại giúp bạn nhé.";

type UploadImageOptions = {
  signal?: AbortSignal;
  onProgress?: (percent: number) => void;
};

function isAbortError(error: unknown): boolean {
  return typeof error === "object" && error !== null && "name" in error && error.name === "AbortError";
}

type StorageUploadResult = { ok: boolean; status: number };

/** POST multipart có tiến độ byte thật.
 *
 * `fetch` không phát sự kiện upload progress. Bản cũ vẫn nhảy 20% → 85% theo
 * các bước API nên thanh tiến độ trông như đo bytes nhưng thực ra chỉ là ba số
 * hardcode. XHR ở đây chỉ dùng cho lượt gửi thẳng lên storage; mọi API JSON vẫn
 * đi qua client typed như trước.
 */
function uploadForm(
  url: string,
  form: FormData,
  options: UploadImageOptions,
): Promise<StorageUploadResult> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    let settled = false;

    const cleanup = () => options.signal?.removeEventListener("abort", abort);
    const finish = (result: StorageUploadResult) => {
      if (settled) return;
      settled = true;
      cleanup();
      resolve(result);
    };
    const fail = (error: Error) => {
      if (settled) return;
      settled = true;
      cleanup();
      reject(error);
    };
    const abort = () => xhr.abort();

    xhr.open("POST", url);
    xhr.upload.addEventListener("progress", (event) => {
      if (!event.lengthComputable || event.total <= 0) return;
      // 0–20% là xin ticket; 20–85% là bytes thật; 85–100% là backend xác
      // nhận object và probe media.
      const byteProgress = Math.round((event.loaded / event.total) * 65);
      options.onProgress?.(Math.min(84, 20 + byteProgress));
    });
    xhr.addEventListener("load", () =>
      finish({ ok: xhr.status >= 200 && xhr.status < 300, status: xhr.status }),
    );
    xhr.addEventListener("error", () => fail(new TypeError("storage upload failed")));
    xhr.addEventListener("abort", () =>
      fail(new DOMException("Upload aborted", "AbortError")),
    );

    if (options.signal?.aborted) {
      fail(new DOMException("Upload aborted", "AbortError"));
      return;
    }
    options.signal?.addEventListener("abort", abort, { once: true });
    xhr.send(form);
  });
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
            ? t("Havi chưa nhận được định dạng {noun} này ({value})", { noun: noun, value: file.type || "không rõ" })
            : t("Chưa tải được {noun} lên, thử lại giúp bạn nhé.", { noun: noun }),
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

    const uploaded = await uploadForm(ticket.data.upload_url, form, options);
    if (!uploaded.ok) {
      return {
        ok: false,
        message:
          uploaded.status === 400
            ? t("{value} quá nặng hoặc sai định dạng — chọn {noun} khác giúp bạn nhé.", { value: noun === "clip" ? "Clip" : "Ảnh", noun: noun })
            : t("Tải {noun} lên chưa xong, thử lại giúp bạn nhé.", { noun: noun }),
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
        message: t("{value} tải lên chưa hợp lệ, thử {noun} khác nhé.", { value: noun === "clip" ? "Clip" : "Ảnh", noun: noun }),
      };
    }
    options.onProgress?.(100);

    return { ok: true, data: completed.data };
  } catch (error) {
    if (isAbortError(error)) {
      return { ok: false, message: t("Đã huỷ tải {noun}.", { noun: noun }) };
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
  targetChannels?: Channel[],
): Promise<Result<ContentJob>> {
  try {
    const { data, error, response } = await apiClient.POST("/content/jobs", {
      body: {
        raw_inputs: rawInputs,
        target_channels: targetChannels,
      } as components["schemas"]["ContentJobCreate"] & {
        target_channels?: Channel[];
      },
      headers: { "Idempotency-Key": encodeURIComponent(idempotencyKey) },
    });
    if (error || !data) {
      const detailObj = (error as { detail?: unknown } | undefined)?.detail;
      if (response?.status === 401) {
        return {
          ok: false,
          message: detailToMessage(detailObj, "Phiên đăng nhập đã hết hạn. Bạn đăng nhập lại hoặc tải lại trang nhé."),
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
          message: detailToMessage(detailObj, "Bạn thao tác hơi nhanh — đợi một chút rồi thử lại nhé."),
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
    return {
      ok: false,
      // Không đẩy `Error.message` thô ra UI: message của fetch/client có thể
      // chứa URL nội bộ và chi tiết kỹ thuật, nhưng vẫn không giúp người dùng
      // quyết định hành động nào khác ngoài thử lại.
      message: NETWORK_ERROR_MESSAGE,
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

/** Bản nháp chờ duyệt hoặc đã lưu — màn này mở ra là thấy ngay, không cần vừa tạo job. */
export async function listPendingItems(): Promise<Result<ContentItem[]>> {
  try {
    const { data, error } = await apiClient.GET("/content", {});
    if (error || !data) return { ok: false, message: GENERIC_ERROR };
    const unapproved = (data.items || []).filter((i) =>
      ["pending_approval", "draft"].includes(i.status)
    );
    return { ok: true, data: unapproved };
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
            ? "Bài này vừa đổi trạng thái ở nơi khác — tải lại giúp bạn nhé."
            : GENERIC_ERROR,
      };
    }
    return { ok: true, data };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

export async function rejectItem(
  itemId: string,
  reason?: string,
): Promise<Result<ContentItem>> {
  try {
    const { data, error, response } = await apiClient.POST(
      "/content/{content_id}/reject",
      {
        params: { path: { content_id: itemId } },
        body: reason ? { reason } : undefined,
      },
    );
    if (error || !data) {
      return {
        ok: false,
        message:
          response?.status === 409
            ? "Bài này vừa đổi trạng thái ở nơi khác — tải lại giúp bạn nhé."
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
            : "Chưa lưu được, thử lại giúp bạn nhé.",
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

export async function dismissItem(itemId: string): Promise<Result<ContentItem>> {
  try {
    const { data, error, response } = await apiClient.POST(
      "/content/{content_id}/dismiss",
      { params: { path: { content_id: itemId } } },
    );
    if (error || !data) {
      return {
        ok: false,
        message:
          response?.status === 409
            ? "Bài này vừa đổi trạng thái ở nơi khác — tải lại giúp bạn nhé."
            : GENERIC_ERROR,
      };
    }
    return { ok: true, data };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

export async function dismissAllItems(itemIds: string[]): Promise<Result<string[]>> {
  try {
    const { data, error } = await apiClient.POST("/content/dismiss-all", {
      body: { content_item_ids: itemIds },
    });
    if (error || !data) return { ok: false, message: GENERIC_ERROR };
    return { ok: true, data: data.dismissed ?? [] };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

export async function uploadRenderedVideoBlob(
  itemId: string,
  blob: Blob,
): Promise<Result<{ media_url: string }>> {
  const contentType = blob.type || "video/webm";
  const file = new File([blob], `havi-render-${itemId}.${contentType.includes("mp4") ? "mp4" : "webm"}`, {
    type: contentType,
  });
  const uploaded = await uploadMedia(file);
  if (!uploaded.ok) return { ok: false, message: uploaded.message };
  const updated = await updateItemMedia(itemId, uploaded.data.url);
  if (!updated.ok) return { ok: false, message: updated.message };
  return { ok: true, data: { media_url: uploaded.data.url } };
}

export async function updateItemMedia(
  itemId: string,
  mediaUrl: string | null,
): Promise<Result<ContentItem>> {
  try {
    const { data, error } = await apiClient.PATCH("/content/{content_id}", {
      params: { path: { content_id: itemId } },
      body: { media_url: mediaUrl === null ? "__NONE__" : mediaUrl },
    });
    if (error || !data) return { ok: false, message: "Chưa cập nhật được ảnh, thử lại giúp bạn nhé." };
    return { ok: true, data };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

export type BulkApproveOutcome = {
  approved: string[];
  rejected: { content_item_id: string; reason: string }[];
};

/** "Duyệt & đăng hết". publishNow=true: phát lệnh xuất bản ngay lập tức. */
/**
 * Duyệt cả loạt. `publishNow=false` thì backend **rải lịch ra nhiều ngày**.
 *
 * Thứ tự `itemIds` là thứ tự lên bài — bài đầu danh sách đăng trước. Đừng sort
 * lại trước khi gọi: đó là cách chủ tiệm xếp câu chuyện của tuần.
 */
export async function approveAll(
  itemIds: string[],
  publishNow = true,
  postsPerDay = 1,
): Promise<Result<BulkApproveOutcome>> {
  try {
    const { data, error, response } = await apiClient.POST("/content/approve-all", {
      body: {
        content_item_ids: itemIds,
        publish_now: publishNow,
        posts_per_day: postsPerDay,
      },
    });
    if (error || !data) {
      // 403 = vai không được duyệt. Nuốt thành lỗi chung là người dùng bấm lại
      // mãi mà không hiểu vì sao — thông báo từ backend đã nói rõ cần vai nào.
      if (response?.status === 403) {
        return { ok: false, message: detailToMessage(error, GENERIC_ERROR) };
      }
      return { ok: false, message: GENERIC_ERROR };
    }
    return {
      ok: true,
      data: { approved: data.approved ?? [], rejected: data.rejected ?? [] },
    };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

export type ChannelOption = components["schemas"]["ChannelOption"];

/**
 * Kênh chọn được khi soạn bài, kèm loại nội dung mỗi kênh nhận.
 *
 * Luật "kênh nào nhận gì" nằm ở backend (`domain/policies/channel_capabilities.py`)
 * chứ không hardcode ở đây: đó là luật của nền tảng — TikTok không nhận bài chữ vì
 * TikTok là thế — và backend vẫn phải cưỡng chế nó cho client cũ.
 */
export async function listChannelOptions(): Promise<Result<ChannelOption[]>> {
  try {
    const { data, error } = await apiClient.GET("/content/channels");
    if (error || !data) {
      return { ok: false, message: detailToMessage(error, "Chưa tải được danh sách kênh") };
    }
    return { ok: true, data };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

export type ContentPreview = components["schemas"]["ContentPreview"];
export type RenderWarning = components["schemas"]["RenderWarning"];

/**
 * Bài người dùng **tự viết** — không gọi LLM, không tốn quota.
 *
 * Khác `createJob`: đường đó là nút "Để Havi viết bài" và luôn chạy model. Người
 * đã có bài hoàn chỉnh mà buộc đi đường đó thì phải nhờ Havi viết một bản không
 * ai cần rồi ghi đè lên.
 *
 * Không cần `Idempotency-Key`: bấm hai lần tạo hai bản nháp trùng nhau — thấy
 * ngay trong hàng chờ và xoá được, khác với hai lần tiền LLM đã tiêu.
 */
export async function createOwnItem(
  text: string,
  channel: Channel,
  mediaId?: string,
): Promise<Result<ContentItem>> {
  try {
    const { data, error, response } = await apiClient.POST("/content/items", {
      body: { text, channel, kind: "post", media_id: mediaId ?? null },
    });
    if (error || !data) {
      const detailObj = (error as { detail?: unknown } | undefined)?.detail;
      if (response?.status === 404) {
        return {
          ok: false,
          message: detailToMessage(detailObj, t("Không tìm thấy ảnh bạn chọn — thử nạp lại nhé.")),
        };
      }
      if (response?.status === 422) {
        return { ok: false, message: detailToMessage(detailObj, t("Bài chưa hợp lệ.")) };
      }
      return { ok: false, message: detailToMessage(detailObj, GENERIC_ERROR) };
    }
    return { ok: true, data };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

/**
 * Bài sẽ trông thế nào trên Trang. Không ghi gì vào DB.
 *
 * Trả cả bài kèm `truncate_at` chứ không phải chuỗi đã cắt: giao diện cần phần
 * sau để vẽ nút "Xem thêm" mở ra được.
 */
export async function previewContent(
  text: string,
  channel: Channel,
  mediaId?: string,
): Promise<Result<ContentPreview>> {
  try {
    const { data, error, response } = await apiClient.POST("/content/preview", {
      body: { text, channel, kind: "post", media_id: mediaId ?? null },
    });
    if (error || !data) {
      const detailObj = (error as { detail?: unknown } | undefined)?.detail;
      if (response?.status === 404) {
        return {
          ok: false,
          message: detailToMessage(detailObj, t("Không tìm thấy ảnh bạn chọn.")),
        };
      }
      return { ok: false, message: detailToMessage(detailObj, GENERIC_ERROR) };
    }
    return { ok: true, data };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}
