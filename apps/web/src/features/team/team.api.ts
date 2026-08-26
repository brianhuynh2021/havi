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
 * Thành viên, vai trò và quyền hạn của workspace.
 *
 * Bốn vai trò, và chúng khác nhau ở đúng một điều đáng kể: **ai được bấm
 * duyệt**. Quy trình soạn → duyệt → đăng chỉ có nghĩa khi hai vai đó tách rời
 * được — nếu ai cũng duyệt được thì bước duyệt chỉ là một cú bấm thêm.
 */

import { apiClient } from "@/lib/api-client/client";
import { NETWORK_ERROR_MESSAGE, detailToMessage } from "@/features/auth/auth.api";
import { readTokens } from "@/lib/auth/token-store";
import type { components } from "@/lib/api-client/schema";

export type WorkspaceMember = components["schemas"]["WorkspaceMember"];
export type WorkspaceRole = components["schemas"]["WorkspaceRole"];

export type Result<T> = { ok: true; data: T } | { ok: false; message: string };

const NO_WORKSPACE = "Chưa chọn workspace. Tải lại trang giúp bạn nhé.";

/** Mô tả vai trò bằng việc người đó *làm được gì*, không bằng tên chức danh. */
export const ROLE_LABELS: Record<string, { name: string; can: string }> = {
  owner: { name: "Chủ workspace", can: "Toàn quyền, kể cả mời và gỡ thành viên" },
  marketer: { name: "Người soạn", can: "Soạn nội dung và gửi đi chờ duyệt" },
  reviewer: { name: "Người duyệt", can: "Duyệt nội dung để Havi đăng lên kênh" },
  sales: { name: "Trực hội thoại", can: "Trả lời tin nhắn và bình luận của khách" },
};

function workspaceId(): string | null {
  return readTokens()?.activeWorkspaceId ?? null;
}

export async function listMembers(): Promise<Result<WorkspaceMember[]>> {
  const id = workspaceId();
  if (!id) return { ok: false, message: NO_WORKSPACE };
  try {
    const { data, error } = await apiClient.GET("/workspaces/{workspace_id}/members", {
      params: { path: { workspace_id: id } },
    });
    if (error || !data) {
      return { ok: false, message: detailToMessage(error, "Không tải được danh sách thành viên") };
    }
    return { ok: true, data };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

export async function inviteMember(
  email: string,
  role: WorkspaceRole,
): Promise<Result<WorkspaceMember>> {
  const id = workspaceId();
  if (!id) return { ok: false, message: NO_WORKSPACE };
  try {
    const { data, error } = await apiClient.POST("/workspaces/{workspace_id}/members", {
      params: { path: { workspace_id: id } },
      body: { email, role },
    });
    if (error || !data) {
      return { ok: false, message: detailToMessage(error, "Không mời được thành viên") };
    }
    return { ok: true, data };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

export async function removeMember(userId: string): Promise<Result<null>> {
  const id = workspaceId();
  if (!id) return { ok: false, message: NO_WORKSPACE };
  try {
    const { error } = await apiClient.DELETE(
      "/workspaces/{workspace_id}/members/{user_id}",
      { params: { path: { workspace_id: id, user_id: userId } } },
    );
    if (error) {
      return { ok: false, message: detailToMessage(error, "Không gỡ được thành viên") };
    }
    return { ok: true, data: null };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

export async function updateMemberRole(userId: string, role: WorkspaceRole): Promise<Result<WorkspaceMember>> {
  const id = workspaceId();
  if (!id) return { ok: false, message: NO_WORKSPACE };
  try {
    const { data, error } = await apiClient.PUT(
      "/workspaces/{workspace_id}/members/{user_id}/role",
      {
        params: { path: { workspace_id: id, user_id: userId } },
        body: { role },
      },
    );
    if (error || !data) {
      return { ok: false, message: detailToMessage(error, "Không đổi được vai trò") };
    }
    return { ok: true, data };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

export async function resendInvite(userId: string): Promise<Result<WorkspaceMember>> {
  const id = workspaceId();
  if (!id) return { ok: false, message: NO_WORKSPACE };
  try {
    const { data, error } = await apiClient.POST(
      "/workspaces/{workspace_id}/members/{user_id}/resend",
      { params: { path: { workspace_id: id, user_id: userId } } },
    );
    if (error || !data) {
      return { ok: false, message: detailToMessage(error, "Không gửi lại được lời mời") };
    }
    return { ok: true, data };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}
