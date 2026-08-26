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

/** Onboarding còn hai bước, và bước 1 chỉ có một trường: tên thương hiệu. */
async function tiepTuc() {
  const user = userEvent.setup();
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
      expect(screen.getByLabelText("Tên thương hiệu")).toHaveValue("Spa An Nhiên"),
    );
  });

  it("nhập tên xong thì tạo workspace thật và token hết needs_onboarding", async () => {
    const fetchSpy = mockApi();
    renderOnboarding();
    await waitFor(() =>
      expect(screen.getByLabelText("Tên thương hiệu")).toHaveValue("Spa An Nhiên"),
    );

    await tiepTuc();

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
      screen.getByRole("heading", { name: /kết nối kênh của bạn/i }),
    ).toBeInTheDocument();
  });

  it("tạo workspace lỗi thì báo lỗi, giữ nguyên bước 1 và không đổi token", async () => {
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
    await user.type(screen.getByLabelText("Tên thương hiệu"), "Spa An Nhiên");
    await tiepTuc();

    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(readTokens()?.accessToken).toBe("cu");
    expect(readTokens()?.needsOnboarding).toBe(true);
  });

  it("chưa nhập tên thì nút Tiếp tục bị chặn, không gọi API nào", async () => {
    // Chặn trước thay vì cho bấm rồi báo lỗi: người dùng không phải đọc một câu
    // mắng để biết mình thiếu gì — trường trống ngay trên nút là đủ rõ.
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation(async () =>
        jsonResponse({ id: "u1", name: "", email: "a@b.vn" }),
      );

    renderOnboarding();

    await waitFor(() =>
      expect(screen.getByLabelText("Tên thương hiệu")).toHaveValue(""),
    );
    expect(screen.getByRole("button", { name: /^tiếp tục$/i })).toBeDisabled();

    const calledUrls = fetchSpy.mock.calls.map(([input]) =>
      input instanceof Request ? input.url : String(input),
    );
    expect(calledUrls.some((u) => u.endsWith("/workspaces"))).toBe(false);
  });

  it("bước cuối vào app bằng replace, không để quay lại onboarding", async () => {
    mockApi();
    renderOnboarding();
    await waitFor(() =>
      expect(screen.getByLabelText("Tên thương hiệu")).toHaveValue("Spa An Nhiên"),
    );
    await tiepTuc();

    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: /bỏ qua/i }));

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/app"), { timeout: 2000 });

  });

  it("KHÔNG còn bước chọn ngành", async () => {
    // Ngành từng là bước 1 của onboarding, nhưng nó chỉ được copy sang brand
    // profile rồi không ai đọc — và sản phẩm là một hàng đợi việc, thứ mà ngành
    // nghề không ảnh hưởng gì tới. Giọng thương hiệu đặt ở Cài đặt.
    mockApi();
    renderOnboarding();

    expect(screen.queryByRole("button", { name: /spa/i })).toBeNull();
    expect(screen.queryByText("★ Đề xuất pilot")).toBeNull();
    expect(screen.queryByText(/ngành/i)).toBeNull();
    // Bước 1 chỉ còn đúng một trường.
    expect(screen.getByLabelText("Tên thương hiệu")).toBeInTheDocument();
  });

  it("quay lại bước 1 sửa tên thì gọi PATCH cập nhật chứ không tạo workspace thứ hai (idempotent)", async () => {
    const fetchSpy = mockApi();
    renderOnboarding();
    await waitFor(() =>
      expect(screen.getByLabelText("Tên thương hiệu")).toHaveValue("Spa An Nhiên"),
    );

    const user = userEvent.setup();
    await tiepTuc();

    // Đang ở bước 2
    expect(
      await screen.findByRole("heading", { name: /kết nối kênh của bạn/i }),
    ).toBeInTheDocument();

    // Bấm nút Quay lại về bước 1
    const backBtn = screen.getByRole("button", { name: /quay lại/i });
    await user.click(backBtn);

    // Đã quay về bước 1
    expect(
      screen.getByRole("heading", { name: /thương hiệu bạn quản trị tên gì/i }),
    ).toBeInTheDocument();

    // Sửa tên tiệm
    const nameInput = screen.getByLabelText("Tên thương hiệu");
    await user.clear(nameInput);
    await user.type(nameInput, "Spa An Nhiên Premium");

    // Bấm Tiếp tục lần 2
    await user.click(screen.getByRole("button", { name: /^tiếp tục$/i }));

    // Kiểm tra API: Lần 2 phải gọi PATCH /workspaces/w1 chứ không POST /workspaces tạo mới
    const patchCalls = fetchSpy.mock.calls.filter(([input, init]) => {
      const url = input instanceof Request ? input.url : String(input);
      const method = input instanceof Request ? input.method : init?.method;
      return url.includes("/workspaces/w1") && method === "PATCH";
    });
    expect(patchCalls.length).toBe(1);
  });
});
