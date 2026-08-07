import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { Button } from "./button";

describe("Button", () => {
  it("renders children and fires onClick", async () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Duyệt & đăng</Button>);

    const button = screen.getByRole("button", { name: "Duyệt & đăng" });
    await userEvent.click(button);

    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("does not fire onClick when disabled", async () => {
    const onClick = vi.fn();
    render(
      <Button onClick={onClick} disabled>
        Duyệt & đăng
      </Button>,
    );

    await userEvent.click(screen.getByRole("button"));

    expect(onClick).not.toHaveBeenCalled();
  });
});
