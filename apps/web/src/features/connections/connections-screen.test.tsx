import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { writeTokens } from "@/lib/auth/token-store";
import { LanguageProvider } from "@/lib/i18n/language-context";
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

function mockConnections(body: unknown, status = 200) {
  return vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(async () => jsonResponse(body, status));
}

function stubAssign() {
  const assign = vi.fn();
  vi.spyOn(window, "open").mockReturnValue(null);
  Object.defineProperty(window, "location", {
    configurable: true,
    value: { ...window.location, assign, search: "", href: "http://localhost/cai-dat" },
  });
  return assign;
}

function renderConnections() {
  return render(
    <LanguageProvider>
      <ConnectionsScreen />
    </LanguageProvider>
  );
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
    renderConnections();

    expect(
      (await screen.findAllByRole("button", { name: /^kết nối$/i }))[0],
    ).toBeInTheDocument();
    expect(screen.getAllByText("Chưa kết nối")[0]).toBeInTheDocument();
    expect(screen.queryByText("Đã nối")).not.toBeInTheDocument();
  });

  it("kênh đã nối hiện tên Page và không có nút nối lại", async () => {
    mockConnections([connection()]);
    renderConnections();

    expect(await screen.findByText("Đã nối")).toBeInTheDocument();
    expect(screen.getByText("Spa An Nhiên")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /nối lại/i }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /ngắt kết nối/i }),
    ).toBeInTheDocument();
  });

  it("token hết hạn thì hiện CTA nối lại kèm lý do", async () => {
    mockConnections([connection({ status: "expired" })]);
    renderConnections();

    expect(await screen.findByText("Hết hạn")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /nối lại/i }),
    ).toBeInTheDocument();
    expect(screen.getByText(/hết hạn cấp quyền/i)).toBeInTheDocument();
  });

  it("mất quyền nói lý do khác với hết hạn", async () => {
    mockConnections([connection({ status: "revoked" })]);
    renderConnections();

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

    renderConnections();
    const user = userEvent.setup();

    const connectButton = (await screen.findAllByRole("button", {
      name: /^kết nối$/i,
    }))[0];
    await user.click(connectButton);

    await waitFor(() =>
      expect(assign).toHaveBeenCalledWith(
        "https://www.facebook.com/dialog/oauth?state=s1",
      ),
    );
  });
});
