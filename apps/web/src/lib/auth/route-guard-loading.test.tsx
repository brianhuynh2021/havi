import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { RouteGuard } from "./route-guard";

const replace = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace }),
}));

vi.mock("./session", () => ({
  useSession: () => ({
    status: "loading",
    needsOnboarding: false,
  }),
}));

describe("RouteGuard while session is hydrating", () => {
  beforeEach(() => replace.mockClear());

  it("does not flash protected or guest content before auth is known", () => {
    render(
      <RouteGuard require="guest">
        <p>nội dung</p>
      </RouteGuard>,
    );

    expect(screen.queryByText("nội dung")).not.toBeInTheDocument();
    expect(replace).not.toHaveBeenCalled();
  });
});
