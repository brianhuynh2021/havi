import { describe, expect, it } from "vitest";
import { missingCapabilities } from "./connections.api";
import type { components } from "@/lib/api-client/schema";

type PlatformConnection = components["schemas"]["PlatformConnection"];

function connection(capabilities: string[]): PlatformConnection {
  return {
    workspace_id: "11111111-1111-1111-1111-111111111111",
    platform: "facebook",
    status: "connected",
    capabilities,
  } as PlatformConnection;
}

describe("missingCapabilities", () => {
  it("không nói gì khi kênh đủ quyền", () => {
    expect(
      missingCapabilities(
        connection([
          "publish_post",
          "reply_comment",
          "reply_message",
          "receive_inbox",
        ]),
      ),
    ).toEqual([]);
  });

  it("nêu đúng tính năng bị tắt khi thiếu quyền Messenger", () => {
    // Đây là ca chính khiến cả tính năng này tồn tại: tiệm không dùng Messenger
    // vẫn nối được kênh, chỉ mất đúng phần trả lời tin nhắn.
    const missing = missingCapabilities(
      connection(["publish_post", "reply_comment", "receive_inbox"]),
    );
    expect(missing).toEqual(["Trả lời tin nhắn"]);
  });

  it("không hiện gì khi kênh chưa nối", () => {
    // Chưa nối thì huy hiệu "Chưa kết nối" đã nói hết; liệt kê thêm bốn tính
    // năng thiếu chỉ làm nhiễu.
    expect(missingCapabilities(undefined)).toEqual([]);
  });

  it("giữ thứ tự ổn định để UI không nhảy giữa hai lần tải", () => {
    const missing = missingCapabilities(connection([]));
    expect(missing).toEqual([
      "Đăng bài",
      "Trả lời bình luận",
      "Trả lời tin nhắn",
      "Nhận tin về Hộp thư",
    ]);
  });
});
