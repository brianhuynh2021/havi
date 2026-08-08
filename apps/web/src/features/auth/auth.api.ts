import { publicApiClient } from "@/lib/api-client/client";
import type { StoredTokens } from "@/lib/auth/token-store";

/** Lỗi mạng và lỗi backend phải nói cùng một thứ tiếng với người dùng.
 *
 * Cohort pilot dùng 4G chập chờn (ROADMAP §4 Việt Nam-first), nên "mất mạng"
 * là trạng thái thường gặp chứ không phải ngoại lệ hiếm — và nó cần câu chữ
 * khác hẳn "sai mật khẩu", vì cách xử lý của chủ tiệm khác hẳn.
 */
export const NETWORK_ERROR_MESSAGE =
  "Không kết nối được với Havi. Kiểm tra mạng rồi thử lại giúp chị nhé.";

type TokenPairBody = {
  access_token: string;
  refresh_token: string;
  active_workspace_id?: string | null;
  needs_onboarding?: boolean;
};

export function toStoredTokens(body: TokenPairBody): StoredTokens {
  return {
    accessToken: body.access_token,
    refreshToken: body.refresh_token,
    activeWorkspaceId: body.active_workspace_id ?? null,
    needsOnboarding: body.needs_onboarding ?? false,
  };
}

export type AuthResult =
  | { ok: true; tokens: StoredTokens }
  | { ok: false; message: string };

/** `detail` của FastAPI khi 422 là mảng object, không phải chuỗi — render thẳng
 * ra UI sẽ hiện "[object Object]". */
function detailToMessage(detail: unknown, fallback: string): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const first = detail[0] as { msg?: string } | undefined;
    if (first?.msg) return first.msg;
  }
  return fallback;
}

export async function login(
  email: string,
  password: string,
): Promise<AuthResult> {
  try {
    const { data, error, response } = await publicApiClient.POST(
      "/auth/login/email",
      { body: { email, password } },
    );
    if (error || !data) {
      const message =
        response?.status === 401
          ? "Email hoặc mật khẩu không đúng"
          : detailToMessage(
              (error as { detail?: unknown } | undefined)?.detail,
              "Chưa đăng nhập được, thử lại giúp chị nhé.",
            );
      return { ok: false, message };
    }
    return { ok: true, tokens: toStoredTokens(data as TokenPairBody) };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

export async function signUp(
  name: string,
  email: string,
  password: string,
): Promise<AuthResult> {
  try {
    const { data, error, response } = await publicApiClient.POST(
      "/auth/sign-up",
      { body: { name, email, password } },
    );
    if (error || !data) {
      const message =
        response?.status === 409
          ? "Email này đã có tài khoản — đăng nhập thay vì đăng ký nhé."
          : detailToMessage(
              (error as { detail?: unknown } | undefined)?.detail,
              "Chưa tạo được tài khoản, thử lại giúp chị nhé.",
            );
      return { ok: false, message };
    }
    return { ok: true, tokens: toStoredTokens(data as TokenPairBody) };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}
