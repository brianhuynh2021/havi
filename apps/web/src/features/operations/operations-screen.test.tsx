import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { writeTokens } from "@/lib/auth/token-store";
import { OperationsScreen } from "./operations-screen";

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

function metrics(overrides: Record<string, unknown> = {}) {
  return {
    window_start: "2026-08-05T17:00:00Z",
    window_end: "2026-08-12T17:00:00Z",
    event_count: 12,
    error_count: 3,
    error_rate: 0.25,
    avg_duration_ms: 120,
    p95_duration_ms: 410,
    tokens_in: 1000,
    tokens_out: 250,
    tokens_total: 1250,
    providers: [
      {
        provider: "openai",
        event_count: 8,
        error_count: 1,
        tokens_total: 900,
      },
      {
        provider: "facebook",
        event_count: 4,
        error_count: 2,
        tokens_total: 0,
      },
    ],
    publish: {
      total: 5,
      succeeded: 4,
      dead_letter: 1,
      success_rate: 0.8,
      dead_letter_rate: 0.2,
    },
    ...overrides,
  };
}

describe("OperationsScreen", () => {
  beforeEach(() => {
    window.localStorage.clear();
    signedIn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("hiện aggregate metrics nội bộ từ analytics operations", async () => {
    const asked: URL[] = [];
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input: RequestInfo | URL) => {
      const request = input instanceof Request ? input : new Request(input);
      const url = new URL(request.url);
      asked.push(url);
      return jsonResponse(metrics());
    });

    render(<OperationsScreen />);

    expect(await screen.findByText("Vận hành")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
    expect(screen.getByText("25%")).toBeInTheDocument();
    expect(screen.getByText("1.250")).toBeInTheDocument();
    expect(screen.getByText("410ms")).toBeInTheDocument();
    expect(screen.getByText("Publish health")).toBeInTheDocument();
    expect(screen.getByText("80%")).toBeInTheDocument();
    expect(screen.getByText("20%")).toBeInTheDocument();
    expect(screen.getByText("Provider breakdown")).toBeInTheDocument();
    expect(screen.getByText("openai")).toBeInTheDocument();
    expect(screen.getByText("facebook")).toBeInTheDocument();
    await waitFor(() => expect(asked[0].pathname).toBe("/analytics/operations"));
    expect(asked[0].searchParams.get("start")).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    expect(asked[0].searchParams.get("end")).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });

  it("không hiển thị request body, token secret hay raw error", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(
        metrics({
          input_summary: "customer@example.com prompt body",
          output_summary: "sk-secret raw response",
          error: "Graph token expired",
        }),
      ),
    );

    render(<OperationsScreen />);

    expect(await screen.findByText("Provider breakdown")).toBeInTheDocument();
    expect(screen.queryByText(/customer@example.com/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/sk-secret/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/graph token expired/i)).not.toBeInTheDocument();
  });

  it("workspace rỗng có empty state", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(
        metrics({
          event_count: 0,
          error_count: 0,
          error_rate: 0,
          avg_duration_ms: 0,
          p95_duration_ms: 0,
          tokens_in: 0,
          tokens_out: 0,
          tokens_total: 0,
          providers: [],
          publish: {
            total: 0,
            succeeded: 0,
            dead_letter: 0,
            success_rate: 0,
            dead_letter_rate: 0,
          },
        }),
      ),
    );

    render(<OperationsScreen />);

    expect(await screen.findByText(/chưa có dữ liệu vận hành/i)).toBeInTheDocument();
    expect(screen.getByText(/chưa có provider nào/i)).toBeInTheDocument();
  });

  it("lỗi mạng thì báo rõ và cho thử lại", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("fail"));

    render(<OperationsScreen />);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      /không kết nối được/i,
    );
    expect(screen.getByRole("button", { name: /thử lại/i })).toBeInTheDocument();
  });
});
