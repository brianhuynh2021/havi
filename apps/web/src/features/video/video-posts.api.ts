/**
 * Luồng video: tải clip lên → duyệt → Havi đăng lên Facebook Reels.
 *
 * Havi không dựng và không sửa video. Chủ tiệm tự quay và tự cắt bằng công cụ họ
 * đã quen; phần Havi lo là đăng đúng giờ, biết chắc bài đã lên, và không đăng
 * trùng. Module này chỉ gọi bốn endpoint tương ứng bốn bước đó.
 */

import { authedFetch, baseUrl } from "@/lib/api-client/client";
import { NETWORK_ERROR_MESSAGE, detailToMessage } from "@/features/auth/auth.api";
import { readTokens } from "@/lib/auth/token-store";

export type Result<T> = { ok: true; data: T } | { ok: false; message: string };

export type VideoPostStatus =
  | "ready_for_review"
  | "approved"
  | "publishing"
  | "verifying"
  | "published"
  | "failed"
  | "failed_permanent"
  | "pending_reconciliation"
  | "cancelled";

export type VideoChannel = "reels" | "tiktok" | "youtube";

export type VideoPost = {
  id: string;
  workspace_id: string;
  caption: string;
  channel: VideoChannel;
  status: VideoPostStatus;
  source_media_id: string | null;
  /** Giờ Havi sẽ gửi clip đi (ISO, UTC). `null` = gửi ngay. */
  scheduled_at: string | null;
  error_message: string | null;
  published_at: string | null;
  created_at: string;
};

/**
 * Lỗi "clip này chưa đăng được" mang theo **cả danh sách** lý do.
 *
 * Backend trả hết một lượt để chủ tiệm sửa một lần (quay dọc lại *và* cắt ngắn)
 * thay vì tải lên ba lần để phát hiện ba lỗi. Đừng rút gọn xuống câu đầu tiên.
 */
export type ClipRejection = { message: string; reasons: string[] };

function workspaceUrl(suffix = ""): string | null {
  const workspaceId = readTokens()?.activeWorkspaceId;
  if (!workspaceId) return null;
  return `${baseUrl}/workspaces/${workspaceId}/video/posts${suffix}`;
}

const NO_WORKSPACE = "Chưa chọn workspace. Tải lại trang giúp bạn nhé.";

/** Gom lý do từ chối thành một câu đọc được, giữ nguyên thứ tự backend trả. */
export function rejectionMessage(detail: unknown, fallback: string): string {
  if (detail && typeof detail === "object" && "reasons" in detail) {
    const reasons = (detail as ClipRejection).reasons;
    if (Array.isArray(reasons) && reasons.length) return reasons.join(". ");
  }
  return detailToMessage(detail, fallback);
}

export async function listVideoPosts(): Promise<Result<VideoPost[]>> {
  const url = workspaceUrl();
  if (!url) return { ok: false, message: NO_WORKSPACE };
  try {
    const res = await authedFetch(new Request(url));
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      return { ok: false, message: detailToMessage(body?.detail, "Không tải được danh sách video") };
    }
    const body = await res.json();
    return { ok: true, data: body.items ?? [] };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

/** Biến một clip đã upload xong thành bài chờ duyệt. */
export async function createVideoPost(params: {
  sourceMediaId: string;
  caption: string;
  channel?: VideoChannel;
}): Promise<Result<VideoPost>> {
  const url = workspaceUrl();
  if (!url) return { ok: false, message: NO_WORKSPACE };
  try {
    const res = await authedFetch(
      new Request(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          source_media_id: params.sourceMediaId,
          caption: params.caption,
          channel: params.channel ?? "reels",
        }),
      }),
    );
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      return { ok: false, message: rejectionMessage(body?.detail, "Chưa tạo được bài video") };
    }
    return { ok: true, data: await res.json() };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

export async function updateVideoCaption(
  postId: string,
  caption: string,
): Promise<Result<VideoPost>> {
  const url = workspaceUrl(`/${postId}`);
  if (!url) return { ok: false, message: NO_WORKSPACE };
  try {
    const res = await authedFetch(
      new Request(url, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ caption }),
      }),
    );
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      return { ok: false, message: rejectionMessage(body?.detail, "Không sửa được nội dung") };
    }
    return { ok: true, data: await res.json() };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

/**
 * Duyệt để Havi đăng. Trả thêm `queuedForPublish`.
 *
 * `false` không phải lỗi: bài đã ở `approved` và worker quét lại sẽ nhặt được.
 * Nhưng UI phải nói khác đi — "đang gửi" và "đã duyệt, sẽ gửi khi hàng đợi hoạt
 * động trở lại" là hai điều khác nhau với người đang đứng chờ.
 */
export async function approveVideoPost(
  postId: string,
  scheduledAt?: string | null,
): Promise<Result<{ post: VideoPost; queuedForPublish: boolean }>> {
  const url = workspaceUrl(`/${postId}/approve`);
  if (!url) return { ok: false, message: NO_WORKSPACE };
  try {
    const res = await authedFetch(
      new Request(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ scheduled_at: scheduledAt ?? null }),
      }),
    );
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      return { ok: false, message: rejectionMessage(body?.detail, "Chưa duyệt được video") };
    }
    const body = await res.json();
    return {
      ok: true,
      data: { post: body.post, queuedForPublish: Boolean(body.queued_for_publish) },
    };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

export async function cancelVideoPost(postId: string): Promise<Result<null>> {
  const url = workspaceUrl(`/${postId}/cancel`);
  if (!url) return { ok: false, message: NO_WORKSPACE };
  try {
    const res = await authedFetch(new Request(url, { method: "POST" }));
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      return { ok: false, message: detailToMessage(body?.detail, "Không huỷ được video") };
    }
    return { ok: true, data: null };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}
