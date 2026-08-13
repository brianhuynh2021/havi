import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { writeTokens } from "@/lib/auth/token-store";
import { LanguageProvider } from "@/lib/i18n/language-context";
import { SettingsScreen } from "./settings-screen";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function workspace(overrides: Record<string, unknown> = {}) {
  return {
    id: "w1",
    name: "Spa An Nhiên",
    industry: "spa",
    plan: "trial",
    publish_mode: "review_first",
    created_at: "2026-08-10T00:00:00Z",
    ...overrides,
  };
}

function profile(overrides: Record<string, unknown> = {}) {
  return {
    workspace_id: "w1",
    industry: "spa",
    tone: "thân thiện",
    banned_claims: ["cam kết 100%"],
    faq: [],
    logo_url: null,
    brand_colors: [],
    ...overrides,
  };
}

function signedIn() {
  writeTokens({
    accessToken: "at",
    refreshToken: "rt",
    activeWorkspaceId: "w1",
    needsOnboarding: false,
  });
}

function renderSettings() {
  return render(
    <LanguageProvider>
      <SettingsScreen />
    </LanguageProvider>
  );
}

describe("SettingsScreen", () => {
  beforeEach(() => {
    window.localStorage.clear();
    signedIn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("load workspace, brand profile và kênh nối", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input: RequestInfo | URL) => {
      const request = input instanceof Request ? input : new Request(input);
      if (request.url.includes("/workspaces/w1")) return jsonResponse(workspace());
      if (request.url.includes("/brand-profile")) return jsonResponse(profile());
      if (request.url.includes("/connections")) return jsonResponse([]);
      return jsonResponse({ detail: "not found" }, 404);
    });

    renderSettings();

    expect(await screen.findByDisplayValue("Spa An Nhiên")).toBeInTheDocument();
    expect(screen.getByDisplayValue("thân thiện")).toBeInTheDocument();
  });

  it("save workspace và brand voice", async () => {
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation(async (input: RequestInfo | URL) => {
        const request = input instanceof Request ? input : new Request(input);
        if (request.method === "GET" && request.url.includes("/workspaces/w1")) {
          return jsonResponse(workspace());
        }
        if (request.method === "GET" && request.url.includes("/brand-profile")) {
          return jsonResponse(profile());
        }
        if (request.method === "GET" && request.url.includes("/connections")) {
          return jsonResponse([]);
        }
        if (request.method === "PATCH" && request.url.includes("/workspaces/w1")) {
          return jsonResponse(workspace({ name: "Tiệm An Nhiên" }));
        }
        if (request.method === "PUT" && request.url.includes("/brand-profile")) {
          return jsonResponse(
            profile({
              tone: "ấm áp, xưng chị em",
              banned_claims: ["cam kết 100%", "trắng da sau 1 lần"],
            }),
          );
        }
        return jsonResponse({ detail: "not found" }, 404);
      });

    renderSettings();
    const user = userEvent.setup();
    await screen.findByDisplayValue("Spa An Nhiên");

    await user.clear(await screen.findByLabelText(/Tên doanh nghiệp/i));
    await user.type(screen.getByLabelText(/Tên doanh nghiệp/i), "Tiệm An Nhiên");
    await user.clear(screen.getByLabelText(/Giọng văn/i));
    await user.type(screen.getByLabelText(/Giọng văn/i), "ấm áp, xưng chị em");
    await user.click(screen.getByRole("button", { name: /lưu/i }));

    expect(await screen.findByText(/thành công/i)).toBeInTheDocument();
  });
});
