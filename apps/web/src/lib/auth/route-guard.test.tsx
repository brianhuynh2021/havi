import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { RouteGuard } from "./route-guard";
import { SessionProvider } from "./session";
import { writeTokens } from "./token-store";

const replace = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, push: vi.fn() }),
}));

function renderGuard(require: "app" | "onboarding" | "guest") {
  return render(
    <SessionProvider>
      <RouteGuard require={require}>
        <p>nội dung</p>
      </RouteGuard>
    </SessionProvider>,
  );
}

describe("RouteGuard", () => {
  beforeEach(() => {
    window.localStorage.clear();
    replace.mockClear();
  });

  it("chưa đăng nhập mà vào app thì bị đá về đăng nhập", async () => {
    renderGuard("app");
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/login"));
    expect(screen.queryByText("nội dung")).not.toBeInTheDocument();
  });

  it("đã đăng nhập và đã onboarding thì render nội dung", async () => {
    writeTokens({
      accessToken: "a",
      refreshToken: "r",
      activeWorkspaceId: "w1",
      needsOnboarding: false,
    });
    renderGuard("app");
    await waitFor(() =>
      expect(screen.getByText("nội dung")).toBeInTheDocument(),
    );
    expect(replace).not.toHaveBeenCalled();
  });

  it("chưa onboarding thì bị đưa về onboarding, không cho vào app", async () => {
    writeTokens({
      accessToken: "a",
      refreshToken: "r",
      activeWorkspaceId: null,
      needsOnboarding: true,
    });
    renderGuard("app");
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/onboarding"));
    expect(screen.queryByText("nội dung")).not.toBeInTheDocument();
  });

  it("chưa onboarding thì vẫn vào được màn onboarding", async () => {
    writeTokens({
      accessToken: "a",
      refreshToken: "r",
      activeWorkspaceId: null,
      needsOnboarding: true,
    });
    renderGuard("onboarding");
    await waitFor(() =>
      expect(screen.getByText("nội dung")).toBeInTheDocument(),
    );
    expect(replace).not.toHaveBeenCalled();
  });

  it("đã đăng nhập rồi thì không cần xem lại màn đăng nhập", async () => {
    writeTokens({
      accessToken: "a",
      refreshToken: "r",
      activeWorkspaceId: "w1",
      needsOnboarding: false,
    });
    renderGuard("guest");
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/app"));
  });

  it("khách vãng lai xem được màn đăng nhập", async () => {
    renderGuard("guest");
    await waitFor(() =>
      expect(screen.getByText("nội dung")).toBeInTheDocument(),
    );
    expect(replace).not.toHaveBeenCalled();
  });
});
