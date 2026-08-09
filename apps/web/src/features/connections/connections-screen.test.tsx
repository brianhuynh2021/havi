import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { writeTokens } from "@/lib/auth/token-store";
import { ConnectionsScreen } from "./connections-screen";
import { readCallbackOutcome } from "./connections.api";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function signedIn() {
  writeTokens({
    accessToken: "at",
    refreshToken: "rt",
    activeWorkspaceId: "w1",
    needsOnboarding: false,
  });
}

function connection(overrides: Record<string, unknown> = {}) {
  return {
    workspace_id: "w1",
    platform: "facebook",
    status: "connected",
    account_name: "Spa An Nhiên",
    expires_at: null,
    connected_by: "u1",
    ...overrides,
  };
}

/** Mock ở tầng transport (`fetch`) chứ không mock module app: giữ nguyên
 * `apiClient` thật nên lỗi ở tầng client (header, refresh 401) vẫn lộ ra. */
function mockConnections(body: unknown, status = 200) {
  return vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(async () => jsonResponse(body, status));
}

/** `window.location.assign` không chạy được trong jsdom — thay bằng spy để
 * kiểm "có điều hướng sang Facebook không" mà không rời trang test. */
function stubAssign() {
  const assign = vi.fn();
  Object.defineProperty(window, "location", {
    configurable: true,
    value: { ...window.location, assign, search: "", href: "http://localhost/cai-dat" },
  });
  return assign;
}

describe("readCallbackOutcome", () => {
  it("đọc kết quả nối kênh thành công", () => {
    expect(readCallbackOutcome("?ket_noi=ok")).toEqual({ kind: "ok" });
  });

  it("dịch từng mã lỗi sang câu tiếng Việt riêng", () => {
    const huy = readCallbackOutcome("?ket_noi=loi&ly_do=huy");
    const hetHan = readCallbackOutcome("?ket_noi=loi&ly_do=het_han");
    expect(huy).toMatchObject({ kind: "error" });
    expect(hetHan).toMatchObject({ kind: "error" });
    // Hai lý do khác nhau phải ra hai câu khác nhau — gộp thành một câu chung
    // thì chủ tiệm bấm Huỷ nhầm lại tưởng hệ thống hỏng.
    expect((huy as { message: string }).message).not.toBe(
      (hetHan as { message: string }).message,
    );
  });

  it("mã lỗi lạ vẫn ra câu chung, không hiện mã thô", () => {
    const outcome = readCallbackOutcome("?ket_noi=loi&ly_do=cai_gi_do_moi");
    expect(outcome).toMatchObject({ kind: "error" });
    expect((outcome as { message: string }).message).not.toContain(
      "cai_gi_do_moi",
    );
  });

  it("URL không có tham số thì không hiện banner nào", () => {
    expect(readCallbackOutcome("")).toBeNull();
    expect(readCallbackOutcome("?tab=1")).toBeNull();
  });
});

describe("ConnectionsScreen", () => {
  beforeEach(() => {
    window.localStorage.clear();
    signedIn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("kênh chưa nối thì hiện nút kết nối, không hiện Đã nối", async () => {
    mockConnections([]);
    render(<ConnectionsScreen />);

    expect(
      await screen.findByRole("button", { name: /kết nối facebook page/i }),
    ).toBeInTheDocument();
    expect(screen.getByText("Chưa nối")).toBeInTheDocument();
    expect(screen.queryByText("Đã nối")).not.toBeInTheDocument();
  });

  it("kênh đã nối hiện tên Page và không có nút nối lại", async () => {
    mockConnections([connection()]);
    render(<ConnectionsScreen />);

    expect(await screen.findByText("Đã nối")).toBeInTheDocument();
    expect(screen.getByText("Spa An Nhiên")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /nối lại/i }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /ngắt kênh/i }),
    ).toBeInTheDocument();
  });

  it("token hết hạn thì hiện CTA nối lại kèm lý do", async () => {
    mockConnections([connection({ status: "expired" })]);
    render(<ConnectionsScreen />);

    expect(await screen.findByText("Hết hạn")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /nối lại/i }),
    ).toBeInTheDocument();
    // Chủ tiệm phải biết vì sao bài ngừng đăng, không chỉ thấy một nhãn đỏ.
    expect(screen.getByText(/hết hạn cấp quyền/i)).toBeInTheDocument();
  });

  it("mất quyền nói lý do khác với hết hạn", async () => {
    mockConnections([connection({ status: "revoked" })]);
    render(<ConnectionsScreen />);

    expect(await screen.findByText("Mất quyền")).toBeInTheDocument();
    expect(screen.getByText(/quyền quản trị/i)).toBeInTheDocument();
  });

  it("bấm kết nối thì điều hướng sang URL của Facebook", async () => {
    const assign = stubAssign();
    vi.spyOn(globalThis, "fetch").mockImplementation(
      async (input: RequestInfo | URL) => {
        const url = input instanceof Request ? input.url : String(input);
        if (url.includes("/start")) {
          return jsonResponse({
            authorization_url: "https://www.facebook.com/dialog/oauth?state=s1",
            state: "s1",
          });
        }
        return jsonResponse([]);
      },
    );

    render(<ConnectionsScreen />);
    const user = userEvent.setup();
    await user.click(
      await screen.findByRole("button", { name: /kết nối facebook page/i }),
    );

    await waitFor(() =>
      expect(assign).toHaveBeenCalledWith(
        "https://www.facebook.com/dialog/oauth?state=s1",
      ),
    );
  });

  it("nối từ Cài đặt thì xin backend đưa về Cài đặt, không về onboarding", async () => {
    // Đây là mấu chốt của cả bản sửa: thiếu `tro_ve=settings` thì chủ tiệm dùng
    // app hàng tháng bấm "Nối lại" xong bị đá vào wizard onboarding.
    const assign = stubAssign();
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation(async (input: RequestInfo | URL) => {
        const url = input instanceof Request ? input.url : String(input);
        if (url.includes("/start")) {
          return jsonResponse({
            authorization_url: "https://www.facebook.com/dialog/oauth?state=s1",
            state: "s1",
          });
        }
        return jsonResponse([]);
      });

    render(<ConnectionsScreen />);
    const user = userEvent.setup();
    await user.click(
      await screen.findByRole("button", { name: /kết nối facebook page/i }),
    );

    await waitFor(() => expect(assign).toHaveBeenCalled());
    const startUrl = fetchSpy.mock.calls
      .map(([input]) => (input instanceof Request ? input.url : String(input)))
      .find((u) => u.includes("/start"));
    expect(startUrl).toContain("tro_ve=settings");
  });

  it("kênh chưa có adapter (501) báo chưa hỗ trợ, không im lặng", async () => {
    stubAssign();
    vi.spyOn(globalThis, "fetch").mockImplementation(
      async (input: RequestInfo | URL) => {
        const url = input instanceof Request ? input.url : String(input);
        if (url.includes("/start")) {
          return jsonResponse({ detail: "chua ho tro" }, 501);
        }
        return jsonResponse([]);
      },
    );

    render(<ConnectionsScreen />);
    const user = userEvent.setup();
    await user.click(
      await screen.findByRole("button", { name: /kết nối facebook page/i }),
    );

    expect(await screen.findByRole("alert")).toHaveTextContent(/chưa nối được/i);
  });

  it("chỉ liệt kê kênh pilot — không hứa TikTok/Zalo/Maps", async () => {
    mockConnections([]);
    render(<ConnectionsScreen />);

    await screen.findByText("Chưa nối");
    for (const kenh of ["TikTok", "Zalo", "Maps", "YouTube"]) {
      expect(screen.queryByText(new RegExp(kenh, "i"))).not.toBeInTheDocument();
    }
  });

  it("API trả về thứ không phải mảng thì báo lỗi chứ không đổ trang", async () => {
    mockConnections({ detail: "khong phai mang" });
    render(<ConnectionsScreen />);

    expect(await screen.findByRole("alert")).toBeInTheDocument();
    // Trang vẫn còn đó để chủ tiệm thử lại.
    expect(
      screen.getByRole("heading", { name: /kênh đã nối/i }),
    ).toBeInTheDocument();
  });
});
