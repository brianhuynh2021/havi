import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { LanguageProvider } from "@/lib/i18n/language-context";
import { SessionProvider } from "@/lib/auth/session";
import { writeTokens } from "@/lib/auth/token-store";
import { AppNav, isActive } from "./app-nav";
import { AppShell } from "./app-shell";
import { MobileAdminSheet } from "./mobile-admin-sheet";
import * as dashboardApi from "@/features/dashboard/dashboard.api";

let currentPath = "/app";

vi.mock("next/navigation", () => ({
  usePathname: () => currentPath,
  useRouter: () => ({ replace: vi.fn(), push: vi.fn(), prefetch: vi.fn() }),
}));

function jsonSummary(overrides: Partial<dashboardApi.DashboardContentSummary> = {}): dashboardApi.DashboardContentSummary {
  return {
    drafts: 0,
    pending_approval: 0,
    scheduled: 0,
    published: 0,
    failed: 0,
    broken_connections: 0,
    unhandled_inbox: 0,
    total_connections: 0,
    ...overrides,
  };
}

describe("Navigation & AppNav System", () => {
  beforeEach(() => {
    currentPath = "/app";
    window.localStorage.clear();
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: vi.fn().mockImplementation((query) => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    });
    vi.spyOn(dashboardApi, "fetchDashboardSummary").mockResolvedValue({
      ok: true,
      data: jsonSummary(),
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("isActive helper", () => {
    it("đánh dấu /app chỉ khi ở /app hoặc /", () => {
      expect(isActive("/app", "/app")).toBe(true);
      expect(isActive("/", "/app")).toBe(true);
      expect(isActive("/app/content", "/app")).toBe(false);
      expect(isActive("/app/settings", "/app")).toBe(false);
    });

    it("đánh dấu /app/content active khi ở /app/content hoặc /app/media", () => {
      expect(isActive("/app/content", "/app/content")).toBe(true);
      expect(isActive("/app/content/create", "/app/content")).toBe(true);
      expect(isActive("/app/media", "/app/content")).toBe(true);
      expect(isActive("/app/media/upload", "/app/content")).toBe(true);
      expect(isActive("/app/inbox", "/app/content")).toBe(false);
    });

    it("đánh dấu route con cho các mục khác", () => {
      expect(isActive("/app/calendar", "/app/calendar")).toBe(true);
      expect(isActive("/app/calendar/week", "/app/calendar")).toBe(true);
      expect(isActive("/app/inbox", "/app/inbox")).toBe(true);
      expect(isActive("/app/inbox/convo-1", "/app/inbox")).toBe(true);
      expect(isActive("/app/settings", "/app/settings")).toBe(true);
      expect(isActive("/app/settings", "/app/team")).toBe(false);
    });
  });

  describe("Desktop Navigation", () => {
    it("chỉ hiển thị đúng 4 mục chính và nút Quản trị khi mở lần đầu (Quản trị đóng)", async () => {
      render(
        <LanguageProvider>
          <AppNav variant="desktop" />
        </LanguageProvider>
      );

      // 4 mục chính phải hiển thị
      expect(screen.getByRole("link", { name: /Việc cần làm/i })).toBeInTheDocument();
      expect(screen.getByRole("link", { name: /Nội dung/i })).toBeInTheDocument();
      expect(screen.getByRole("link", { name: /Lịch đăng/i })).toBeInTheDocument();
      expect(screen.getByRole("link", { name: /Hội thoại/i })).toBeInTheDocument();

      // Nút toggle Quản trị
      const adminToggle = screen.getByRole("button", { name: /Quản trị/i });
      expect(adminToggle).toBeInTheDocument();
      expect(adminToggle).toHaveAttribute("aria-expanded", "false");

      // 7 mục quản trị chưa xuất hiện
      expect(screen.queryByRole("link", { name: /Kênh kết nối/i })).not.toBeInTheDocument();
      expect(screen.queryByRole("link", { name: /Cài đặt/i })).not.toBeInTheDocument();
      expect(screen.queryByRole("link", { name: /Đội ngũ/i })).not.toBeInTheDocument();
    });

    it("mở Quản trị sẽ hiển thị đủ 7 mục quản trị phụ và ghi nhớ vào localStorage", async () => {
      const user = userEvent.setup();
      render(
        <LanguageProvider>
          <AppNav variant="desktop" />
        </LanguageProvider>
      );

      const adminToggle = screen.getByRole("button", { name: /Quản trị/i });
      await user.click(adminToggle);

      expect(adminToggle).toHaveAttribute("aria-expanded", "true");
      expect(window.localStorage.getItem("havi_admin_nav_expanded")).toBe("true");

      // 7 mục quản trị phải xuất hiện đầy đủ
      expect(screen.getByRole("link", { name: /Thư viện media/i })).toBeInTheDocument();
      expect(screen.getByRole("link", { name: /Kênh kết nối/i })).toBeInTheDocument();
      expect(screen.getByRole("link", { name: /Đội ngũ/i })).toBeInTheDocument();
      expect(screen.getByRole("link", { name: /Lịch sử/i })).toBeInTheDocument();
      expect(screen.getByRole("link", { name: /Báo cáo/i })).toBeInTheDocument();
      expect(screen.getByRole("link", { name: /Gói cước/i })).toBeInTheDocument();
      expect(screen.getByRole("link", { name: /Cài đặt/i })).toBeInTheDocument();

      // Click lại thu gọn
      await user.click(adminToggle);
      expect(adminToggle).toHaveAttribute("aria-expanded", "false");
      expect(window.localStorage.getItem("havi_admin_nav_expanded")).toBe("false");
      expect(screen.queryByRole("link", { name: /Cài đặt/i })).not.toBeInTheDocument();
    });

    it("tự động mở nhóm Quản trị khi người dùng đang ở route quản trị (ví dụ /app/settings)", async () => {
      currentPath = "/app/settings";

      render(
        <LanguageProvider>
          <AppNav variant="desktop" />
        </LanguageProvider>
      );

      const adminToggle = screen.getByRole("button", { name: /Quản trị/i });
      expect(adminToggle).toHaveAttribute("aria-expanded", "true");

      const settingsLink = screen.getByRole("link", { name: /Cài đặt/i });
      expect(settingsLink).toBeInTheDocument();
      expect(settingsLink).toHaveAttribute("aria-current", "page");
    });

    it("đánh dấu mục Nội dung là active khi truy cập /app/media", async () => {
      currentPath = "/app/media";

      render(
        <LanguageProvider>
          <AppNav variant="desktop" />
        </LanguageProvider>
      );

      const contentLink = screen.getByRole("link", { name: /Nội dung/i });
      expect(contentLink).toHaveAttribute("aria-current", "page");
    });

    it("hiển thị badge cho Nội dung, Lịch đăng, Hội thoại và cảnh báo kết nối hỏng trên Quản trị", async () => {
      vi.spyOn(dashboardApi, "fetchDashboardSummary").mockResolvedValue({
        ok: true,
        data: jsonSummary({
          pending_approval: 4,
          failed: 2,
          unhandled_inbox: 7,
          broken_connections: 1,
        }),
      });

      render(
        <LanguageProvider>
          <AppNav variant="desktop" />
        </LanguageProvider>
      );

      await waitFor(() => {
        expect(screen.getByText("4")).toBeInTheDocument();
        expect(screen.getByText("2")).toBeInTheDocument();
        expect(screen.getByText("7")).toBeInTheDocument();
        expect(screen.getByText("!")).toBeInTheDocument();
      });

      // Việc cần làm không có badge đếm gộp
      const todoLink = screen.getByRole("link", { name: /Việc cần làm/i });
      expect(todoLink.textContent).not.toMatch(/\d+/);
    });
  });

  describe("Mobile Navigation", () => {
    it("chỉ hiển thị đúng 4 tab ở đáy màn hình, không có tab Thêm", async () => {
      render(
        <LanguageProvider>
          <AppNav variant="mobile" />
        </LanguageProvider>
      );

      const mobileNav = screen.getByRole("navigation", { hidden: true });
      const links = mobileNav.querySelectorAll("a");
      expect(links).toHaveLength(4);

      expect(screen.getByRole("link", { name: /Việc cần làm/i, hidden: true })).toBeInTheDocument();
      expect(screen.getByRole("link", { name: /Nội dung/i, hidden: true })).toBeInTheDocument();
      expect(screen.getByRole("link", { name: /Lịch đăng/i, hidden: true })).toBeInTheDocument();
      expect(screen.getByRole("link", { name: /Hội thoại/i, hidden: true })).toBeInTheDocument();

      // Không còn tab "Thêm"
      expect(screen.queryByRole("button", { name: /Thêm/i, hidden: true })).not.toBeInTheDocument();
      expect(screen.queryByRole("link", { name: /Thêm/i, hidden: true })).not.toBeInTheDocument();
    });

    it("hiển thị số badge chính xác trên mobile nav", async () => {
      vi.spyOn(dashboardApi, "fetchDashboardSummary").mockResolvedValue({
        ok: true,
        data: jsonSummary({
          pending_approval: 5,
          failed: 1,
          unhandled_inbox: 3,
        }),
      });

      render(
        <LanguageProvider>
          <AppNav variant="mobile" />
        </LanguageProvider>
      );

      await waitFor(() => {
        expect(screen.getByText("5")).toBeInTheDocument();
        expect(screen.getByText("1")).toBeInTheDocument();
        expect(screen.getByText("3")).toBeInTheDocument();
      });
    });
  });

  describe("MobileAdminSheet (Bottom Sheet Quản trị)", () => {
    it("không render khi isOpen=false", () => {
      render(
        <LanguageProvider>
          <MobileAdminSheet isOpen={false} onClose={vi.fn()} />
        </LanguageProvider>
      );

      expect(screen.queryByTestId("mobile-admin-sheet")).not.toBeInTheDocument();
    });

    it("render đầy đủ 7 mục quản trị khi isOpen=true", async () => {
      render(
        <LanguageProvider>
          <MobileAdminSheet isOpen={true} onClose={vi.fn()} />
        </LanguageProvider>
      );

      const sheet = screen.getByTestId("mobile-admin-sheet");
      expect(sheet).toBeInTheDocument();
      expect(sheet).toHaveAttribute("role", "dialog");
      expect(sheet).toHaveAttribute("aria-modal", "true");

      expect(screen.getByRole("link", { name: /Thư viện media/i })).toBeInTheDocument();
      expect(screen.getByRole("link", { name: /Kênh kết nối/i })).toBeInTheDocument();
      expect(screen.getByRole("link", { name: /Đội ngũ/i })).toBeInTheDocument();
      expect(screen.getByRole("link", { name: /Lịch sử/i })).toBeInTheDocument();
      expect(screen.getByRole("link", { name: /Báo cáo/i })).toBeInTheDocument();
      expect(screen.getByRole("link", { name: /Gói cước/i })).toBeInTheDocument();
      expect(screen.getByRole("link", { name: /Cài đặt/i })).toBeInTheDocument();
    });

    it("gọi onClose khi nhấn nút đóng X", async () => {
      const user = userEvent.setup();
      const onClose = vi.fn();

      render(
        <LanguageProvider>
          <MobileAdminSheet isOpen={true} onClose={onClose} />
        </LanguageProvider>
      );

      const closeBtn = screen.getByRole("button", { name: /Đóng menu quản trị/i });
      await user.click(closeBtn);

      expect(onClose).toHaveBeenCalledTimes(1);
    });

    it("gọi onClose khi nhấn vào backdrop", async () => {
      const user = userEvent.setup();
      const onClose = vi.fn();

      render(
        <LanguageProvider>
          <MobileAdminSheet isOpen={true} onClose={onClose} />
        </LanguageProvider>
      );

      const backdrop = screen.getByTestId("mobile-admin-backdrop");
      await user.click(backdrop);

      expect(onClose).toHaveBeenCalledTimes(1);
    });

    it("gọi onClose khi nhấn phím Escape", async () => {
      const user = userEvent.setup();
      const onClose = vi.fn();

      render(
        <LanguageProvider>
          <MobileAdminSheet isOpen={true} onClose={onClose} />
        </LanguageProvider>
      );

      await user.keyboard("{Escape}");
      expect(onClose).toHaveBeenCalledTimes(1);
    });

    it("gọi onClose khi chọn một mục điều hướng", async () => {
      const onClose = vi.fn();

      render(
        <LanguageProvider>
          <MobileAdminSheet isOpen={true} onClose={onClose} />
        </LanguageProvider>
      );

      const settingsLink = screen.getByRole("link", { name: /Cài đặt/i });
      fireEvent.click(settingsLink);

      expect(onClose).toHaveBeenCalledTimes(1);
    });
  });

  describe("AppShell Integration", () => {
    it("mở Bottom Sheet khi nhấn nút Quản trị trên mobile header", async () => {
      const user = userEvent.setup();
      writeTokens({
        accessToken: "at",
        refreshToken: "rt",
        activeWorkspaceId: "w1",
        needsOnboarding: false,
      });

      vi.spyOn(dashboardApi, "fetchDashboardSummary").mockResolvedValue({
        ok: true,
        data: jsonSummary({ broken_connections: 1 }),
      });

      render(
        <SessionProvider>
          <LanguageProvider>
            <AppShell>
              <div>Nội dung trang</div>
            </AppShell>
          </LanguageProvider>
        </SessionProvider>
      );

      const mobileAdminBtn = screen.getByTestId("mobile-header-admin-btn");
      expect(mobileAdminBtn).toBeInTheDocument();

      // Warning badge xuất hiện trên mobile header admin button
      await waitFor(() => {
        expect(mobileAdminBtn).toHaveTextContent("!");
      });

      // Click mở bottom sheet
      await user.click(mobileAdminBtn);

      const sheet = screen.getByTestId("mobile-admin-sheet");
      expect(sheet).toBeInTheDocument();
      expect(screen.getByRole("link", { name: /Kênh kết nối/i })).toBeInTheDocument();
    });
  });
});

/**
 * CSS module không được jsdom áp dụng, nên các test render ở trên không thể thấy
 * một lớp `display: none` không bao giờ được bật lại. Lỗi đã xảy ra thật:
 * `.mobileHeaderAdminBtn` mặc định `display: none` mà không có quy tắc nào trong
 * `@media (max-width: 768px)` bật lên, khiến 7 mục Quản trị không còn đường tới
 * trên mobile — sidebar chứa chúng cũng bị ẩn ở đúng breakpoint đó.
 *
 * Nên đọc thẳng file CSS. Kém tinh tế, nhưng nó kiểm được điều duy nhất quan
 * trọng ở đây: lối vào Quản trị trên mobile có thật sự hiện hay không.
 */
describe("Lối vào Quản trị trên mobile (đọc CSS)", () => {
  const css = readFileSync(
    resolve(__dirname, "app-shell.module.css"),
    "utf8",
  );

  function mobileBlock(): string {
    const start = css.indexOf("@media (max-width: 768px)");
    expect(start).toBeGreaterThan(-1);
    let depth = 0;
    for (let i = css.indexOf("{", start); i < css.length; i++) {
      if (css[i] === "{") depth++;
      else if (css[i] === "}" && --depth === 0) return css.slice(start, i);
    }
    throw new Error("Không tìm được điểm đóng của @media");
  }

  it("ẩn sidebar ở mobile thì phải bật nút mở bottom sheet Quản trị", () => {
    const block = mobileBlock();
    expect(block).toMatch(/\.sidebar\s*\{[^}]*display:\s*none/);
    expect(block).toMatch(/\.mobileHeaderAdminBtn\s*\{[^}]*display:\s*(inline-)?flex/);
  });

  it("nút Quản trị vẫn ẩn ở desktop, nơi sidebar đã có sẵn nhóm đó", () => {
    const desktop = css.slice(0, css.indexOf("@media (max-width: 768px)"));
    expect(desktop).toMatch(/\.mobileHeaderAdminBtn\s*\{[^}]*display:\s*none/);
  });
});
