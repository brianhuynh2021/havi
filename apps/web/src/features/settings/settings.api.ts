import { NETWORK_ERROR_MESSAGE } from "@/features/auth/auth.api";
import { apiClient } from "@/lib/api-client/client";
import { readTokens } from "@/lib/auth/token-store";
import type { components } from "@/lib/api-client/schema";

export type BrandProfile = components["schemas"]["BrandProfile"];
export type Industry = components["schemas"]["Industry"];
export type Workspace = components["schemas"]["Workspace"];

export type SettingsData = {
  workspace: Workspace;
  profile: BrandProfile;
};

export type SaveSettingsInput = {
  workspaceId: string;
  name: string;
  industry: Industry;
  tone: string;
  bannedClaims: string[];
};

export type Result<T> = { ok: true; data: T } | { ok: false; message: string };

const SAVE_ERROR = "Chưa lưu được cài đặt, thử lại giúp bạn nhé.";

export async function loadSettings(): Promise<Result<SettingsData>> {
  const workspaceId = readTokens()?.activeWorkspaceId;
  if (!workspaceId) {
    return {
      ok: false,
      message: "Tài khoản chưa chọn tiệm — hoàn thành onboarding trước nhé.",
    };
  }

  try {
    const [workspace, profile] = await Promise.all([
      apiClient.GET("/workspaces/{workspace_id}", {
        params: { path: { workspace_id: workspaceId } },
      }),
      apiClient.GET("/brand-profile"),
    ]);

    // Nói rõ **phần nào** hỏng. Gộp cả hai vào một câu thì người vận hành không
    // biết nên nối lại kênh, đăng nhập lại, hay gọi hỗ trợ.
    if (workspace.error || !workspace.data) {
      return { ok: false, message: "Chưa đọc được thông tin thương hiệu — thử lại giúp bạn nhé." };
    }
    if (profile.error || !profile.data) {
      return { ok: false, message: "Chưa đọc được giọng văn và bộ quy tắc — thử lại giúp bạn nhé." };
    }
    return { ok: true, data: { workspace: workspace.data, profile: profile.data } };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

export async function saveSettings(
  input: SaveSettingsInput,
): Promise<Result<SettingsData>> {
  try {
    const [workspace, profile] = await Promise.all([
      apiClient.PATCH("/workspaces/{workspace_id}", {
        params: { path: { workspace_id: input.workspaceId } },
        body: { name: input.name, industry: input.industry },
      }),
      apiClient.PUT("/brand-profile", {
        body: {
          tone: input.tone,
          banned_claims: input.bannedClaims,
        },
      }),
    ]);

    if (workspace.error || !workspace.data || profile.error || !profile.data) {
      return { ok: false, message: SAVE_ERROR };
    }
    return { ok: true, data: { workspace: workspace.data, profile: profile.data } };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

export function parseBannedClaims(value: string): string[] {
  return value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
}

export function formatBannedClaims(value: string[] | undefined): string {
  return (value ?? []).join("\n");
}

export async function deleteWorkspace(workspaceId: string): Promise<Result<void>> {
  try {
    const response = await apiClient.DELETE("/workspaces/{workspace_id}", {
      params: { path: { workspace_id: workspaceId } },
    });
    const errorObj = (response as { error?: unknown }).error;
    if (errorObj) {
      const detail = errorObj && typeof errorObj === "object" && "detail" in errorObj
        ? String((errorObj as { detail?: unknown }).detail)
        : null;
      return {
        ok: false,
        message: detail || "Không thể xoá workspace, thử lại giúp bạn nhé.",
      };
    }
    return { ok: true, data: undefined };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

export async function deleteAccount(): Promise<Result<void>> {
  try {
    const response = await apiClient.DELETE("/auth/me");
    const errorObj = (response as { error?: unknown }).error;
    if (errorObj) {
      const detail = errorObj && typeof errorObj === "object" && "detail" in errorObj
        ? String((errorObj as { detail?: unknown }).detail)
        : null;
      return {
        ok: false,
        message: detail || "Không thể xoá tài khoản, thử lại giúp bạn nhé.",
      };
    }
    return { ok: true, data: undefined };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

