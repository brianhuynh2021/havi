import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ContentCreationScreen } from "./content-creation-screen";

const listPendingItems = vi.fn();
const approveAll = vi.fn();
const createJob = vi.fn();

vi.mock("./content-creation.api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("./content-creation.api")>();
  return {
    ...actual,
    listPendingItems: (...args: unknown[]) => listPendingItems(...args),
    approveAll: (...args: unknown[]) => approveAll(...args),
    createJob: (...args: unknown[]) => createJob(...args),
    uploadMedia: vi.fn(),
    dismissItem: vi.fn(),
    dismissAllItems: vi.fn(),
  };
});

vi.mock("./quota-banner", () => ({ QuotaBanner: () => null }));

const permissions = vi.fn();
vi.mock("@/lib/auth/use-permissions", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/auth/use-permissions")>();
  return { ...actual, usePermissions: () => permissions() };
});
vi.mock("@/features/video/video-branch", () => ({
  VideoBranch: () => <div data-testid="video-branch">nhánh video</div>,
}));
vi.mock("@/features/voice-note/voice-recorder-modal", () => ({
  VoiceRecorderModal: () => null,
}));

function draft(index: number) {
  return {
    id: `item-${index}`,
    job_id: "job-1",
    channel: "facebook_page",
    kind: "post",
    text: `Câu chuyện số ${index}`,
    media_url: null,
    media_note: null,
    status: "pending_approval",
    scheduled_at: null,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  listPendingItems.mockResolvedValue({ ok: true, data: [] });
  // Mặc định: Chủ workspace, duyệt được.
  permissions.mockReturnValue({
    known: true,
    role: "owner",
    permissions: ["draft_content", "approve_content"],
    can: () => true,
  });
});

describe("ContentCreationScreen — một tab, một luồng", () => {
  it("bắt đầu ở nhánh Bài viết và chỉ hiện một nhánh mỗi lúc", async () => {
    render(<ContentCreationScreen />);
    await waitFor(() => expect(listPendingItems).toHaveBeenCalled());

    expect(screen.getByRole("tab", { name: /Bài viết/ })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(screen.queryByTestId("video-branch")).toBeNull();
  });

  it("chọn Video thì rẽ sang nhánh video, không mở tab khác", async () => {
    render(<ContentCreationScreen />);
    await waitFor(() => expect(listPendingItems).toHaveBeenCalled());

    await userEvent.click(screen.getByRole("tab", { name: /Video/ }));

    expect(await screen.findByTestId("video-branch")).toBeInTheDocument();
    // Nhánh bài viết biến mất — không phải hai luồng chạy song song.
    expect(screen.queryByText(/Kể cho Havi nghe/)).toBeNull();
  });

  it("nhiều bản nháp thì hiện bảng xem trước lịch, mỗi bài một dòng", async () => {
    listPendingItems.mockResolvedValue({
      ok: true,
      data: [draft(1), draft(2), draft(3), draft(4), draft(5)],
    });

    render(<ContentCreationScreen />);
    await screen.findByRole("button", { name: /Duyệt & xếp lịch 5 bài/ });

    const rows = document.querySelectorAll("ol li");
    expect(rows).toHaveLength(5);
  });

  it("mặc định là rải lịch, không phải đăng hết ngay", async () => {
    listPendingItems.mockResolvedValue({ ok: true, data: [draft(1), draft(2)] });
    approveAll.mockResolvedValue({ ok: true, data: { approved: ["item-1", "item-2"], rejected: [] } });

    render(<ContentCreationScreen />);
    await userEvent.click(await screen.findByRole("button", { name: /Duyệt & xếp lịch/ }));

    await waitFor(() => expect(approveAll).toHaveBeenCalled());
    const [, publishNow, postsPerDay] = approveAll.mock.calls[0];
    expect(publishNow).toBe(false);
    expect(postsPerDay).toBe(1);
  });

  it("đổi mật độ sang 2 bài/ngày thì gửi đúng con số đó cho backend", async () => {
    listPendingItems.mockResolvedValue({
      ok: true,
      data: [draft(1), draft(2), draft(3), draft(4)],
    });
    approveAll.mockResolvedValue({ ok: true, data: { approved: [], rejected: [] } });

    render(<ContentCreationScreen />);
    await userEvent.click(await screen.findByRole("button", { name: "2 bài/ngày" }));
    await userEvent.click(screen.getByRole("button", { name: /Duyệt & xếp lịch 4 bài/ }));

    await waitFor(() => expect(approveAll).toHaveBeenCalled());
    expect(approveAll.mock.calls[0][2]).toBe(2);
  });

  it("chọn đăng hết ngay với nhiều bài thì cảnh báo trông như spam", async () => {
    listPendingItems.mockResolvedValue({ ok: true, data: [draft(1), draft(2), draft(3)] });

    render(<ContentCreationScreen />);
    await userEvent.click(await screen.findByRole("button", { name: /Đăng hết ngay/ }));

    expect(await screen.findByText(/spam/)).toBeInTheDocument();
  });

  it("một bài duy nhất thì không cảnh báo spam", async () => {
    listPendingItems.mockResolvedValue({ ok: true, data: [draft(1)] });

    render(<ContentCreationScreen />);
    await userEvent.click(await screen.findByRole("button", { name: /Đăng hết ngay/ }));

    expect(screen.queryByText(/spam/)).toBeNull();
  });

  it("thứ tự bài gửi đi đúng thứ tự đang hiện trên màn hình", async () => {
    listPendingItems.mockResolvedValue({ ok: true, data: [draft(1), draft(2), draft(3)] });
    approveAll.mockResolvedValue({ ok: true, data: { approved: [], rejected: [] } });

    render(<ContentCreationScreen />);
    await userEvent.click(await screen.findByRole("button", { name: /Duyệt & xếp lịch/ }));

    await waitFor(() => expect(approveAll).toHaveBeenCalled());
    expect(approveAll.mock.calls[0][0]).toEqual(["item-1", "item-2", "item-3"]);
  });

  it("không có bản nháp nào thì không có chỗ nào bấm đăng được", async () => {
    render(<ContentCreationScreen />);
    await waitFor(() => expect(listPendingItems).toHaveBeenCalled());

    expect(screen.queryByRole("button", { name: /Duyệt/ })).toBeNull();
  });

  it("vai Người soạn KHÔNG thấy nút duyệt, nhưng vẫn thấy danh sách", async () => {
    permissions.mockReturnValue({
      known: true,
      role: "marketer",
      permissions: ["draft_content"],
      can: (p: string) => p === "draft_content",
    });
    listPendingItems.mockResolvedValue({ ok: true, data: [draft(1), draft(2)] });

    render(<ContentCreationScreen />);

    expect(await screen.findByText(/2 bài này đang chờ duyệt/)).toBeInTheDocument();
    expect(screen.getByText(/Người soạn/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Duyệt/ })).toBeNull();
    // Vẫn thấy nội dung để bàn với người duyệt.
    expect(document.querySelectorAll("ol li")).toHaveLength(2);
  });

  it("chưa biết vai thì VẪN hiện nút — tránh nháy và tránh chặn nhầm", async () => {
    permissions.mockReturnValue({
      known: false,
      role: null,
      permissions: [],
      can: () => true,
    });
    listPendingItems.mockResolvedValue({ ok: true, data: [draft(1)] });

    render(<ContentCreationScreen />);
    expect(await screen.findByRole("button", { name: /Duyệt & xếp lịch/ })).toBeInTheDocument();
  });
});
