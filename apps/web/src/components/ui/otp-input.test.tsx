import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it } from "vitest";
import { OtpInput } from "./otp-input";

function ControlledOtp() {
  const [value, setValue] = useState("");
  return <OtpInput value={value} onChange={setValue} />;
}

describe("OtpInput", () => {
  it("advances focus to the next box after typing a digit", async () => {
    render(<ControlledOtp />);
    const boxes = screen.getAllByRole("textbox");

    await userEvent.type(boxes[0], "1");
    expect(boxes[0]).toHaveValue("1");
    expect(boxes[1]).toHaveFocus();
  });

  it("moves focus back on backspace when the box is empty", async () => {
    render(<ControlledOtp />);
    const boxes = screen.getAllByRole("textbox");

    await userEvent.type(boxes[0], "1");
    boxes[1].focus();
    await userEvent.keyboard("{Backspace}");

    expect(boxes[0]).toHaveFocus();
  });
});
