import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { SessionProvider } from "@/lib/auth/session";
import { readTokens } from "@/lib/auth/token-store";
import { LoginScreen } from "./login-screen";

const replace = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, push: vi.fn() }),
}));

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

import { LanguageProvider } from "@/lib/i18n/language-context";

function renderLogin() {
  return render(
    <SessionProvider>
      <LanguageProvider>
        <LoginScreen />
      </LanguageProvider>
    </SessionProvider>,
  );
}


async function fillAndSubmit(email: string, password: string) {
  const user = userEvent.setup();
  await user.type(screen.getByLabelText("Email"), email);
  await user.type(screen.getByLabelText("Mật khẩu"), password);
  await user.click(screen.getByRole("button", { name: /đăng nhập/i }));
}

describe("LoginScreen", () => {
  beforeEach(() => {
    window.localStorage.clear();
    replace.mockClear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("đăng nhập thành công thì lưu token và vào app", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse({
        access_token: "a",
        refresh_token: "r",
        active_workspace_id: "w1",
        needs_onboarding: false,
      }),
    );

    renderLogin();
    await fillAndSubmit("huong@spaannhien.vn", "matkhau123");

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/app"));
    expect(readTokens()?.accessToken).toBe("a");
  });

  it("tài khoản chưa onboarding thì đi onboarding, không vào app rỗng", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse({
        access_token: "a",
        refresh_token: "r",
        active_workspace_id: null,
        needs_onboarding: true,
      }),
    );

    renderLogin();
    await fillAndSubmit("huong@spaannhien.vn", "matkhau123");

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/onboarding"));
  });

  it("sai mật khẩu thì hiện lỗi và không lưu token", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse({ detail: "Email hoặc mật khẩu không đúng" }, 401),
    );

    renderLogin();
    await fillAndSubmit("huong@spaannhien.vn", "sai-mat-khau");

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Email hoặc mật khẩu không đúng",
    );
    expect(readTokens()).toBeNull();
    expect(replace).not.toHaveBeenCalled();
  });

  it("mất mạng thì báo bằng tiếng Việt, không hiện lỗi kỹ thuật", async () => {
    // Cohort pilot dùng 4G chập chờn — đây là trạng thái thường gặp.
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("fetch fail"));

    renderLogin();
    await fillAndSubmit("huong@spaannhien.vn", "matkhau123");

    expect(await screen.findByRole("alert")).toHaveTextContent(
      /không kết nối được/i,
    );
  });

  it("email sai định dạng thì chặn tại chỗ, không gọi API", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    renderLogin();
    await fillAndSubmit("khong-phai-email", "matkhau123");

    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(fetchSpy).not.toHaveBeenCalled();
  });
});
