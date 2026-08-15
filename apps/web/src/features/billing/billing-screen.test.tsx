import { render, screen, waitFor } from "@testing-library/react";
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

  it("tải gói cước hiện tại và hiển thị hạn mức Token", async () => {
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
            amount_vnd: 299000,
            status: "paid",
            issued_at: "2026-08-15T10:00:00Z",
          },
        ]);
      }
      return jsonResponse([]);
    });

    renderBilling();

    const planTitles = await screen.findAllByText(/Gói Tiệm Đơn/i);
    expect(planTitles.length).toBeGreaterThan(0);
    expect(screen.getByText(/50.000 \/ 250.000 Tokens/i)).toBeInTheDocument();
    const prices = screen.getAllByText(/299.000/i);
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
      return jsonResponse([]);
    });

    renderBilling();
    const user = userEvent.setup();

    const upgradeBtn = await screen.findByRole("button", {
      name: /Nâng cấp lên Gói Tiệm Đơn/i,
    });
    await user.click(upgradeBtn);

    expect(await screen.findByText(/Quét mã VietQR để nâng cấp Gói Tiệm Đơn/i)).toBeInTheDocument();
    expect(screen.getByText(/CONG TY HAVI VIETNAM/i)).toBeInTheDocument();
  });
});
