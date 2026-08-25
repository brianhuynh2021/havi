import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { VideoBranch } from "./video-branch";

const listVideoPosts = vi.fn();
const createVideoPost = vi.fn();
const approveVideoPost = vi.fn();
const cancelVideoPost = vi.fn();
const uploadMedia = vi.fn();

vi.mock("./video-posts.api", () => ({
  listVideoPosts: (...args: unknown[]) => listVideoPosts(...args),
  createVideoPost: (...args: unknown[]) => createVideoPost(...args),
  approveVideoPost: (...args: unknown[]) => approveVideoPost(...args),
  cancelVideoPost: (...args: unknown[]) => cancelVideoPost(...args),
}));

vi.mock("@/features/content-creation/content-creation.api", () => ({
  uploadMedia: (...args: unknown[]) => uploadMedia(...args),
  mediaTypeOf: (file: File) => (file.type.startsWith("video/") ? "video" : "image"),
}));

function clipAsset(overrides: Record<string, unknown> = {}) {
  return {
    id: "asset-1",
    url: "https://storage.havi.vn/clip.mp4",
    // Kích thước pixel thật, không phải nhãn: khung hình giờ tính từ đây.
    width: 720,
    height: 1648,
    aspect_ratio: "720:1648",
    duration_seconds: 20,
    has_audio: true,
    eligible_channels: ["reels", "tiktok"],
    ...overrides,
  };
}

async function uploadAClip(asset = clipAsset()) {
  uploadMedia.mockResolvedValue({ ok: true, data: asset });
  const input = document.querySelector('input[type="file"]') as HTMLInputElement;
  const file = new File(["x"], "clip.mp4", { type: "video/mp4" });
  await userEvent.upload(input, file);
}

beforeEach(() => {
  vi.clearAllMocks();
  listVideoPosts.mockResolvedValue({ ok: true, data: [] });
  globalThis.URL.createObjectURL = vi.fn(() => "blob:preview");
  globalThis.URL.revokeObjectURL = vi.fn();
});

describe("VideoBranch (nhánh Video của luồng Đăng bài)", () => {
  it("không hiện bất kỳ công cụ biên tập nào — Havi không phải CapCut", async () => {
    render(<VideoBranch />);
    await waitFor(() => expect(listVideoPosts).toHaveBeenCalled());

    const body = document.body.textContent ?? "";
    for (const editingWord of ["Cắt", "Ghép", "Phụ đề", "Hiệu ứng", "Nhạc nền", "Dựng"]) {
      expect(body).not.toContain(editingWord);
    }
  });

  it("sau khi tải clip lên thì nói ngay clip đăng được kênh nào", async () => {
    render(<VideoBranch />);
    await waitFor(() => expect(listVideoPosts).toHaveBeenCalled());

    await uploadAClip();

    expect(await screen.findByText(/Facebook Reels: đăng được/)).toBeInTheDocument();
    expect(screen.getByText(/YouTube Shorts: chưa hợp/)).toBeInTheDocument();
    // 720×1648 phải đọc ra "khung dọc 20.6:9", không phải "720:1648".
    expect(screen.getByText(/khung dọc 20.6:9/)).toBeInTheDocument();
  });

  it("clip quay ngang thì bảng kênh báo chưa hợp cả ba", async () => {
    render(<VideoBranch />);
    await waitFor(() => expect(listVideoPosts).toHaveBeenCalled());

    await uploadAClip(
      clipAsset({ width: 1920, height: 1080, aspect_ratio: "16:9", eligible_channels: [] }),
    );

    expect(await screen.findByText(/Facebook Reels: chưa hợp/)).toBeInTheDocument();
    expect(screen.getByText(/khung ngang 16:9/)).toBeInTheDocument();
  });

  it("backend từ chối clip thì hiện HẾT lý do, không chỉ lý do đầu", async () => {
    render(<VideoBranch />);
    await waitFor(() => expect(listVideoPosts).toHaveBeenCalled());
    await uploadAClip();

    createVideoPost.mockResolvedValue({
      ok: false,
      message:
        "Facebook Reels cần khung dọc hoặc vuông, video này là khung ngang 16:9. " +
        "Facebook Reels chỉ nhận video tối đa 90 giây, video này 120 giây",
    });

    await userEvent.click(screen.getByRole("button", { name: /Đưa vào hàng chờ duyệt/ }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/khung ngang 16:9/);
    expect(alert).toHaveTextContent(/tối đa 90 giây/);
    // Hai lý do là hai dòng riêng, không phải một câu dài dính liền.
    expect(alert.querySelectorAll("li")).toHaveLength(2);
  });

  it("lý do cũ biến mất khi chọn clip khác", async () => {
    render(<VideoBranch />);
    await waitFor(() => expect(listVideoPosts).toHaveBeenCalled());
    await uploadAClip();

    createVideoPost.mockResolvedValue({ ok: false, message: "Clip quay ngang" });
    await userEvent.click(screen.getByRole("button", { name: /Đưa vào hàng chờ duyệt/ }));
    expect(await screen.findByRole("alert")).toBeInTheDocument();

    await uploadAClip();
    await waitFor(() => expect(screen.queryByRole("alert")).toBeNull());
  });

  it("video đang chờ xác nhận KHÔNG được hiện là đã đăng", async () => {
    listVideoPosts.mockResolvedValue({
      ok: true,
      data: [
        {
          id: "post-1",
          workspace_id: "ws-1",
          caption: "Ưu đãi tháng 8",
          channel: "reels",
          status: "verifying",
          source_media_id: "asset-1",
          error_message: null,
          published_at: null,
          created_at: new Date().toISOString(),
        },
      ],
    });

    render(<VideoBranch />);

    expect(await screen.findByText(/chờ xác nhận/)).toBeInTheDocument();
    expect(document.body.textContent).not.toContain("Đã lên Trang");
  });

  it("video đã gửi đi thì không còn nút duyệt hay huỷ", async () => {
    listVideoPosts.mockResolvedValue({
      ok: true,
      data: [
        {
          id: "post-1",
          workspace_id: "ws-1",
          caption: "Clip lớp Robot",
          channel: "reels",
          status: "published",
          source_media_id: "asset-1",
          error_message: null,
          published_at: new Date().toISOString(),
          created_at: new Date().toISOString(),
        },
      ],
    });

    render(<VideoBranch />);
    await screen.findByText("Đã lên Trang");

    expect(screen.queryByRole("button", { name: /Duyệt & đăng/ })).toBeNull();
    expect(screen.queryByRole("button", { name: /^Huỷ$/ })).toBeNull();
  });

  it("duyệt cả loạt thì mỗi clip nhận một giờ khác nhau, không dồn một lúc", async () => {
    const clips = ["Clip thứ nhất", "Clip thứ hai", "Clip thứ ba"].map((caption, index) => ({
      id: `post-${index + 1}`,
      workspace_id: "ws-1",
      caption,
      channel: "reels" as const,
      status: "ready_for_review" as const,
      source_media_id: "asset-1",
      scheduled_at: null,
      error_message: null,
      published_at: null,
      created_at: new Date(Date.now() + index * 1000).toISOString(),
    }));
    listVideoPosts.mockResolvedValue({ ok: true, data: clips });
    approveVideoPost.mockImplementation(async (id: string) => ({
      ok: true,
      data: {
        post: { ...clips.find((c) => c.id === id)!, status: "approved" },
        queuedForPublish: false,
      },
    }));

    render(<VideoBranch />);
    await userEvent.click(
      await screen.findByRole("button", { name: /Duyệt & xếp lịch 3 video/ }),
    );

    await waitFor(() => expect(approveVideoPost).toHaveBeenCalledTimes(3));

    const times = approveVideoPost.mock.calls.map(([, when]) => when as string);
    expect(new Set(times).size).toBe(3);

    const days = times.map((t) => new Date(t).toDateString());
    expect(new Set(days).size).toBe(3);
  });

  it("clip tải lên trước là câu chuyện của ngày trước", async () => {
    const older = {
      id: "post-old",
      workspace_id: "ws-1",
      caption: "Clip cũ hơn",
      channel: "reels" as const,
      status: "ready_for_review" as const,
      source_media_id: "asset-1",
      scheduled_at: null,
      error_message: null,
      published_at: null,
      created_at: "2026-08-20T10:00:00Z",
    };
    const newer = { ...older, id: "post-new", caption: "Clip mới hơn", created_at: "2026-08-24T10:00:00Z" };
    // API trả mới nhất trước; UI phải đảo lại để thứ tự lên bài đúng.
    listVideoPosts.mockResolvedValue({ ok: true, data: [newer, older] });
    approveVideoPost.mockImplementation(async (id: string) => ({
      ok: true,
      data: { post: { ...older, id, status: "approved" }, queuedForPublish: false },
    }));

    render(<VideoBranch />);
    await userEvent.click(
      await screen.findByRole("button", { name: /Duyệt & xếp lịch 2 video/ }),
    );
    await waitFor(() => expect(approveVideoPost).toHaveBeenCalledTimes(2));

    expect(approveVideoPost.mock.calls[0][0]).toBe("post-old");
    expect(approveVideoPost.mock.calls[1][0]).toBe("post-new");
  });

  it("chọn đăng ngay thì không gửi kèm giờ hẹn nào", async () => {
    listVideoPosts.mockResolvedValue({
      ok: true,
      data: [
        {
          id: "post-1",
          workspace_id: "ws-1",
          caption: "Clip lớp Robot",
          channel: "reels" as const,
          status: "ready_for_review" as const,
          source_media_id: "asset-1",
          scheduled_at: null,
          error_message: null,
          published_at: null,
          created_at: new Date().toISOString(),
        },
      ],
    });
    approveVideoPost.mockResolvedValue({
      ok: true,
      data: { post: { id: "post-1", status: "approved" }, queuedForPublish: true },
    });

    render(<VideoBranch />);
    await userEvent.click(await screen.findByRole("button", { name: /Đăng hết ngay/ }));
    await userEvent.click(screen.getByRole("button", { name: /Duyệt & đăng 1 video ngay/ }));

    await waitFor(() => expect(approveVideoPost).toHaveBeenCalled());
    expect(approveVideoPost.mock.calls[0][1]).toBeNull();
  });

  it("bảng xem trước hiện đúng số dòng bằng số clip chờ duyệt", async () => {
    listVideoPosts.mockResolvedValue({
      ok: true,
      data: [1, 2, 3, 4].map((n) => ({
        id: `post-${n}`,
        workspace_id: "ws-1",
        caption: `Clip ${n}`,
        channel: "reels" as const,
        status: "ready_for_review" as const,
        source_media_id: "asset-1",
        scheduled_at: null,
        error_message: null,
        published_at: null,
        created_at: new Date().toISOString(),
      })),
    });

    render(<VideoBranch />);
    await screen.findByRole("button", { name: /Duyệt & xếp lịch 4 video/ });

    const rows = document.querySelectorAll("ol li");
    expect(rows).toHaveLength(4);
  });
});
