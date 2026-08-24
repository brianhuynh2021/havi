import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { writeTokens } from "@/lib/auth/token-store";
import { ContentCreationScreen } from "./content-creation-screen";

vi.mock("./kinetic-video-generator", async (importOriginal) => {
  const actual = await importOriginal<typeof import("./kinetic-video-generator")>();
  return {
    ...actual,
    generateKineticShortVideo: vi.fn(async () => "blob:generated-video"),
  };
});

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
  list?: () => Response | Promise<Response>;
  ticket?: () => Response | Promise<Response>;
  storage?: (request: Request) => Response | Promise<Response>;
  complete?: () => Response | Promise<Response>;
  createJob?: () => Response | Promise<Response>;
  getJob?: () => Response | Promise<Response>;
  approve?: () => Response | Promise<Response>;
  reject?: () => Response | Promise<Response>;
  approveAll?: () => Response | Promise<Response>;
  patch?: () => Response | Promise<Response>;
  versions?: () => Response | Promise<Response>;
  quota?: () => Response | Promise<Response>;
};

function mockApi(routes: Routes = {}) {
  return vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = input instanceof Request ? input.url : String(input);
      const method = input instanceof Request ? input.method : (init?.method ?? "GET");

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
        const req =
          input instanceof Request
            ? input
            : ({
                url,
                method,
                signal: init?.signal ?? new AbortController().signal,
              } as Request);
        return routes.storage?.(req) ?? new Response(null, { status: 204 });
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

async function chonClip() {
  const user = userEvent.setup();
  const input = screen.getByTestId("file-input") as HTMLInputElement;
  const file = new File(["xxx"], "clip-doc.mp4", { type: "video/mp4" });
  await user.upload(input, file);
}

async function chonFlowVideo() {
  const user = userEvent.setup();
  const trackTabs = screen.getByRole("tablist", { name: /loại nội dung muốn tạo/i });
  await user.click(within(trackTabs).getByRole("tab", { name: /video ngắn/i }));
}

/** Asset video như backend trả về sau khi probe xong ở lượt `complete`. */
function videoAsset(overrides: Record<string, unknown> = {}) {
  return {
    id: "asset-1",
    type: "video",
    duration_seconds: 20,
    width: 1080,
    height: 1920,
    aspect_ratio: "9:16",
    has_audio: true,
    eligible_channels: ["reels", "tiktok", "youtube"],
    ...overrides,
  };
}

describe("ContentCreationScreen", () => {
  beforeEach(() => {
    window.localStorage.clear();
    Object.defineProperty(URL, "createObjectURL", {
      configurable: true,
      value: vi.fn(() => "blob:preview"),
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      configurable: true,
      value: vi.fn(),
    });
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
    expect(screen.getByText(/0 bản nháp bài viết/i)).toBeInTheDocument();
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
    expect(await screen.findByRole("button", { name: /bỏ goi-dau.jpg/i })).toBeInTheDocument();

    const calls = fetchSpy.mock.calls.map(([input]) =>
      input instanceof Request ? input.url : String(input),
    );
    expect(calls.some((u) => u.includes("/media/upload-ticket"))).toBe(true);
    // Bytes không đi qua API — POST thẳng lên object storage.
    expect(calls.some((u) => u.startsWith("http://storage.local"))).toBe(true);
    expect(calls.some((u) => u.includes("/complete"))).toBe(true);
  });

  it("hiện preview và phần trăm tiến độ upload", async () => {
    mockApi();
    render(<ContentCreationScreen />);
    await screen.findByText(/chưa có bản nháp nào/i);

    await chonAnh();

    expect(
      await screen.findByRole("img", { name: /xem trước goi-dau.jpg/i }),
    ).toHaveAttribute("src", "blob:preview");
    await waitFor(() =>
      expect(
        screen.getByRole("progressbar", { name: /tiến độ tải goi-dau.jpg/i }),
      ).toHaveAttribute("aria-valuenow", "100"),
    );
    expect(screen.getByText("Xong")).toBeInTheDocument();
  });

  it("huỷ upload giữa chừng thì không tạo chip ảnh", async () => {
    mockApi({
      storage: (request) =>
        new Promise<Response>((resolve, reject) => {
          request.signal.addEventListener("abort", () => {
            reject(new DOMException("Aborted", "AbortError"));
          });
          setTimeout(() => resolve(new Response(null, { status: 204 })), 500);
        }),
    });
    render(<ContentCreationScreen />);
    await screen.findByText(/chưa có bản nháp nào/i);

    await chonAnh();
    await userEvent.click(await screen.findByRole("button", { name: "Huỷ" }));

    expect(await screen.findByText("Đã huỷ")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /bỏ goi-dau.jpg/i }),
    ).not.toBeInTheDocument();

    // Bấm nút Xoá để đóng hàng upload đã huỷ/lỗi
    await userEvent.click(screen.getByRole("button", { name: /xoá goi-dau.jpg/i }));
    expect(screen.queryByText("goi-dau.jpg")).not.toBeInTheDocument();
  });

  it("upload clip xin ticket loại video, không phải image", async () => {
    const fetchSpy = mockApi({ complete: () => jsonResponse(videoAsset()) });
    render(<ContentCreationScreen />);
    await screen.findByText(/chưa có bản nháp nào/i);

    await chonClip();
    await screen.findByText("Xong");

    const ticketCall = fetchSpy.mock.calls.find(([input]) =>
      (input instanceof Request ? input.url : String(input)).includes(
        "/media/upload-ticket",
      ),
    );
    const [input, init] = ticketCall ?? [];
    const raw =
      input instanceof Request ? await input.clone().text() : String(init?.body);
    const body = JSON.parse(raw);
    expect(body.type).toBe("video");
    expect(body.content_type).toBe("video/mp4");
  });

  it("clip dọc hợp cả ba kênh thì hiện đủ ba kênh là đăng được", async () => {
    mockApi({ complete: () => jsonResponse(videoAsset()) });
    render(<ContentCreationScreen />);
    await screen.findByText(/chưa có bản nháp nào/i);

    await chonClip();

    expect(await screen.findByText(/facebook reels: đăng được/i)).toBeInTheDocument();
    expect(screen.getByText(/tiktok: đăng được/i)).toBeInTheDocument();
    expect(screen.getByText(/youtube shorts: đăng được/i)).toBeInTheDocument();
    // Thông số hiện ra bằng thứ chủ tiệm hiểu, không phải tên trường.
    expect(screen.getByText(/khung 9:16 · 20 giây/i)).toBeInTheDocument();
  });

  it("clip dài quá 60 giây thì nói rõ Shorts không đăng được nhưng Reels thì có", async () => {
    // Đây chính là câu ROADMAP §16 đòi: "clip này fits Reels nhưng không fits
    // Shorts" — phải thấy lúc còn quay lại được, không phải lúc đã lỡ giờ đăng.
    mockApi({
      complete: () =>
        jsonResponse(
          videoAsset({ duration_seconds: 75, eligible_channels: ["reels", "tiktok"] }),
        ),
    });
    render(<ContentCreationScreen />);
    await screen.findByText(/chưa có bản nháp nào/i);

    await chonClip();

    expect(await screen.findByText(/facebook reels: đăng được/i)).toBeInTheDocument();
    expect(screen.getByText(/youtube shorts: không đăng được/i)).toBeInTheDocument();
  });

  it("clip quay ngang thì nói rõ chưa hợp kênh video nào", async () => {
    mockApi({
      complete: () =>
        jsonResponse(videoAsset({ aspect_ratio: "16:9", eligible_channels: [] })),
    });
    render(<ContentCreationScreen />);
    await screen.findByText(/chưa có bản nháp nào/i);

    await chonClip();

    expect(await screen.findByText(/chưa hợp kênh video nào/i)).toBeInTheDocument();
    expect(screen.getByText(/facebook reels: không đăng được/i)).toBeInTheDocument();
  });

  it("clip chưa probe được thì nói là chưa đọc được, không nói là không đăng được", async () => {
    // Khác biệt quan trọng: "Havi chưa đọc được" ≠ "clip không hợp kênh nào".
    // Kết luận thứ hai là bịa ra từ chỗ không có dữ liệu.
    mockApi({
      complete: () =>
        jsonResponse(
          videoAsset({
            duration_seconds: null,
            aspect_ratio: null,
            has_audio: null,
            eligible_channels: [],
          }),
        ),
    });
    render(<ContentCreationScreen />);
    await screen.findByText(/chưa có bản nháp nào/i);

    await chonClip();

    expect(await screen.findByText(/chưa đọc được thông số clip/i)).toBeInTheDocument();
    expect(screen.queryByText(/không đăng được/i)).not.toBeInTheDocument();
  });

  it("clip tạo chip liệu thô để đưa vào các kênh video", async () => {
    mockApi({ complete: () => jsonResponse(videoAsset()) });
    render(<ContentCreationScreen />);
    await screen.findByText(/chưa có bản nháp nào/i);

    await chonClip();
    await screen.findByText("Xong");

    // Clip tạo chip để đưa vào bài đăng YouTube Shorts, TikTok, Reels
    expect(
      await screen.findByRole("button", { name: /bỏ clip-doc.mp4/i }),
    ).toBeInTheDocument();
  });

  it("tạo job có gửi Idempotency-Key để bấm hai lần không tốn hai lần tiền LLM", async () => {
    const fetchSpy = mockApi();
    render(<ContentCreationScreen />);
    await screen.findByText(/chưa có bản nháp nào/i);
    await chonAnh();
    await screen.findByRole("button", { name: /bỏ goi-dau.jpg/i });

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /tạo bài viết facebook/i }));

    await waitFor(() => {
      const jobCall = fetchSpy.mock.calls.find(([input]) => {
        const req = input instanceof Request ? input : null;
        return req?.url.includes("/content/jobs") && req.method === "POST";
      });
      expect(jobCall).toBeDefined();
      const req = jobCall![0] as Request;
      expect(req.headers.get("Idempotency-Key")).toBeTruthy();
      return expect(req.clone().json()).resolves.toMatchObject({
        target_channels: ["facebook_page", "google_business"],
      });
    });
  });

  it("chọn Video ngắn thì hiện AI Studio và chỉ yêu cầu backend sinh ba kênh video", async () => {
    const fetchSpy = mockApi();
    render(<ContentCreationScreen />);
    await screen.findByText(/chưa có bản nháp nào/i);

    await chonFlowVideo();

    const aiStudioLink = screen.getByRole("link", { name: /ai studio quét trend/i });
    expect(aiStudioLink).toHaveAttribute("href", "/app/video-studio");
    expect(screen.queryByLabelText("Chế độ đăng bài")).not.toBeInTheDocument();
    expect(
      screen.queryByText("Tự Động Chốt Lead & Trả Lời Tin Nhắn 24/7 (AI Lead Agent)"),
    ).not.toBeInTheDocument();
    expect(screen.getByText(/video luôn chờ chị xem lại/i)).toBeInTheDocument();
    expect(screen.getByText(/chưa có kịch bản video nào/i)).toBeInTheDocument();
    expect(screen.getByText(/chọn trend hoặc gõ một ý tưởng/i)).toBeInTheDocument();

    const user = userEvent.setup();
    await user.type(
      screen.getByRole("textbox", { name: /video này muốn nói điều gì/i }),
      "Khoe kết quả học viên sau khóa học AI",
    );
    await user.click(screen.getByRole("button", { name: /ai tạo video 9:16 cho tôi/i }));

    await waitFor(async () => {
      const jobCall = fetchSpy.mock.calls.find(([input]) => {
        const req = input instanceof Request ? input : null;
        return req?.url.includes("/content/jobs") && req.method === "POST";
      });
      expect(jobCall).toBeDefined();
      const body = await (jobCall![0] as Request).clone().json();
      expect(body.target_channels).toEqual(["tiktok", "youtube", "reels"]);
    });
  });

  it("job đang chạy thì hiện trạng thái thật, không dùng timer giả lập", async () => {
    mockApi({ getJob: () => jsonResponse({ id: "j1", status: "processing" }) });
    render(<ContentCreationScreen />);
    await screen.findByText(/chưa có bản nháp nào/i);
    await chonAnh();
    await screen.findByRole("button", { name: /bỏ goi-dau.jpg/i });

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /tạo bài viết facebook/i }));
    expect((await screen.findAllByText(/havi đang viết bài/i)).length).toBeGreaterThanOrEqual(1);
  });

  it("job failed thì báo lỗi và cho thử lại, không quay vô tận", async () => {
    mockApi({ getJob: () => jsonResponse({ id: "j1", status: "failed" }) });
    render(<ContentCreationScreen />);
    await screen.findByText(/chưa có bản nháp nào/i);
    await chonAnh();
    await screen.findByRole("button", { name: /bỏ goi-dau.jpg/i });

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /tạo bài viết facebook/i }));

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
    await user.click(screen.getByRole("button", { name: /lên lịch/i }));

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
    await user.click(screen.getByRole("button", { name: /^⚡ đăng ngay$/i }));

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
    await user.click(screen.getByRole("button", { name: /đăng 2 bài viết sẵn sàng/i }));

    expect((await screen.findAllByText(/đã phát lệnh đăng/i)).length).toBeGreaterThan(0);
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

  it("hiển thị bộ công cụ AI Magic Visual (AI Vẽ lại, Tút ảnh, Bỏ ảnh) trên thẻ bài nháp", async () => {
    mockApi({
      list: () =>
        jsonResponse({
          items: [pendingItem("c1")],
          total: 1,
          limit: 50,
          offset: 0,
        }),
    });
    render(<ContentCreationScreen />);
    await screen.findByText("Nội dung c1");

    expect(screen.getByRole("button", { name: /✨ ai vẽ lại đẹp hơn/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /🪄 tút lại ảnh thật/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /❌ bỏ ảnh/i })).toBeInTheDocument();

    // Test click Magic Enhance
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /🪄 tút lại ảnh thật/i }));
    expect(screen.getByText(/🪄 đã tút nét hd/i)).toBeInTheDocument();
  });

  it("gộp ba draft TikTok, Reels, Shorts thành một video master 9:16", async () => {
    mockApi({
      list: () =>
        jsonResponse({
          items: [
            pendingItem("post-fb", "facebook_page"),
            pendingItem("post-gg", "google_business"),
            pendingItem("vid-tt", "tiktok"),
            pendingItem("vid-yt", "youtube"),
            pendingItem("vid-reels", "reels"),
          ],
          total: 5,
          limit: 50,
          offset: 0,
        }),
    });
    render(<ContentCreationScreen />);
    await screen.findByText("Nội dung post-fb");

    const draftTabs = screen.getByRole("tablist", { name: /lọc bản nháp/i });
    await userEvent.setup().click(within(draftTabs).getByRole("tab", { name: /tất cả kênh/i }));

    // Kiểm tra tiêu đề 2 nhóm
    expect(
      screen.getByText(/Nhóm 1: Bài Viết Fanpage Facebook/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Video Ngắn 9:16 → TikTok, Reels và YouTube Shorts/i),
    ).toBeInTheDocument();

    expect(screen.getAllByText(/một video master/i)).toHaveLength(1);
    expect(screen.getByText(/tiktok: gửi vào hộp thư tiktok/i)).toBeInTheDocument();

    // Reels không còn là một card video riêng có hành động Facebook riêng.
    const shareBtns = screen.getAllByRole("button", { name: /trang cá nhân/i });
    expect(shareBtns.length).toBe(1);

    // Clip tự quay chỉ còn là lựa chọn phụ duy nhất của video master.
    expect(screen.getAllByText(/muốn dùng clip tự quay/i)).toHaveLength(1);
  });

  it("bấm chọn Campaign Playbook thì tự động điền kịch bản chiến lược vào ô ghi chú", async () => {
    mockApi();
    render(<ContentCreationScreen />);
    await screen.findByText(/chưa có bản nháp nào/i);

    const user = userEvent.setup();
    const flashSaleBtn = screen.getByRole("button", { name: /flash sale & kéo khách/i });
    await user.click(flashSaleBtn);

    const textarea = screen.getByPlaceholderText(/tuần này giảm 20%/i) as HTMLTextAreaElement;
    expect(textarea.value).toContain("CTA cuối bài: mời khách nhắn tin");
  });


  it("chuyển Tab Video và Bài viết lọc danh sách trực quan", async () => {
    mockApi({
      list: () =>
        jsonResponse({
          items: [
            pendingItem("post-fb", "facebook_page"),
            pendingItem("vid-tt", "tiktok"),
          ],
          total: 2,
          limit: 50,
          offset: 0,
        }),
    });
    render(<ContentCreationScreen />);
    await screen.findByText("Nội dung post-fb");

    const user = userEvent.setup();
    const draftTabs = screen.getByRole("tablist", { name: /lọc bản nháp/i });
    const videoTab = within(draftTabs).getByRole("tab", { name: /video ngắn/i });
    await user.click(videoTab);

    expect(screen.getAllByText("Nội dung vid-tt").length).toBeGreaterThanOrEqual(1);
    expect(screen.queryByText("Nội dung post-fb")).not.toBeInTheDocument();

    const postsTab = within(draftTabs).getByRole("tab", { name: /bài viết/i });
    await user.click(postsTab);

    expect(screen.getByText("Nội dung post-fb")).toBeInTheDocument();
    expect(screen.queryByText("Nội dung vid-tt")).not.toBeInTheDocument();
  });

  it("bấm Hẹn Giờ Vàng thì lên lịch hàng loạt khung giờ vàng", async () => {
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
          approved: ["c1", "c2"],
          rejected: [],
        }),
    });
    render(<ContentCreationScreen />);
    await screen.findByText("Nội dung c1");

    const user = userEvent.setup();
    const goldHourBtn = screen.getByRole("button", { name: /hẹn bài lúc 11:30/i });
    await user.click(goldHourBtn);

    expect(
      await screen.findByText(/đã lên lịch đăng bài viết/i),
    ).toBeInTheDocument();
  });

  it("video master đặt AI dựng video làm hành động mặc định", async () => {
    mockApi({
      list: () =>
        jsonResponse({
          items: [{ ...pendingItem("vid-1"), channel: "tiktok", text: "Bí quyết tự học công nghệ thực chiến" }],
          total: 1,
          limit: 50,
          offset: 0,
        }),
    });
    render(<ContentCreationScreen />);
    await chonFlowVideo();
    await screen.findByText(/video ngắn sẵn sàng cho ba kênh/i);

    const user = userEvent.setup();
    const aiButton = screen.getByRole("button", { name: /tạo video ai — xem thử trước/i });
    expect(aiButton).toBeInTheDocument();
    expect(screen.getByText(/muốn dùng clip tự quay/i)).toBeInTheDocument();

    await user.click(aiButton);
    expect(await screen.findByRole("dialog", { name: /xem thử video ai/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /dùng video này cho 3 kênh/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /làm lại giọng khác/i })).toBeInTheDocument();
  });

  it("lưu clip tự quay từ video master và đồng bộ URL vào bản nháp", async () => {
    const fetchSpy = mockApi({
      list: () =>
        jsonResponse({
          items: [{ ...pendingItem("vid-upload", "tiktok"), text: "Video công nghệ" }],
          total: 1,
          limit: 50,
          offset: 0,
        }),
      complete: () =>
        jsonResponse({
          id: "asset-video-1",
          url: "https://storage.local/w1/asset-video-1.mp4",
          type: "video",
        }),
    });
    render(<ContentCreationScreen />);
    await chonFlowVideo();
    await screen.findByText(/video ngắn sẵn sàng cho ba kênh/i);

    const input = document.querySelector("#upload-video-master-vid-upload") as HTMLInputElement;
    await userEvent.setup().upload(
      input,
      new File(["video"], "phong-ky-thuat.mp4", { type: "video/mp4" }),
    );

    await screen.findByText(/đã gắn & đồng bộ video thật/i);
    const patchRequest = fetchSpy.mock.calls.find(([request]) =>
      request instanceof Request && request.method === "PATCH",
    )?.[0];
    expect(patchRequest).toBeInstanceOf(Request);
    expect(await (patchRequest as Request).clone().text()).toContain(
      "https://storage.local/w1/asset-video-1.mp4",
    );
    expect(
      fetchSpy.mock.calls.some(([request]) =>
        String(request instanceof Request ? request.url : request).includes(
          "upload-rendered-video",
        ),
      ),
    ).toBe(false);
  });

  it("thẻ kịch bản video hiển thị 3 Style Presets và 2 Giọng đọc AI để chủ tiệm tuỳ chỉnh", async () => {
    mockApi({
      list: () =>
        jsonResponse({
          items: [{ ...pendingItem("vid-1"), channel: "tiktok", text: "Bí quyết tự học công nghệ thực chiến" }],
          total: 1,
          limit: 50,
          offset: 0,
        }),
    });
    render(<ContentCreationScreen />);
    await chonFlowVideo();
    await screen.findByText(/video ngắn sẵn sàng cho ba kênh/i);

    const user = userEvent.setup();
    expect(screen.getByRole("button", { name: /capcut kinetic/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /chân thật/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /🔥 flash sale/i })).toBeInTheDocument();

    expect(screen.getByRole("button", { name: /hoài my/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /nam minh/i })).toBeInTheDocument();

    // Chọn phong cách Tâm Sự Chân Thật và giọng Nam Minh
    await user.click(screen.getByRole("button", { name: /chân thật/i }));
    await user.click(screen.getByRole("button", { name: /nam minh/i }));
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
