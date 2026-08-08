import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { readTokens, writeTokens } from "@/lib/auth/token-store";
import { apiClient } from "./client";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

const TOKENS = {
  accessToken: "access-cu",
  refreshToken: "refresh-cu",
  activeWorkspaceId: "w1",
  needsOnboarding: false,
};

describe("apiClient", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("gắn Bearer token vào request", async () => {
    writeTokens(TOKENS);
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(jsonResponse({ id: "u1" }));

    await apiClient.GET("/auth/me");

    const request = fetchSpy.mock.calls[0][0] as Request;
    expect(request.headers.get("Authorization")).toBe("Bearer access-cu");
  });

  it("gặp 401 thì refresh rồi thử lại đúng một lần", async () => {
    writeTokens(TOKENS);
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(jsonResponse({ detail: "hết hạn" }, 401))
      .mockResolvedValueOnce(
        jsonResponse({
          access_token: "access-moi",
          refresh_token: "refresh-moi",
          active_workspace_id: "w1",
          needs_onboarding: false,
        }),
      )
      .mockResolvedValueOnce(jsonResponse({ id: "u1" }));

    const { data } = await apiClient.GET("/auth/me");

    expect(data).toEqual({ id: "u1" });
    expect(fetchSpy).toHaveBeenCalledTimes(3);
    // Token mới phải được lưu lại, không thì request sau lại 401.
    expect(readTokens()?.accessToken).toBe("access-moi");
    const retry = fetchSpy.mock.calls[2][0] as Request;
    expect(retry.headers.get("Authorization")).toBe("Bearer access-moi");
  });

  it("refresh thất bại thì xoá token, không lặp vô hạn", async () => {
    writeTokens(TOKENS);
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(jsonResponse({ detail: "hết hạn" }, 401))
      .mockResolvedValueOnce(jsonResponse({ detail: "revoked" }, 401));

    const { response } = await apiClient.GET("/auth/me");

    expect(response.status).toBe(401);
    expect(fetchSpy).toHaveBeenCalledTimes(2);
    expect(readTokens()).toBeNull();
  });

  it("nhiều request cùng 401 chỉ refresh một lần", async () => {
    // Refresh token xoay vòng: gọi /auth/refresh hai lần với cùng token cũ thì
    // lần hai bị backend từ chối và revoke cả session.
    writeTokens(TOKENS);
    let refreshCalls = 0;
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      // refresh gọi `fetch(url, init)` với url dạng chuỗi, còn openapi-fetch
      // gửi một Request — mock phải nhận được cả hai.
      const url = typeof input === "string" ? input : (input as Request).url;
      if (url.includes("/auth/refresh")) {
        refreshCalls += 1;
        return jsonResponse({
          access_token: "access-moi",
          refresh_token: "refresh-moi",
        });
      }
      const auth = (input as Request).headers.get("Authorization");
      return auth === "Bearer access-moi"
        ? jsonResponse({ ok: true })
        : jsonResponse({ detail: "hết hạn" }, 401);
    });

    await Promise.all([
      apiClient.GET("/auth/me"),
      apiClient.GET("/auth/me"),
      apiClient.GET("/auth/me"),
    ]);

    expect(refreshCalls).toBe(1);
  });

  it("POST retry sau refresh vẫn giữ nguyên body", async () => {
    // `fetch` đọc body của Request, nên phải clone TRƯỚC khi gửi lần đầu.
    writeTokens(TOKENS);
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(jsonResponse({ detail: "hết hạn" }, 401))
      .mockResolvedValueOnce(
        jsonResponse({ access_token: "access-moi", refresh_token: "r" }),
      )
      .mockResolvedValueOnce(jsonResponse({ id: "j1" }, 202));

    await apiClient.POST("/content/jobs", {
      body: { raw_inputs: [{ kind: "text", text: "ưu đãi cuối tuần" }] },
    });

    const retry = fetchSpy.mock.calls[2][0] as Request;
    expect(await retry.json()).toEqual({
      raw_inputs: [{ kind: "text", text: "ưu đãi cuối tuần" }],
    });
  });

  it("chưa đăng nhập thì không gắn header và không refresh", async () => {
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(jsonResponse({ detail: "cần đăng nhập" }, 401));

    await apiClient.GET("/auth/me");

    expect(fetchSpy).toHaveBeenCalledTimes(1);
    const request = fetchSpy.mock.calls[0][0] as Request;
    expect(request.headers.get("Authorization")).toBeNull();
  });
});
