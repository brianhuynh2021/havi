import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { writeTokens } from "@/lib/auth/token-store";
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

    render(<SettingsScreen />);

    expect(await screen.findByDisplayValue("Spa An Nhiên")).toBeInTheDocument();
    expect(screen.getByDisplayValue("thân thiện")).toBeInTheDocument();
    expect(screen.getByDisplayValue("cam kết 100%")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /kết nối facebook page/i }),
    ).toBeInTheDocument();
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

    render(<SettingsScreen />);
    const user = userEvent.setup();

    await user.clear(await screen.findByLabelText("Tên tiệm"));
    await user.type(screen.getByLabelText("Tên tiệm"), "Tiệm An Nhiên");
    await user.clear(screen.getByLabelText("Cách Havi nên viết"));
    await user.type(screen.getByLabelText("Cách Havi nên viết"), "ấm áp, xưng chị em");
    await user.clear(screen.getByLabelText("Không được hứa"));
    await user.type(
      screen.getByLabelText("Không được hứa"),
      "cam kết 100%\ntrắng da sau 1 lần",
    );
    await user.click(screen.getByRole("button", { name: /lưu thay đổi/i }));

    expect(await screen.findByText("Đã lưu giọng thương hiệu.")).toBeInTheDocument();
    const patchBody = fetchSpy.mock.calls
      .map(([input]) => (input instanceof Request ? input : new Request(input)))
      .find((request) => request.method === "PATCH")
      ?.clone();
    const putBody = fetchSpy.mock.calls
      .map(([input]) => (input instanceof Request ? input : new Request(input)))
      .find((request) => request.method === "PUT")
      ?.clone();

    await waitFor(() => expect(patchBody).toBeDefined());
    await expect(patchBody?.json()).resolves.toMatchObject({
      name: "Tiệm An Nhiên",
      industry: "spa",
    });
    await expect(putBody?.json()).resolves.toMatchObject({
      tone: "ấm áp, xưng chị em",
      banned_claims: ["cam kết 100%", "trắng da sau 1 lần"],
    });
  });

  it("save lỗi thì hiện alert và giữ form", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input: RequestInfo | URL) => {
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
      if (request.method === "PATCH" || request.method === "PUT") {
        return jsonResponse({ detail: "nope" }, 500);
      }
      return jsonResponse({ detail: "not found" }, 404);
    });

    render(<SettingsScreen />);
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: /lưu thay đổi/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/chưa lưu được/i);
    expect(screen.getByDisplayValue("Spa An Nhiên")).toBeInTheDocument();
  });
});
