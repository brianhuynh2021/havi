import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { SessionProvider } from "@/lib/auth/session";
import { readTokens, writeTokens } from "@/lib/auth/token-store";
import { OnboardingScreen } from "./onboarding-screen";

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

/** Onboarding chỉ mở cho người đã đăng nhập — token này là token sau đăng ký,
 * còn `needs_onboarding: true`. */
function signedUpTokens() {
  writeTokens({
    accessToken: "cu",
    refreshToken: "cu-refresh",
    activeWorkspaceId: null,
    needsOnboarding: true,
  });
}

/** Route theo URL: `/auth/me` điền tên sẵn, `POST /workspaces` tạo tiệm,
 * `/activate` ký lại token, `/connections` là danh sách kênh ở bước 2. */
function mockApi(
  overrides: { activate?: Response; connections?: unknown } = {},
) {
  return vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(async (input: RequestInfo | URL) => {
      const url = input instanceof Request ? input.url : String(input);
      if (url.includes("/auth/me")) {
        return jsonResponse({
          id: "u1",
          name: "Spa An Nhiên",
          email: "huong@spaannhien.vn",
        });
      }
      if (url.includes("/activate")) {
        return (
          overrides.activate ??
          jsonResponse({
            access_token: "moi",
            refresh_token: "moi-refresh",
            active_workspace_id: "w1",
            needs_onboarding: false,
          })
        );
      }
      // Phải đứng TRƯỚC nhánh mặc định: `/connections` mà rơi vào nhánh tạo
      // workspace sẽ trả một object thay vì mảng, và bước 2 đổ.
      if (url.includes("/connections")) {
        return jsonResponse(overrides.connections ?? []);
      }
      return jsonResponse({ id: "w1", name: "Spa An Nhiên" }, 201);
    });
}

function renderOnboarding() {
  return render(
    <SessionProvider>
      <OnboardingScreen />
    </SessionProvider>,
  );
}

async function chonNganhVaTiepTuc() {
  const user = userEvent.setup();
  await user.click(screen.getByRole("button", { name: /spa/i }));
  await user.click(screen.getByRole("button", { name: /^tiếp tục$/i }));
}

describe("OnboardingScreen", () => {
  beforeEach(() => {
    window.localStorage.clear();
    signedUpTokens();
    replace.mockClear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("điền sẵn tên tiệm từ tài khoản để chủ tiệm không gõ lại", async () => {
    mockApi();
    renderOnboarding();

    await waitFor(() =>
      expect(screen.getByLabelText("Tên tiệm")).toHaveValue("Spa An Nhiên"),
    );
  });

  it("chọn ngành xong thì tạo tiệm thật và token hết needs_onboarding", async () => {
    const fetchSpy = mockApi();
    renderOnboarding();
    await waitFor(() =>
      expect(screen.getByLabelText("Tên tiệm")).toHaveValue("Spa An Nhiên"),
    );

    await chonNganhVaTiepTuc();

    await waitFor(() => expect(readTokens()?.accessToken).toBe("moi"));
    // Điểm chính của cả bước này: thiếu nó thì route guard đá ngược về
    // /onboarding và user không bao giờ vào được app.
    expect(readTokens()?.needsOnboarding).toBe(false);
    expect(readTokens()?.activeWorkspaceId).toBe("w1");

    const calledUrls = fetchSpy.mock.calls.map(([input]) =>
      input instanceof Request ? input.url : String(input),
    );
    expect(calledUrls.some((u) => u.endsWith("/workspaces"))).toBe(true);
    expect(calledUrls.some((u) => u.includes("/activate"))).toBe(true);

    expect(
      screen.getByRole("heading", { name: /nối kênh facebook/i }),
    ).toBeInTheDocument();
  });

  it("tạo tiệm lỗi thì báo lỗi, giữ nguyên bước 1 và không đổi token", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(
      async (input: RequestInfo | URL) => {
        const url = input instanceof Request ? input.url : String(input);
        if (url.includes("/auth/me")) {
          return jsonResponse({ id: "u1", name: "", email: "a@b.vn" });
        }
        return jsonResponse({ detail: "loi" }, 500);
      },
    );

    renderOnboarding();
    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Tên tiệm"), "Spa An Nhiên");
    await chonNganhVaTiepTuc();

    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(readTokens()?.accessToken).toBe("cu");
    expect(readTokens()?.needsOnboarding).toBe(true);
  });

  it("chưa nhập tên tiệm thì chặn tại chỗ, không tạo workspace", async () => {
    // `/auth/me` trả tên rỗng — tài khoản đăng ký bằng tên trống.
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation(async () =>
        jsonResponse({ id: "u1", name: "", email: "a@b.vn" }),
      );

    renderOnboarding();
    await chonNganhVaTiepTuc();

    expect(await screen.findByRole("alert")).toBeInTheDocument();
    const calledUrls = fetchSpy.mock.calls.map(([input]) =>
      input instanceof Request ? input.url : String(input),
    );
    expect(calledUrls.some((u) => u.endsWith("/workspaces"))).toBe(false);
  });

  it("bước cuối vào app bằng replace, không để quay lại onboarding", async () => {
    mockApi();
    renderOnboarding();
    await waitFor(() =>
      expect(screen.getByLabelText("Tên tiệm")).toHaveValue("Spa An Nhiên"),
    );
    await chonNganhVaTiepTuc();

    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: /để sau/i }));
    await user.click(screen.getByRole("button", { name: /bắt đầu/i }));
    await user.click(screen.getByRole("button", { name: /vào app/i }));

    expect(replace).toHaveBeenCalledWith("/");
  });
});
