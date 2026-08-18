import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { LandingScreen } from "./landing-screen";
import { LanguageProvider } from "@/lib/i18n/language-context";

function renderLanding() {
  return render(
    <LanguageProvider>
      <LandingScreen />
    </LanguageProvider>
  );
}

describe("LandingScreen", () => {
  it("hiển thị đầy đủ 4 trụ cột tiếp thị đa kênh của Havi", () => {
    renderLanding();
    expect(screen.getAllByText(/facebook/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/tiktok/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/google maps/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/trực inbox/i).length).toBeGreaterThan(0);
  });

  it("hiển thị bảng giá thương mại chính thức (Gói Khởi Nghiệp 189k & Gói Chuyên Nghiệp 369k)", () => {
    renderLanding();
    expect(screen.getAllByText(/189.000 đ/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/369.000 đ/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/7 ngày/i).length).toBeGreaterThan(0);
  });

  it("nói rõ nguyên tắc an toàn duyệt-trước là giá trị cốt lõi", () => {
    renderLanding();
    expect(screen.getByText(/bạn duyệt trước, luôn luôn/i)).toBeInTheDocument();
    expect(screen.getByText(/chỉ dùng api chính thức/i)).toBeInTheDocument();
  });

  it("cho phép tương tác đổi tab trong Studio Demo trực tuyến", async () => {
    renderLanding();
    const user = userEvent.setup();

    // Bấm chuyển sang tab TikTok Video
    const videoTab = screen.getByRole("button", { name: /tiktok video/i });
    await user.click(videoTab);
    expect(screen.getAllByText(/3-Second Retention Hook/i).length).toBeGreaterThan(0);

    // Bấm chuyển sang tab Trực Inbox Bắt SĐT
    const inboxTab = screen.getByRole("button", { name: /trực inbox bắt sđt/i });
    await user.click(inboxTab);
    expect(screen.getAllByText(/Đã bắt SĐT về CRM/i).length).toBeGreaterThan(0);
  });

  it("CTA dẫn tới đăng ký và đăng nhập", () => {
    renderLanding();
    const signupLinks = screen.getAllByRole("link", { name: /dùng thử 14 ngày/i });
    expect(signupLinks.length).toBeGreaterThan(0);
    for (const link of signupLinks) {
      expect(link).toHaveAttribute("href", "/signup");
    }

    const loginLinks = screen.getAllByRole("link", { name: /^đăng nhập$/i });
    expect(loginLinks.length).toBeGreaterThan(0);
    for (const link of loginLinks) {
      expect(link).toHaveAttribute("href", "/login");
    }
  });

  it("có anchor navigation tới các section chính", () => {
    const { container } = renderLanding();
    for (const id of ["demo-studio", "cach-hoat-dong", "bang-gia", "nguyen-tac"]) {
      expect(container.querySelector(`#${id}`)).not.toBeNull();
      expect(
        container.querySelector(`a[href="#${id}"]`),
        `thiếu link tới #${id}`,
      ).not.toBeNull();
    }
  });
});

