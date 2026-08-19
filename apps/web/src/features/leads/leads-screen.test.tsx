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

function renderLeads(defaultTab: "inbox" | "leads" = "inbox") {
  return render(
    <LanguageProvider>
      <LeadsScreen defaultTab={defaultTab} />
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

  it("hiển thị danh sách tin nhắn chăm sóc khách cũ và duyệt gửi", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(
      async (input: RequestInfo | URL) => {
        const url = new URL(input instanceof Request ? input.url : String(input));
        if (url.pathname.endsWith("/inbox")) {
          return jsonResponse({ items: [], total: 0 });
        }
        if (url.pathname.endsWith("/leads")) {
          return jsonResponse({ items: [], total: 0 });
        }
        if (url.pathname.includes("/crm/nudges")) {
          return jsonResponse({
            items: [
              {
                id: "nudge-1",
                workspace_id: "w1",
                lead_id: "lead-1",
                nudge_type: "inactive_30_days",
                status: "pending_approval",
                message: "Chào chị Lan, tiệm tặng chị voucher giảm 20% khi ghé tuần này nhé!",
                created_at: "2026-08-13T10:00:00Z",
              },
            ],
            total: 1,
          });
        }
        return jsonResponse({});
      }
    );

    renderLeads("leads");

    expect(
      await screen.findByText(/Chào chị Lan, tiệm tặng chị voucher/i)
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /duyệt & gửi tin nhắn/i })).toBeInTheDocument();
  });

  it("hiển thị Hot Lead Radar và 2 nút gọi điện + nhắn Zalo cho khách có SĐT", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(
      async (input: RequestInfo | URL) => {
        const url = new URL(input instanceof Request ? input.url : String(input));
        if (url.pathname.endsWith("/leads")) {
          return jsonResponse({
            items: [
              {
                id: "lead-vip",
                workspace_id: "w1",
                name: "Chị Ngọc",
                phone: "0912345678",
                source: "facebook",
                stage: "qualified",
                message: "Tư vấn cho mình gói chăm sóc da mụn",
                created_at: "2026-08-19T10:00:00Z",
              },
            ],
            total: 1,
          });
        }
        if (url.pathname.includes("/crm/nudges")) {
          return jsonResponse({ items: [], total: 0 });
        }
        return jsonResponse({ items: [], total: 0 });
      }
    );

    renderLeads("leads");

    expect(await screen.findByText(/Hot Lead Radar/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /bắn thử chuông báo/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /mở bot telegram/i })).toHaveAttribute(
      "href",
      "https://t.me/HaviLeadAlertBot"
    );
    expect(screen.getByText("Chị Ngọc")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /gọi điện ngay/i })).toHaveAttribute(
      "href",
      "tel:0912345678"
    );
    expect(screen.getByRole("link", { name: /nhắn zalo/i })).toHaveAttribute(
      "href",
      "https://zalo.me/0912345678"
    );
  });
});
