import createClient from "openapi-fetch";
import {
  clearTokens,
  readTokens,
  writeTokens,
  type StoredTokens,
} from "@/lib/auth/token-store";
import type { paths } from "./schema";

// Frontend không giữ database credential, OAuth secret hay token nền tảng
// (ROADMAP §1 nguyên tắc #6) — chỉ JWT của chính user.
// Local dev chạy Next ở :3000 và API ở :8000. Khi production đi qua Nginx,
// dùng same-origin để không phải hard-code localhost vào bundle trình duyệt.
/** Gốc của API, đã tính cả trường hợp production đi qua Nginx same-origin.
 *  Export ra để mọi module gọi API dùng chung một giá trị — hard-code
 *  `http://localhost:8000` ở nơi khác sẽ chạy ngon ở local rồi chết ở production. */
export const baseUrl =
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  (typeof window !== "undefined" && window.location.port !== "3000"
    ? window.location.origin
    : "http://localhost:8000");

/** Refresh token xoay vòng: dùng lại token cũ bị backend từ chối. Nên khi nhiều
 * request cùng nhận 401 một lúc (dashboard gọi 3 API song song), chỉ được có
 * đúng một lượt refresh — nếu không, lượt thứ hai gửi token đã bị xoay và
 * backend revoke cả session, đá user ra màn đăng nhập giữa chừng. */
let refreshInFlight: Promise<StoredTokens | null> | null = null;

async function refreshTokens(): Promise<StoredTokens | null> {
  const current = readTokens();

  const response = await fetch(`${baseUrl}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ refresh_token: current?.refreshToken }),
  });

  if (!response.ok) {
    clearTokens();
    return null;
  }

  const body = await response.json();
  const next: StoredTokens = {
    accessToken: body.access_token,
    refreshToken: body.refresh_token,
    activeWorkspaceId: body.active_workspace_id ?? null,
    needsOnboarding: body.needs_onboarding ?? false,
  };
  writeTokens(next);
  return next;
}

function refreshOnce(): Promise<StoredTokens | null> {
  refreshInFlight ??= refreshTokens().finally(() => {
    refreshInFlight = null;
  });
  return refreshInFlight;
}

/**
 * `fetch` có gắn Bearer token và tự refresh đúng một lần khi gặp 401.
 *
 * Chỉ thử lại một lần: 401 sau khi vừa refresh nghĩa là session đã chết thật
 * (bị revoke, đổi mật khẩu), retry tiếp chỉ tạo vòng lặp vô hạn.
 */
async function authedFetch(input: Request): Promise<Response> {
  const tokens = readTokens();
  if (tokens) {
    input.headers.set("Authorization", `Bearer ${tokens.accessToken}`);
  }

  // Clone TRƯỚC khi gửi: `fetch` đọc body của request, và `clone()` trên một
  // Request đã `bodyUsed` sẽ ném. Không clone sẵn thì mọi POST retry đều hỏng.
  const retry = input.clone();

  let response: Response;
  try {
    response = await fetch(input, { credentials: "include" });
  } catch (err) {
    try {
      response = await fetch(retry, { credentials: "include" });
    } catch {
      throw err;
    }
  }

  if (response.status !== 401 || !tokens) return response;

  const refreshed = await refreshOnce();
  if (!refreshed) return response;

  retry.headers.set("Authorization", `Bearer ${refreshed.accessToken}`);
  return fetch(retry, { credentials: "include" });
}

export { authedFetch };
export const apiClient = createClient<paths>({ baseUrl, fetch: authedFetch });

/** Client không kèm token — cho /auth/login, /auth/sign-up, reset mật khẩu.
 * Tách riêng để một token hỏng trong localStorage không làm hỏng luôn đường
 * đăng nhập lại.
 *
 * Gọi `globalThis.fetch` tại thời điểm request chứ không nhận mặc định của
 * openapi-fetch: mặc định đó chốt `globalThis.fetch` ngay lúc tạo client, nên
 * test thay `fetch` sau khi import sẽ không chặn được — request thật bay ra
 * ngoài và test hoá ra đang gọi backend đang chạy. */
export const publicApiClient = createClient<paths>({
  baseUrl,
  fetch: (input) => globalThis.fetch(input, { credentials: "include" }),
});
