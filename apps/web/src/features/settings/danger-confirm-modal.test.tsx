import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { DangerConfirmModal } from "./danger-confirm-modal";

describe("DangerConfirmModal", () => {
  it("hiển thị đúng thông tin cảnh báo và retention hooks khi mở", () => {
    render(
      <DangerConfirmModal
        isOpen={true}
        type="workspace"
        targetName="Spa Lan Anh"
        isDeleting={false}
        onClose={vi.fn()}
        onConfirm={vi.fn()}
      />,
    );

    expect(screen.getByText(/Xác nhận xoá tiệm “Spa Lan Anh”/i)).toBeInTheDocument();
    expect(screen.getByText(/Bạn sẽ mất các quyền lợi sau/i)).toBeInTheDocument();
    expect(screen.getByText(/Mất toàn bộ cấu hình giọng văn/i)).toBeInTheDocument();
    expect(screen.getByText(/0984 883 750/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Giữ Lại Tiệm/i })).toBeInTheDocument();
  });

  it("khóa nút xoá cho đến khi người dùng gõ đúng từ khóa xác nhận", async () => {
    const onConfirm = vi.fn();
    render(
      <DangerConfirmModal
        isOpen={true}
        type="workspace"
        targetName="Spa Lan Anh"
        isDeleting={false}
        onClose={vi.fn()}
        onConfirm={onConfirm}
      />,
    );

    const user = userEvent.setup();
    const deleteBtn = screen.getByRole("button", { name: /Xác nhận xoá vĩnh viễn/i });
    expect(deleteBtn).toBeDisabled();

    const input = screen.getByPlaceholderText(/Gõ “XOATIEM”/i);
    await user.type(input, "sai keyword");
    expect(deleteBtn).toBeDisabled();

    await user.clear(input);
    await user.type(input, "XOATIEM");
    expect(deleteBtn).not.toBeDisabled();

    await user.click(deleteBtn);
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it("hỗ trợ đóng modal khi bấm nút Giữ lại hoặc nút X", async () => {
    const onClose = vi.fn();
    render(
      <DangerConfirmModal
        isOpen={true}
        type="account"
        isDeleting={false}
        onClose={onClose}
        onConfirm={vi.fn()}
      />,
    );

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /Giữ Lại Tài Khoản/i }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
