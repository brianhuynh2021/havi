import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { LandingScreen } from "./landing-screen";
import { LanguageProvider } from "@/lib/i18n/language-context";
import { writeTokens, clearTokens } from "@/lib/auth/token-store";

function renderLanding() {
  return render(
    <LanguageProvider>
      <LandingScreen />
    </LanguageProvider>
  );
}

describe("LandingScreen", () => {
  it("phân biệt Facebook Beta và pilot dữ liệu thật", () => {
    renderLanding();
    expect(screen.getAllByText(/facebook beta/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/pilot/i).length).toBeGreaterThan(0);
  });

  it("không hiển thị bảng giá thu tiền khi đang trong giai đoạn pilot", () => {
    renderLanding();
    expect(screen.queryByText(/189.000 đ/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/369.000 đ/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/799.000 đ/i)).not.toBeInTheDocument();
  });

  it("nói rõ nguyên tắc an toàn duyệt-trước là giá trị cốt lõi", () => {
    renderLanding();
    expect(screen.getByText(/bạn duyệt trước, luôn luôn/i)).toBeInTheDocument();
    expect(screen.getByText(/api chính thức, trạng thái trung thực/i)).toBeInTheDocument();
  });

  it("cho phép tương tác đổi ngành trong Showcase 3D Demo trực tuyến", async () => {
    renderLanding();
    const user = userEvent.setup();

    // Bấm chọn ngành F&B Quán ăn & Cafe
    const fbBtn = screen.getByRole("button", { name: /quán ăn & cafe/i });
    await user.click(fbBtn);
    expect(screen.getAllByText(/quán ăn & cafe/i).length).toBeGreaterThan(0);

    // Bấm chọn ngành Dạy Nghề Thực Chiến
    const eduBtn = screen.getByRole("button", { name: /đào tạo & dịch vụ nghề/i });
    await user.click(eduBtn);
    expect(screen.getAllByText(/đào tạo & dịch vụ nghề/i).length).toBeGreaterThan(0);
  });

  it("CTA dẫn tới đăng ký và đăng nhập", () => {
    renderLanding();
    const signupLinks = screen.getAllByRole("link", { name: /dùng thử 7 ngày/i });
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
    for (const id of ["demo-studio", "khach-hang", "nguyen-tac", "faq"]) {
      expect(container.querySelector(`#${id}`)).not.toBeNull();
      expect(
        container.querySelector(`a[href="#${id}"]`),
        `thiếu link tới #${id}`,
      ).not.toBeNull();
    }
  });

  it("bấm nút Liên hệ Chuyên viên B2B thì mở popup tư vấn doanh nghiệp", async () => {
    renderLanding();
    const user = userEvent.setup();

    const b2bButton = screen.getByRole("button", { name: /liên hệ chuyên viên b2b/i });
    await user.click(b2bButton);

    expect(screen.getByText(/Tư Vấn Giải Pháp Havi Enterprise/i)).toBeInTheDocument();
    expect(screen.getByText(/Gửi Yêu Cầu Tư Vấn Ngay/i)).toBeInTheDocument();
  });

  it("không dựng testimonial hoặc ROI khi pilot chưa có bằng chứng", () => {
    renderLanding();
    expect(screen.getByText(/Pilot Đang Được Đo Bằng Dữ Liệu Thật/i)).toBeInTheDocument();
    expect(screen.getByText(/chưa công bố testimonial, ROI/i)).toBeInTheDocument();
    expect(screen.queryByText(/Chị Mai Lan/i)).not.toBeInTheDocument();
  });

  it("cho phép tương tác đóng mở Accordion FAQ", async () => {
    renderLanding();
    const user = userEvent.setup();

    expect(screen.getByRole("heading", { name: /Câu Hỏi Thường Gặp/i })).toBeInTheDocument();
    // Default open FAQ 0
    expect(screen.getByText(/Havi hướng tới thao tác đơn giản trên điện thoại/i)).toBeInTheDocument();

    // Click FAQ 1: Havi có tự động đăng bài...
    const faqBtn = screen.getByRole("button", { name: /Havi có tự động đăng bài lên mạng xã hội/i });
    await user.click(faqBtn);
    expect(screen.getByText(/Tuyệt đối KHÔNG. Nguyên tắc cốt lõi số 1 của Havi/i)).toBeInTheDocument();
  });

  it("hiển thị Hero 3D Cinematic Showcase và cho phép chuyển đổi giữa các bước", async () => {
    renderLanding();
    const user = userEvent.setup();

    expect(screen.getByTestId("hero-cinematic-showcase")).toBeInTheDocument();
    expect(screen.getByTestId("step-content-0")).toBeInTheDocument();
    expect(screen.getByText(/Đã nhận diện bối cảnh & dịch vụ tiệm/i)).toBeInTheDocument();

    // Click step 2: Tự tạo bài & Video
    const step2Btn = screen.getByRole("button", { name: /Bước 2: Tự tạo bài & Video/i });
    await user.click(step2Btn);
    const step1El = screen.getByTestId("step-content-1");
    expect(step1El).toBeInTheDocument();
    expect(within(step1El).getByText(/TikTok Video 9:16/i)).toBeInTheDocument();

    // Click step 3: Theo dõi vận hành
    const step3Btn = screen.getByRole("button", { name: /Bước 3: Theo dõi vận hành/i });
    await user.click(step3Btn);
    const step2El = screen.getByTestId("step-content-2");
    expect(step2El).toBeInTheDocument();
    expect(within(step2El).getByText(/Trung tâm vận hành Havi/i)).toBeInTheDocument();
  });

  it("bấm nút Xem Video Thực Chiến 60s thì mở video modal và có thể đóng lại", async () => {
    renderLanding();
    const user = userEvent.setup();

    const watchBtn = screen.getByRole("button", { name: /Xem Video Thực Chiến 60s/i });
    await user.click(watchBtn);

    expect(screen.getByRole("dialog", { name: /Video trình diễn thực chiến Havi 60 giây/i })).toBeInTheDocument();
    expect(screen.getByText(/DEMO THỰC CHIẾN 60S/i)).toBeInTheDocument();

    // Click close button
    const closeBtn = screen.getByRole("button", { name: /Đóng video/i });
    await user.click(closeBtn);

    expect(screen.queryByRole("dialog", { name: /Video trình diễn thực chiến Havi 60 giây/i })).not.toBeInTheDocument();
  });

  it("khi người dùng đã đăng nhập thì hiện nút Vào ứng dụng và dẫn vào /app", () => {
    writeTokens({
      accessToken: "mock-valid-jwt",
      refreshToken: "mock-refresh",
      activeWorkspaceId: "ws-123",
      needsOnboarding: false,
    });

    renderLanding();

    const appLinks = screen.getAllByRole("link", { name: /vào ứng dụng/i });
    expect(appLinks.length).toBeGreaterThan(0);
    expect(appLinks[0]).toHaveAttribute("href", "/app");

    expect(screen.getByRole("link", { name: /vào không gian làm việc của bạn/i })).toHaveAttribute(
      "href",
      "/app",
    );

    clearTokens();
  });
});
