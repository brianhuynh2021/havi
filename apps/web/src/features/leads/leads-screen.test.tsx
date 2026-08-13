import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { writeTokens } from "@/lib/auth/token-store";
import { LanguageProvider } from "@/lib/i18n/language-context";
import { LeadsScreen } from "./leads-screen";

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

function renderLeads() {
  return render(
    <LanguageProvider>
      <LeadsScreen />
    </LanguageProvider>
  );
}

describe("LeadsScreen", () => {
  beforeEach(() => {
    window.localStorage.clear();
    signedIn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("tải danh sách tin nhắn inbox từ API thật", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(
      async (input: RequestInfo | URL) => {
        const url = new URL(input instanceof Request ? input.url : String(input));
        if (url.pathname.endsWith("/inbox")) {
          return jsonResponse({
            items: [
              {
                id: "item-1",
                workspace_id: "w1",
                platform: "facebook",
                type: "message",
                content: "Shop cho mình xin bảng giá với ạ",
                author_name: "Chị Mai",
                status: "drafted",
                ai_suggested_reply: "Chào Chị Mai, Havi đã nhận thông tin!",
                created_at: "2026-08-13T10:00:00Z",
              },
            ],
            total: 1,
            limit: 50,
            offset: 0,
          });
        }
        if (url.pathname.endsWith("/leads")) {
          return jsonResponse({ items: [], total: 0, limit: 50, offset: 0 });
        }
        return jsonResponse({});
      }
    );

    renderLeads();

    expect(await screen.findByText("Chị Mai")).toBeInTheDocument();
    expect(screen.getByText(/Shop cho mình xin bảng giá/i)).toBeInTheDocument();
    expect(screen.getByText(/Havi đã nhận thông tin/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /duyệt & gửi/i })).toBeInTheDocument();
  });

  it("xử lý trạng thái rỗng khi chưa có tin nhắn", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(
      async (input: RequestInfo | URL) => {
        const url = new URL(input instanceof Request ? input.url : String(input));
        if (url.pathname.endsWith("/inbox")) {
          return jsonResponse({ items: [], total: 0, limit: 50, offset: 0 });
        }
        return jsonResponse({ items: [], total: 0, limit: 50, offset: 0 });
      }
    );

    renderLeads();

    expect(
      await screen.findByText(/chưa có tin nhắn hoặc bình luận nào/i)
    ).toBeInTheDocument();
  });

  it("báo lỗi khi không kết nối được backend", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("fail"));

    renderLeads();

    expect(await screen.findByRole("alert")).toHaveTextContent(
      /không kết nối được/i
    );
    expect(screen.getByRole("button", { name: /thử lại/i })).toBeInTheDocument();
  });
});
