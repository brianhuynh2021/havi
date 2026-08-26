import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { writeTokens } from "@/lib/auth/token-store";
import { LanguageProvider } from "@/lib/i18n/language-context";
import { BillingScreen } from "./billing-screen";

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

function renderBilling() {
  return render(
    <LanguageProvider>
      <BillingScreen />
    </LanguageProvider>
  );
}

describe("BillingScreen", () => {
  beforeEach(() => {
    window.localStorage.clear();
    signedIn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("tải gói cước hiện tại và hiển thị hạn mức", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input: RequestInfo | URL) => {
      const url = new URL(input instanceof Request ? input.url : String(input));
      if (url.pathname.includes("/billing/subscription")) {
        return jsonResponse({
          workspace_id: "w1",
          plan: "tiem_nho",
          status: "active",
          current_period_end: "2026-09-15T00:00:00Z",
          token_quota_used: 50000,
          token_quota_limit: 250000,
        });
      }
      if (url.pathname.includes("/billing/invoices")) {
        return jsonResponse([
          {
            id: "inv-1",
            workspace_id: "w1",
            plan: "tiem_nho",
            amount_vnd: 189000,
            status: "paid",
            issued_at: "2026-08-15T10:00:00Z",
          },
        ]);
      }
      return jsonResponse([]);
    });

    renderBilling();

    const planTitles = await screen.findAllByText(/Gói Khởi Nghiệp/i);
    expect(planTitles.length).toBeGreaterThan(0);
    expect(screen.getByText(/50.000 \/ 250.000/i)).toBeInTheDocument();
    const prices = screen.getAllByText(/189.000/i);
    expect(prices.length).toBeGreaterThan(0);
  });

  it("bấm nâng cấp thì mở modal VietQR chuyển khoản", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input: RequestInfo | URL) => {
      const url = new URL(input instanceof Request ? input.url : String(input));
      if (url.pathname.includes("/billing/subscription")) {
        return jsonResponse({
          workspace_id: "w1",
          plan: "trial",
          status: "active",
          current_period_end: null,
          token_quota_used: 1000,
          token_quota_limit: 50000,
        });
      }
      if (url.pathname.includes("/billing/checkout")) {
        return jsonResponse({
          invoice_id: "inv-123",
          plan: "tiem_nho",
          amount_vnd: 189000,
          transfer_content: "HAVI inv123",
          bank_id: "MB",
          account_no: "0987654321",
          account_name: "TRUNG TAM CONG NGHE NHAT MINH",
          qr_code_url: "https://img.vietqr.io/image/MB-0987654321-compact2.png",
        });
      }
      if (url.pathname.includes("/billing/invoices/inv-123/status")) {
        return jsonResponse({ status: "pending" });
      }
      return jsonResponse([]);
    });

    renderBilling();
    const user = userEvent.setup();

    const upgradeBtn = await screen.findByRole("button", {
      name: /Nâng cấp lên Gói Khởi Nghiệp/i,
    });
    await user.click(upgradeBtn);

    expect(await screen.findByText(/Quét mã VietQR để nâng cấp Gói Khởi Nghiệp/i)).toBeInTheDocument();
    expect(screen.getByText(/TRUNG TAM CONG NGHE NHAT MINH/i)).toBeInTheDocument();
  });
  /** Gói cước với trần và hạn kỳ tuỳ biến — phần §05 của bảng giá. */
  function mockSubscription(overrides: Record<string, unknown> = {}) {
    return vi.spyOn(globalThis, "fetch").mockImplementation(
      async (input: RequestInfo | URL) => {
        const url = new URL(input instanceof Request ? input.url : String(input));
        if (url.pathname.includes("/billing/subscription")) {
          return jsonResponse({
            workspace_id: "w1",
            plan: "tiem_nho",
            status: "active",
            current_period_end: "2026-09-15T00:00:00Z",
            token_quota_used: 50000,
            token_quota_limit: 250000,
            seats_used: 2,
            seats_limit: 3,
            channels_used: 1,
            channels_limit: 3,
            days_until_due: 20,
            ...overrides,
          });
        }
        return jsonResponse([]);
      },
    );
  }

  it("hiện trần đang được cưỡng chế, không chỉ hạn mức token", async () => {
    // Trước đó quota token là gate DUY NHẤT theo gói: phân quyền, báo cáo, nhiều
    // thương hiệu đều có ở mọi gói. Thang giá thực chất là một thang token.
    mockSubscription();
    renderBilling();

    expect(await screen.findByText("2 / 3")).toBeInTheDocument();
    expect(screen.getByText("1 / 3")).toBeInTheDocument();
  });

  it("kênh không giới hạn thì nói bằng chữ, không in con số 1.000.000", async () => {
    mockSubscription({ channels_limit: 1_000_000, channels_used: 4 });
    renderBilling();

    // Bảng giá gói Chuỗi cũng có chữ "không giới hạn", nên tìm trong ô trần
    // đang được cưỡng chế chứ không tìm khắp trang.
    const label = await screen.findByText("Kênh đã nối");
    expect(label.parentElement?.textContent).toMatch(/4 \/ không giới hạn/i);
    expect(document.body.textContent).not.toContain("1.000.000");
  });

  it("sắp hết kỳ thì nhắc, vì VietQR không tự trừ tiền", async () => {
    // Mỗi tháng khách phải CHỦ ĐỘNG quyết định trả tiếp — nhắc trước là cơ chế
    // chống churn duy nhất đang có.
    mockSubscription({ days_until_due: 3 });
    renderBilling();

    expect(await screen.findByText(/Còn 3 ngày là hết kỳ/)).toBeInTheDocument();
    expect(screen.getByText(/không tự trừ tiền/)).toBeInTheDocument();
  });

  it("còn xa hạn thì KHÔNG nhắc — nhắc mỗi ngày thì người ta thôi đọc", async () => {
    mockSubscription({ days_until_due: 20 });
    renderBilling();

    await screen.findByText("2 / 3");
    expect(screen.queryByText(/hết kỳ/)).toBeNull();
  });

  it("quá hạn thì nói rõ là đã hết hạn, ở mức cảnh báo khác", async () => {
    mockSubscription({ days_until_due: -2 });
    renderBilling();

    expect(await screen.findByText(/Gói đã hết hạn/)).toBeInTheDocument();
  });
});
