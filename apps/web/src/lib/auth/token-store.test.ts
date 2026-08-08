import { describe, expect, it } from "vitest";
import { clearTokens, readTokens, writeTokens } from "./token-store";

const TOKENS = {
  accessToken: "a",
  refreshToken: "r",
  activeWorkspaceId: "w1",
  needsOnboarding: false,
};

describe("token store", () => {
  it("ghi rồi đọc lại đúng", () => {
    writeTokens(TOKENS);
    expect(readTokens()).toEqual(TOKENS);
  });

  it("chưa đăng nhập thì trả null", () => {
    expect(readTokens()).toBeNull();
  });

  it("xoá token thì coi như đăng xuất", () => {
    writeTokens(TOKENS);
    clearTokens();
    expect(readTokens()).toBeNull();
  });

  it("dữ liệu hỏng coi như chưa đăng nhập, không ném", () => {
    window.localStorage.setItem("havi.tokens", "{không phải json");
    expect(readTokens()).toBeNull();
  });

  it("thiếu refresh token coi như chưa đăng nhập", () => {
    // Không có refresh token thì access token hết hạn là kẹt cứng — thà bắt
    // đăng nhập lại còn hơn để app chạy rồi 401 ở chỗ khó truy.
    window.localStorage.setItem(
      "havi.tokens",
      JSON.stringify({ accessToken: "a" }),
    );
    expect(readTokens()).toBeNull();
  });
});
