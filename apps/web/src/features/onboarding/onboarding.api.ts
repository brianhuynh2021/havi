import { apiClient } from "@/lib/api-client/client";
import { NETWORK_ERROR_MESSAGE, toStoredTokens } from "@/features/auth/auth.api";
import type { StoredTokens } from "@/lib/auth/token-store";
import type { IndustryOption } from "./onboarding.fixture";

/** Tên đã nhập lúc đăng ký, để điền sẵn ô "Tên tiệm".
 *
 * Chỉ là tiện nghi — hỏng thì trả chuỗi rỗng và user tự gõ, không chặn
 * onboarding và không hiện lỗi. */
export async function fetchDefaultShopName(): Promise<string> {
  try {
    const { data } = await apiClient.GET("/auth/me");
    return data?.name ?? "";
  } catch {
    return "";
  }
}

export type CreateWorkspaceResult =
  | { ok: true; tokens: StoredTokens }
  | { ok: false; message: string };

/**
 * Bước 1 onboarding: tạo tiệm rồi lấy token mới.
 *
 * Hai lượt gọi chứ không một: `POST /workspaces` tạo tiệm và set nó thành
 * active ở phía DB, nhưng JWT đang cầm trên tay được ký từ trước đó nên vẫn
 * mang `needs_onboarding: true` và không có `active_workspace_id`. Chỉ
 * `/workspaces/{id}/activate` mới ký lại token. Bỏ bước này thì user tạo tiệm
 * xong vẫn bị route guard đá ngược về /onboarding — vòng lặp không lối ra.
 */
export async function createWorkspace(
  name: string,
  industry: IndustryOption["value"],
): Promise<CreateWorkspaceResult> {
  try {
    const created = await apiClient.POST("/workspaces", {
      body: { name, industry },
    });
    if (created.error || !created.data) {
      return {
        ok: false,
        message: "Chưa tạo được tiệm, thử lại giúp chị nhé.",
      };
    }

    const activated = await apiClient.POST(
      "/workspaces/{workspace_id}/activate",
      { params: { path: { workspace_id: created.data.id } } },
    );
    if (activated.error || !activated.data) {
      // Tiệm đã tạo thật, chỉ token là cũ. Nói theo hướng "thử lại" thay vì
      // "tạo lại" để chủ tiệm không bấm tạo thêm tiệm thứ hai trùng tên.
      return {
        ok: false,
        message: "Đã tạo tiệm nhưng chưa vào được, thử lại giúp chị nhé.",
      };
    }

    return { ok: true, tokens: toStoredTokens(activated.data) };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}
