import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { writeTokens } from "@/lib/auth/token-store";
import { FailedPostsPanel } from "./failed-posts-panel";

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
  }: {
    href: string;
    children: React.ReactNode;
  }) => <a href={href}>{children}</a>,
}));

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

function job(overrides: Record<string, unknown> = {}) {
  return {
    id: "job-1",
    workspace_id: "w1",
    content_item_id: "item-1",
    channel: "facebook_page",
    status: "dead_letter",
    scheduled_at: "2026-08-09T13:00:00Z",
    attempt_count: 4,
    next_attempt_at: null,
    external_post_id: null,
    published_at: null,
    failure_kind: "temporary",
    failure_detail: "Rate limit — thử lại sau",
    ...overrides,
  };
}

/** Mock ở tầng transport để `apiClient` thật vẫn chạy (header, refresh 401). */
function mockApi(handler: (url: string, method: string) => Response) {
  return vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = input instanceof Request ? input.url : String(input);
      const method =
        input instanceof Request ? input.method : (init?.method ?? "GET");
      return handler(url, method);
    });
}

describe("FailedPostsPanel", () => {
  beforeEach(() => {
    window.localStorage.clear();
    signedIn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("không có bài lỗi thì ẩn hẳn, không chiếm chỗ", async () => {
    mockApi(() => jsonResponse([]));
    const { container } = render(<FailedPostsPanel />);

    await waitFor(() => expect(container).toBeEmptyDOMElement());
  });

  it("hiện lý do lỗi và số lần đã thử", async () => {
    mockApi(() => jsonResponse([job()]));
    render(<FailedPostsPanel />);

    expect(await screen.findByText("Lỗi tạm thời")).toBeInTheDocument();
    expect(screen.getByText(/Đã thử 4 lần/)).toBeInTheDocument();
    expect(screen.getByText(/1 bài chưa đăng được/)).toBeInTheDocument();
  });

  it("mất quyền thì KHÔNG cho thử lại, dẫn sang nối lại kênh", async () => {
    // Thử lại khi token đã hỏng thì vẫn hỏng y hệt — đưa nút vào đó là mời chủ
    // tiệm bấm mười lần rồi kết luận Havi hỏng.
    mockApi(() => jsonResponse([job({ failure_kind: "auth_permission" })]));
    render(<FailedPostsPanel />);

    expect(await screen.findByText("Mất quyền đăng bài")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /thử lại/i }),
    ).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: /nối lại kênh/i })).toHaveAttribute(
      "href",
      "/cai-dat",
    );
  });

  it("nội dung bị từ chối vẫn cho thử lại (sửa text rồi đăng lại được)", async () => {
    mockApi(() =>
      jsonResponse([job({ failure_kind: "validation_permanent" })]),
    );
    render(<FailedPostsPanel />);

    expect(
      await screen.findByText("Nền tảng từ chối nội dung"),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /thử lại/i }),
    ).toBeInTheDocument();
  });

  it("thử lại thành công thì bỏ bài khỏi danh sách và báo màn ngoài", async () => {
    const onPublished = vi.fn();
    mockApi((url, method) => {
      if (method === "POST" && url.includes("/retry")) {
        return jsonResponse(job({ status: "succeeded", failure_kind: null }));
      }
      return jsonResponse([job()]);
    });

    render(<FailedPostsPanel onPublished={onPublished} />);
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: /thử lại/i }));

    await waitFor(() => expect(onPublished).toHaveBeenCalled());
    expect(screen.queryByText("Lỗi tạm thời")).not.toBeInTheDocument();
  });

  it("thử lại vẫn hỏng thì hiện lý do MỚI, không giữ lý do cũ", async () => {
    mockApi((url, method) => {
      if (method === "POST" && url.includes("/retry")) {
        return jsonResponse(
          job({
            failure_kind: "auth_permission",
            failure_detail: "Token hết hạn",
            attempt_count: 1,
          }),
        );
      }
      return jsonResponse([job()]);
    });

    render(<FailedPostsPanel />);
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: /thử lại/i }));

    // Lý do đổi từ "Lỗi tạm thời" sang "Mất quyền đăng bài" — giữ lý do cũ là
    // nói sai với chủ tiệm về việc vừa xảy ra.
    expect(await screen.findByText("Mất quyền đăng bài")).toBeInTheDocument();
    expect(screen.queryByText("Lỗi tạm thời")).not.toBeInTheDocument();
  });

  it("409 thì báo tải lại, không im lặng", async () => {
    let listCalls = 0;
    mockApi((url, method) => {
      if (method === "POST" && url.includes("/retry")) {
        return jsonResponse({ detail: "trang thai da doi" }, 409);
      }
      listCalls += 1;
      return jsonResponse([job()]);
    });

    render(<FailedPostsPanel />);
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: /thử lại/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/tải lại/i);
    // Và nạp lại danh sách để khớp backend thay vì để chủ tiệm bấm mãi.
    await waitFor(() => expect(listCalls).toBeGreaterThan(1));
  });

  it("hiện giờ theo múi giờ VN, không theo giờ máy", async () => {
    // 13:00 UTC = 20:00 VN. Máy chạy test có thể ở múi giờ nào cũng phải ra 20:00.
    mockApi(() => jsonResponse([job()]));
    render(<FailedPostsPanel />);

    expect(await screen.findByText(/20:00/)).toBeInTheDocument();
  });

  it("API trả về thứ không phải mảng thì không đổ trang", async () => {
    mockApi(() => jsonResponse({ detail: "loi" }));
    render(<FailedPostsPanel />);

    expect(await screen.findByRole("alert")).toBeInTheDocument();
  });
});
