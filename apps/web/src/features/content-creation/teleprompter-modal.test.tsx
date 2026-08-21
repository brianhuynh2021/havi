import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TeleprompterModal } from "./teleprompter-modal";

describe("TeleprompterModal (Máy Nhắc Chữ 30s)", () => {
  it("không hiển thị khi isOpen = false", () => {
    render(
      <TeleprompterModal
        isOpen={false}
        onClose={vi.fn()}
        title="Kịch bản TikTok"
        hookText="3 BÍ QUYẾT TỰ HỌC NGHỀ"
        cameraAngle="Cầm máy quay cận cảnh"
        scriptText="Xin chào các bạn, hôm nay mình chia sẻ..."
        onUploadVideo={vi.fn()}
      />,
    );
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("hiển thị đầy đủ Hook 3s, Góc máy gợi ý và Lời thoại khi isOpen = true", () => {
    render(
      <TeleprompterModal
        isOpen={true}
        onClose={vi.fn()}
        title="Kịch bản TikTok"
        hookText="3 BÍ QUYẾT TỰ HỌC NGHỀ"
        cameraAngle="Cầm máy quay cận cảnh"
        scriptText="Xin chào các bạn, hôm nay mình chia sẻ..."
        onUploadVideo={vi.fn()}
      />,
    );
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText(/3 BÍ QUYẾT TỰ HỌC NGHỀ/i)).toBeInTheDocument();
    expect(screen.getByText(/Cầm máy quay cận cảnh/i)).toBeInTheDocument();
    expect(screen.getByText(/Xin chào các bạn/i)).toBeInTheDocument();
  });

  it("cho phép đổi cỡ chữ A- và A+", async () => {
    render(
      <TeleprompterModal
        isOpen={true}
        onClose={vi.fn()}
        title="Kịch bản TikTok"
        hookText="3 BÍ QUYẾT TỰ HỌC NGHỀ"
        cameraAngle="Cầm máy quay cận cảnh"
        scriptText="Xin chào các bạn, hôm nay mình chia sẻ..."
        onUploadVideo={vi.fn()}
      />,
    );
    const user = userEvent.setup();
    const increaseBtn = screen.getByTitle(/tăng cỡ chữ/i);
    const decreaseBtn = screen.getByTitle(/giảm cỡ chữ/i);

    await user.click(increaseBtn);
    await user.click(decreaseBtn);
    expect(screen.getByText(/Xin chào các bạn/i)).toBeInTheDocument();
  });

  it("bấm nút đóng thì gọi onClose", async () => {
    const onClose = vi.fn();
    render(
      <TeleprompterModal
        isOpen={true}
        onClose={onClose}
        title="Kịch bản TikTok"
        hookText="3 BÍ QUYẾT TỰ HỌC NGHỀ"
        cameraAngle="Cầm máy quay cận cảnh"
        scriptText="Xin chào các bạn, hôm nay mình chia sẻ..."
        onUploadVideo={vi.fn()}
      />,
    );
    const user = userEvent.setup();
    const closeBtn = screen.getByRole("button", { name: /đóng máy nhắc chữ/i });
    await user.click(closeBtn);
    expect(onClose).toHaveBeenCalled();
  });

  it("bấm bắt đầu cuộn chữ thì kích hoạt đếm ngược 3s", async () => {
    render(
      <TeleprompterModal
        isOpen={true}
        onClose={vi.fn()}
        title="Kịch bản TikTok"
        hookText="3 BÍ QUYẾT TỰ HỌC NGHỀ"
        cameraAngle="Cầm máy quay cận cảnh"
        scriptText="Xin chào các bạn, hôm nay mình chia sẻ..."
        onUploadVideo={vi.fn()}
      />,
    );
    const user = userEvent.setup();
    const playBtn = screen.getByRole("button", { name: /bắt đầu cuộn chữ/i });
    await user.click(playBtn);

    // Hiển thị đếm ngược số 3
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByText(/chuẩn bị nhìn vào camera/i)).toBeInTheDocument();
  });
});
