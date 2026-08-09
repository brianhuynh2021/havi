import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { writeTokens } from "@/lib/auth/token-store";
import { ContentCreationScreen } from "./content-creation-screen";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function pendingItem(id: string, channel = "facebook_page") {
  return {
    id,
    workspace_id: "w1",
    job_id: "j1",
    channel,
    kind: "Bài ảnh",
    text: `Nội dung ${id}`,
    status: "pending_approval",
    version_no: 1,
  };
}

/** Router theo URL — mỗi test chỉ khai phần nó quan tâm. */
type Routes = {
  list?: () => Response;
  ticket?: () => Response;
  storage?: () => Response;
  complete?: () => Response;
  createJob?: () => Response;
  getJob?: () => Response;
  approve?: () => Response;
  reject?: () => Response;
  approveAll?: () => Response;
  patch?: () => Response;
  versions?: () => Response;
  quota?: () => Response;
};

function mockApi(routes: Routes = {}) {
  return vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(async (input: RequestInfo | URL) => {
      const req = input instanceof Request ? input : null;
      const url = req ? req.url : String(input);
      const method = req?.method ?? "GET";

      // Phải đứng TRƯỚC nhánh `/content` chung: QuotaBanner gọi
      // `/content/quota`, mà URL đó cũng khớp `includes("/content")` nên sẽ nhận
      // nhầm body của danh sách bài. Mặc định là quota còn nhiều → banner ẩn.
      if (url.includes("/content/quota")) {
        return (
          routes.quota?.() ??
          jsonResponse({
            used: 1_000,
            limit: 100_000,
            remaining: 99_000,
            near_limit: false,
            exceeded: false,
            resets_at: "2026-09-01T00:00:00Z",
          })
        );
      }

      if (url.includes("/media/upload-ticket")) {
        return (
          routes.ticket?.() ??
          jsonResponse(
            {
              asset_id: "asset-1",
              upload_url: "http://storage.local/havi",
              fields: { key: "w1/asset-1.jpg", policy: "abc" },
            },
            201,
          )
        );
      }
      if (url.includes("/complete")) {
        return routes.complete?.() ?? jsonResponse({ id: "asset-1" });
      }
      if (url.startsWith("http://storage.local")) {
        return routes.storage?.() ?? new Response(null, { status: 204 });
      }
      if (url.includes("/versions")) {
        return (
          routes.versions?.() ??
          jsonResponse([
            { content_item_id: "c1", version_no: 1, text: "Bản gốc", edited_by: null, edited_at: "2026-08-08T02:00:00Z" },
          ])
        );
      }
      if (method === "PATCH") {
        return routes.patch?.() ?? jsonResponse({ ...pendingItem("c1"), text: "Đã sửa", version_no: 2 });
      }
      if (url.includes("/content/approve-all")) {
        return (
          routes.approveAll?.() ?? jsonResponse({ approved: [], rejected: [] })
        );
      }
      if (url.includes("/approve")) {
        return routes.approve?.() ?? jsonResponse(pendingItem("c1"));
      }
      if (url.includes("/reject")) {
        return routes.reject?.() ?? jsonResponse(pendingItem("c1"));
      }
      if (url.includes("/content/jobs/")) {
        return routes.getJob?.() ?? jsonResponse({ id: "j1", status: "queued" });
      }
      if (url.includes("/content/jobs") && method === "POST") {
        return (
          routes.createJob?.() ??
          jsonResponse({ id: "j1", status: "queued" }, 202)
        );
      }
      // GET /content?status=pending_approval
      return (
        routes.list?.() ?? jsonResponse({ items: [], total: 0, limit: 50, offset: 0 })
      );
    });
}

async function chonAnh() {
  const user = userEvent.setup();
  const input = screen.getByTestId("file-input") as HTMLInputElement;
  const file = new File(["xxx"], "goi-dau.jpg", { type: "image/jpeg" });
  await user.upload(input, file);
}

describe("ContentCreationScreen", () => {
  beforeEach(() => {
    window.localStorage.clear();
    writeTokens({
      accessToken: "a",
      refreshToken: "r",
      activeWorkspaceId: "w1",
      needsOnboarding: false,
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("workspace mới thì hiện empty state, không render số liệu giả", async () => {
    mockApi();
    render(<ContentCreationScreen />);

    expect(
      await screen.findByText(/chưa có bản nháp nào chờ duyệt/i),
    ).toBeInTheDocument();
    expect(screen.getByText(/0 bản nháp chờ chị duyệt/i)).toBeInTheDocument();
  });

  it("hiện bản nháp thật lấy từ API", async () => {
    mockApi({
      list: () =>
        jsonResponse({
          items: [pendingItem("c1"), pendingItem("c2", "zalo_oa")],
          total: 2,
          limit: 50,
          offset: 0,
        }),
    });
    render(<ContentCreationScreen />);

    expect(await screen.findByText("Nội dung c1")).toBeInTheDocument();
    expect(screen.getByText("Nội dung c2")).toBeInTheDocument();
    // Nhãn kênh phải dịch sang tiếng Việt, không hiện enum thô.
    expect(screen.getByText("Zalo OA")).toBeInTheDocument();
  });

  it("upload ảnh đi thẳng lên storage rồi mới báo API complete", async () => {
    const fetchSpy = mockApi();
    render(<ContentCreationScreen />);
    await screen.findByText(/chưa có bản nháp nào/i);

    await chonAnh();

    // Chip xuất hiện nghĩa là cả 3 bước đã xong.
    expect(await screen.findByText("goi-dau.jpg")).toBeInTheDocument();

    const calls = fetchSpy.mock.calls.map(([input]) =>
      input instanceof Request ? input.url : String(input),
    );
    expect(calls.some((u) => u.includes("/media/upload-ticket"))).toBe(true);
    // Bytes không đi qua API — POST thẳng lên object storage.
    expect(calls.some((u) => u.startsWith("http://storage.local"))).toBe(true);
    expect(calls.some((u) => u.includes("/complete"))).toBe(true);
  });

  it("tạo job có gửi Idempotency-Key để bấm hai lần không tốn hai lần tiền LLM", async () => {
    const fetchSpy = mockApi();
    render(<ContentCreationScreen />);
    await screen.findByText(/chưa có bản nháp nào/i);
    await chonAnh();
    await screen.findByText("goi-dau.jpg");

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /để havi viết cho chị/i }));

    await waitFor(() => {
      const jobCall = fetchSpy.mock.calls.find(([input]) => {
        const req = input instanceof Request ? input : null;
        return req?.url.includes("/content/jobs") && req.method === "POST";
      });
      expect(jobCall).toBeDefined();
      const req = jobCall![0] as Request;
      expect(req.headers.get("Idempotency-Key")).toBeTruthy();
    });
  });

  it("job đang chạy thì hiện trạng thái thật, không dùng timer giả lập", async () => {
    mockApi({ getJob: () => jsonResponse({ id: "j1", status: "processing" }) });
    render(<ContentCreationScreen />);
    await screen.findByText(/chưa có bản nháp nào/i);
    await chonAnh();
    await screen.findByText("goi-dau.jpg");

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /để havi viết cho chị/i }));

    expect(await screen.findByText(/havi đang viết bài/i)).toBeInTheDocument();
  });

  it("job failed thì báo lỗi và cho thử lại, không quay vô tận", async () => {
    mockApi({ getJob: () => jsonResponse({ id: "j1", status: "failed" }) });
    render(<ContentCreationScreen />);
    await screen.findByText(/chưa có bản nháp nào/i);
    await chonAnh();
    await screen.findByText("goi-dau.jpg");

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /để havi viết cho chị/i }));

    expect(
      await screen.findByText(/havi chưa viết được lần này/i),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /thử lại/i })).toBeInTheDocument();
  });

  it("duyệt một bài thì bài rời hàng chờ", async () => {
    let listed = false;
    mockApi({
      list: () => {
        // Lượt đầu có 1 bài; sau khi duyệt, backend không còn trả bài đó nữa.
        const items = listed ? [] : [pendingItem("c1")];
        listed = true;
        return jsonResponse({ items, total: items.length, limit: 50, offset: 0 });
      },
      approve: () => jsonResponse({ ...pendingItem("c1"), status: "scheduled" }),
    });
    render(<ContentCreationScreen />);
    await screen.findByText("Nội dung c1");

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /^duyệt$/i }));

    await waitFor(() =>
      expect(screen.queryByText("Nội dung c1")).not.toBeInTheDocument(),
    );
    expect(
      await screen.findByText(/đã duyệt — bài sẽ lên đúng lịch/i),
    ).toBeInTheDocument();
  });

  it("duyệt bài đã đổi trạng thái nơi khác thì báo 409, không im lặng", async () => {
    mockApi({
      list: () =>
        jsonResponse({
          items: [pendingItem("c1")],
          total: 1,
          limit: 50,
          offset: 0,
        }),
      approve: () => jsonResponse({ detail: "conflict" }, 409),
    });
    render(<ContentCreationScreen />);
    await screen.findByText("Nội dung c1");

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /^duyệt$/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      /vừa đổi trạng thái/i,
    );
  });

  it("duyệt hết mà có bài hỏng thì nói rõ bài nào chưa duyệt được", async () => {
    mockApi({
      list: () =>
        jsonResponse({
          items: [pendingItem("c1"), pendingItem("c2")],
          total: 2,
          limit: 50,
          offset: 0,
        }),
      approveAll: () =>
        jsonResponse({
          approved: ["c1"],
          rejected: [{ content_item_id: "c2", reason: "Bài đang đăng dở" }],
        }),
    });
    render(<ContentCreationScreen />);
    await screen.findByText("Nội dung c1");

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /duyệt & đăng hết/i }));

    const notice = await screen.findByText(/đã duyệt 1 bài/i);
    expect(notice).toHaveTextContent(/1 bài chưa duyệt được/i);
    expect(notice).toHaveTextContent(/đang đăng dở/i);
  });

  it("full_auto vẫn cảnh báo là đang khoá trong pilot", async () => {
    mockApi();
    render(<ContentCreationScreen />);
    await screen.findByText(/chưa có bản nháp nào/i);

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /tự động đăng/i }));

    const toggle = screen.getByLabelText("Chế độ đăng bài");
    expect(within(toggle).getByText(/đang khoá trong bản pilot/i)).toBeInTheDocument();
  });
});

describe("DraftEditor trong màn Tạo nội dung", () => {
  beforeEach(() => {
    window.localStorage.clear();
    writeTokens({
      accessToken: "a",
      refreshToken: "r",
      activeWorkspaceId: "w1",
      needsOnboarding: false,
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  async function moEditor() {
    mockApi({
      list: () =>
        jsonResponse({ items: [pendingItem("c1")], total: 1, limit: 50, offset: 0 }),
    });
    render(<ContentCreationScreen />);
    await screen.findByText("Nội dung c1");
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /^sửa$/i }));
    return user;
  }

  it("sửa text rồi lưu thì gọi PATCH và hiện bản mới", async () => {
    const user = await moEditor();
    const box = await screen.findByLabelText("Nội dung bài");

    await user.clear(box);
    await user.type(box, "Đã sửa");
    await user.click(screen.getByRole("button", { name: /lưu bản sửa/i }));

    expect(await screen.findByText(/đã lưu bản sửa/i)).toBeInTheDocument();
  });

  it("chưa sửa gì thì nút Lưu bị khoá — không tạo version rác", async () => {
    await moEditor();
    expect(
      await screen.findByRole("button", { name: /lưu bản sửa/i }),
    ).toBeDisabled();
  });

  it("bài đang đăng thì backend trả 409 và UI nói rõ", async () => {
    const user = await moEditor();
    // Ghi đè route PATCH sau khi editor đã mở.
    vi.restoreAllMocks();
    mockApi({
      list: () =>
        jsonResponse({ items: [pendingItem("c1")], total: 1, limit: 50, offset: 0 }),
      patch: () => jsonResponse({ detail: "conflict" }, 409),
    });

    const box = await screen.findByLabelText("Nội dung bài");
    await user.type(box, " thêm chữ");
    await user.click(screen.getByRole("button", { name: /lưu bản sửa/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      /không sửa được nữa/i,
    );
  });

  it("mở lịch sử thì hiện các bản đã sửa", async () => {
    const user = await moEditor();
    await user.click(await screen.findByRole("button", { name: /lịch sử/i }));

    expect(await screen.findByText("Bản gốc")).toBeInTheDocument();
    expect(screen.getByText(/bản 1/i)).toBeInTheDocument();
  });
});
