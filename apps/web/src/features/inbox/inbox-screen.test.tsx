import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { writeTokens } from "@/lib/auth/token-store";
import { InboxScreen } from "./inbox-screen";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

const inboxItem = {
  id: "inbox-1",
  workspace_id: "w1",
  platform: "facebook",
  external_thread_id: "thread-1",
  external_message_id: "message-1",
  author_name: "Minh Anh",
  content: "Shop còn lịch chiều nay không?",
  status: "drafted",
  ai_suggested_reply: "Dạ shop còn lịch lúc 15:00 ạ.",
  created_at: "2026-08-25T08:00:00Z",
  updated_at: "2026-08-25T08:00:00Z",
};

beforeEach(() => {
  writeTokens({
    accessToken: "at",
    refreshToken: "rt",
    activeWorkspaceId: "w1",
    needsOnboarding: false,
  });
});

afterEach(() => vi.restoreAllMocks());

describe("InboxScreen", () => {
  it("cho phép kiểm tra, sửa rồi chủ động gửi bản nháp", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(
      async (input: RequestInfo | URL, init?: RequestInit) => {
        const request = input instanceof Request ? input : new Request(String(input), init);
        const url = new URL(request.url);

        if (request.method === "GET" && url.pathname.endsWith("/inbox")) {
          return jsonResponse({ items: [inboxItem], total: 1 });
        }
        if (request.method === "POST" && url.pathname.endsWith("/inbox/inbox-1/reply")) {
          return jsonResponse({ ...inboxItem, status: "sent", ai_suggested_reply: "Dạ shop còn lịch lúc 16:00 ạ." });
        }
        return jsonResponse({ detail: "not found" }, 404);
      },
    );

    render(<InboxScreen />);

    // Danh sách bên trái hiện trước; phải mở hội thoại rồi mới có ô trả lời.
    fireEvent.click(await screen.findByText("Shop còn lịch chiều nay không?"));

    const draft = screen.getByLabelText(/Trả lời Minh Anh/);
    fireEvent.change(draft, { target: { value: "Dạ shop còn lịch lúc 16:00 ạ." } });
    fireEvent.click(screen.getByRole("button", { name: "Gửi trả lời" }));

    // Gửi xong thì ô soạn biến mất và câu vừa gửi thành bong bóng của tiệm —
    // `ai_suggested_reply` đã bị ghi đè bằng text thật ở `update_status`.
    await screen.findByText(/Havi gửi/);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));

    const replyRequest = fetchMock.mock.calls[1]?.[0];
    expect(replyRequest).toBeInstanceOf(Request);
    expect(await (replyRequest as Request).clone().json()).toEqual({
      text: "Dạ shop còn lịch lúc 16:00 ạ.",
    });
  });

  it("hai khách TRÙNG TÊN không bị gộp làm một hội thoại", async () => {
    // Gom luồng theo `recipient_id` chứ không theo tên hiển thị. Trùng tên trên
    // Facebook là chuyện chắc chắn xảy ra; gộp nhầm thì người trực chat đọc
    // lịch sử của người này rồi trả lời cho người kia.
    const huongA = { ...inboxItem, id: "a", recipient_id: "psid-a", content: "Còn lịch chiều nay không?" };
    const huongB = { ...inboxItem, id: "b", recipient_id: "psid-b", content: "Cho hỏi giá gói mặt?" };

    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse({ items: [huongA, huongB], total: 2 }),
    );

    render(<InboxScreen />);

    expect(await screen.findByText("Còn lịch chiều nay không?")).toBeInTheDocument();
    expect(screen.getByText("Cho hỏi giá gói mặt?")).toBeInTheDocument();
    // Cùng tên "Minh Anh" nhưng là hai người — hai dòng trong danh sách.
    expect(screen.getAllByText("Minh Anh")).toHaveLength(2);
  });

  it("cùng một khách nhắn nhiều lần thì vẫn là MỘT hội thoại", async () => {
    const lan1 = { ...inboxItem, id: "a", recipient_id: "psid-a", content: "Còn lịch chiều nay không?" };
    const lan2 = { ...inboxItem, id: "b", recipient_id: "psid-a", content: "Alo shop ơi" };

    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse({ items: [lan1, lan2], total: 2 }),
    );

    render(<InboxScreen />);

    await screen.findByText("Minh Anh");
    expect(screen.getAllByText("Minh Anh")).toHaveLength(1);
  });

  it("hiển thị trạng thái trống trung thực", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse({ items: [], total: 0 }));

    render(<InboxScreen />);

    expect(await screen.findByText("Chưa có hội thoại")).toBeInTheDocument();
    expect(screen.getByText(/Hội thoại mới từ các kênh/)).toBeInTheDocument();
  });
});
