import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ToastContainer, type ToastItem } from "./toast";
import styles from "./toast.module.css";

describe("ToastContainer", () => {
  it("không render gì khi danh sách toasts rỗng", () => {
    const { container } = render(<ToastContainer toasts={[]} onDismiss={vi.fn()} />);
    expect(container.firstChild).toBeNull();
  });

  it("render toast thành công với icon mặc định 🎉 và không lặp icon", () => {
    const toasts: ToastItem[] = [
      {
        id: "t1",
        type: "success",
        title: "Havi đã sáng tạo xong bài mới!",
        description: "Đã nạp vào danh sách bên dưới.",
      },
    ];

    render(<ToastContainer toasts={toasts} onDismiss={vi.fn()} />);

    const toastElement = screen.getByRole("status");
    expect(toastElement).toBeInTheDocument();
    expect(screen.getByText("Havi đã sáng tạo xong bài mới!")).toBeInTheDocument();
    expect(screen.getByText("Đã nạp vào danh sách bên dưới.")).toBeInTheDocument();
    expect(screen.getByText("🎉")).toBeInTheDocument();
  });

  it("render toast loading với spinner", () => {
    const toasts: ToastItem[] = [
      {
        id: "t2",
        type: "loading",
        title: "Havi đang viết bài cho tiệm...",
      },
    ];

    const { container } = render(<ToastContainer toasts={toasts} onDismiss={vi.fn()} />);
    expect(screen.getByText("Havi đang viết bài cho tiệm...")).toBeInTheDocument();
    expect(
      container.querySelector(`.${styles.spinner}`) ||
        container.querySelector("span[aria-hidden='true']")
    ).toBeInTheDocument();
  });

  it("render toast tùy chỉnh icon khi được truyền", () => {
    const toasts: ToastItem[] = [
      {
        id: "t3",
        type: "success",
        icon: "🎙️",
        title: "Đã chèn giọng nói vào ô ghi chú",
      },
    ];

    render(<ToastContainer toasts={toasts} onDismiss={vi.fn()} />);
    expect(screen.getByText("🎙️")).toBeInTheDocument();
    expect(screen.getByText("Đã chèn giọng nói vào ô ghi chú")).toBeInTheDocument();
  });

  it("gọi onDismiss khi bấm nút đóng", async () => {
    const user = userEvent.setup();
    const handleDismiss = vi.fn();
    const toasts: ToastItem[] = [
      {
        id: "t-close",
        type: "info",
        title: "Thông báo kiểm tra",
      },
    ];

    render(<ToastContainer toasts={toasts} onDismiss={handleDismiss} />);
    const closeBtn = screen.getByRole("button", { name: "Đóng thông báo" });
    await user.click(closeBtn);

    expect(handleDismiss).toHaveBeenCalledWith("t-close");
  });
});
