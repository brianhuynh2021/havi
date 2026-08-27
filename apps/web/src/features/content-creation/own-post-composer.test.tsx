import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { LanguageProvider } from "@/lib/i18n/language-context";
import { OwnPostComposer } from "./own-post-composer";
import * as api from "./content-creation.api";

/**
 * Điều đáng test nhất ở đây không phải form gửi được, mà là **khung xem trước
 * không nói dối**: Facebook không render Markdown và cắt bài sau ~800 ký tự, nên
 * một preview hiện `**đậm**` thành chữ đậm sẽ khiến người dùng duyệt một thứ và
 * khách nhìn thấy một thứ khác.
 */
function preview(overrides: Partial<api.ContentPreview> = {}): api.ContentPreview {
  return {
    text: "Bài ngắn gọn.",
    media_url: null,
    char_count: 13,
    truncate_at: null,
    warnings: [],
    ...overrides,
  } as api.ContentPreview;
}

describe("OwnPostComposer", () => {
  beforeEach(() => {
    vi.spyOn(api, "previewContent").mockResolvedValue({ ok: true, data: preview() });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  function renderComposer(onCreated = vi.fn()) {
    render(
      <LanguageProvider>
        <OwnPostComposer channel="facebook_page" onCreated={onCreated} />
      </LanguageProvider>,
    );
  }

  it("nút gửi bị tắt khi chưa gõ gì", () => {
    renderComposer();
    expect(screen.getByRole("button", { name: /Đưa vào hàng chờ duyệt/i })).toBeDisabled();
  });

  it("hiện chữ nguyên văn, không render Markdown thành chữ đậm", async () => {
    vi.spyOn(api, "previewContent").mockResolvedValue({
      ok: true,
      data: preview({
        text: "**1. MIT dạy tư duy**",
        char_count: 21,
        warnings: [
          {
            code: "MARKDOWN_NOT_SUPPORTED",
            message: "Facebook không hiểu Markdown — **chữ đậm** sẽ hiện nguyên ký hiệu.",
            at_char: null,
          },
        ],
      }),
    });

    const user = userEvent.setup();
    renderComposer();
    await user.type(screen.getByLabelText(/Nội dung bài/i), "x");

    await waitFor(() => {
      expect(screen.getByText("**1. MIT dạy tư duy**")).toBeInTheDocument();
    });
    // Không có <strong>/<b> nào: dấu sao phải còn nguyên trên màn hình.
    expect(document.querySelector("strong")).toBeNull();
    expect(document.querySelector("b")).toBeNull();
    expect(screen.getByText(/Facebook không hiểu Markdown/i)).toBeInTheDocument();
  });

  it("cắt bài dài ở đúng chỗ Facebook cắt, và mở lại được", async () => {
    const long = "a".repeat(1000);
    vi.spyOn(api, "previewContent").mockResolvedValue({
      ok: true,
      data: preview({
        text: long,
        char_count: 1000,
        truncate_at: 800,
        warnings: [
          { code: "TRUNCATED", message: "Facebook chỉ hiện khoảng 800 ký tự đầu.", at_char: 800 },
        ],
      }),
    });

    const user = userEvent.setup();
    renderComposer();
    await user.type(screen.getByLabelText(/Nội dung bài/i), "x");

    const seeMore = await screen.findByRole("button", { name: /Xem thêm/i });
    // Chỉ 800 ký tự đầu được hiện — phần sau nằm sau "Xem thêm", như trên feed.
    expect(screen.getByText("a".repeat(800))).toBeInTheDocument();

    await user.click(seeMore);
    expect(screen.getByText(long)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Thu gọn/i })).toBeInTheDocument();
  });

  it("bài ngắn không hiện nút Xem thêm và không có cảnh báo nào", async () => {
    const user = userEvent.setup();
    renderComposer();
    await user.type(screen.getByLabelText(/Nội dung bài/i), "x");

    await waitFor(() => {
      expect(screen.getByText("Bài ngắn gọn.")).toBeInTheDocument();
    });
    expect(screen.queryByRole("button", { name: /Xem thêm/i })).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/Cảnh báo trước khi đăng/i)).not.toBeInTheDocument();
  });

  it("gửi xong thì gọi onCreated và xoá ô nhập", async () => {
    const onCreated = vi.fn();
    const item = { id: "item-1", text: "Bài của tôi" } as api.ContentItem;
    vi.spyOn(api, "createOwnItem").mockResolvedValue({ ok: true, data: item });

    const user = userEvent.setup();
    renderComposer(onCreated);
    const textarea = screen.getByLabelText(/Nội dung bài/i);
    await user.type(textarea, "Bài của tôi");
    await user.click(screen.getByRole("button", { name: /Đưa vào hàng chờ duyệt/i }));

    await waitFor(() => expect(onCreated).toHaveBeenCalledWith(item));
    expect(textarea).toHaveValue("");
  });

  it("lỗi từ server được hiện ra, không im lặng", async () => {
    vi.spyOn(api, "createOwnItem").mockResolvedValue({
      ok: false,
      message: "Không tìm thấy ảnh bạn chọn.",
    });

    const user = userEvent.setup();
    renderComposer();
    await user.type(screen.getByLabelText(/Nội dung bài/i), "Bài của tôi");
    await user.click(screen.getByRole("button", { name: /Đưa vào hàng chờ duyệt/i }));

    expect(await screen.findByText(/Không tìm thấy ảnh bạn chọn/i)).toBeInTheDocument();
  });
});
