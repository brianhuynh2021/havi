import { render, screen, within } from "@testing-library/react";
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
    expect(screen.getByText(/tuyệt đối an toàn cho fanpage/i)).toBeInTheDocument();
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
    for (const id of ["demo-studio", "bang-gia", "khach-hang", "faq"]) {
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

  it("hiển thị các đánh giá thực chiến từ chủ tiệm (Testimonials)", () => {
    renderLanding();
    expect(screen.getByText(/Chủ Tiệm Nói Gì Về Havi/i)).toBeInTheDocument();
    expect(screen.getByText(/Chị Mai Lan/i)).toBeInTheDocument();
    expect(screen.getByText(/Anh Quốc Hoàng/i)).toBeInTheDocument();
  });

  it("cho phép tương tác đóng mở Accordion FAQ", async () => {
    renderLanding();
    const user = userEvent.setup();

    expect(screen.getByText(/Câu Hỏi Thường Gặp/i)).toBeInTheDocument();
    // Default open FAQ 0
    expect(screen.getByText(/Hoàn toàn dễ dàng! Havi được thiết kế trực quan/i)).toBeInTheDocument();

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

    // Click step 2: AI Sinh Đa Kênh
    const step2Btn = screen.getByRole("button", { name: /Bước 2: AI Sinh Đa Kênh/i });
    await user.click(step2Btn);
    const step1El = screen.getByTestId("step-content-1");
    expect(step1El).toBeInTheDocument();
    expect(within(step1El).getByText(/TikTok Video 9:16/i)).toBeInTheDocument();

    // Click step 3: Bắn Lead Telegram
    const step3Btn = screen.getByRole("button", { name: /Bước 3: Bắn Lead Telegram/i });
    await user.click(step3Btn);
    const step2El = screen.getByTestId("step-content-2");
    expect(step2El).toBeInTheDocument();
    expect(within(step2El).getByText(/Havi Hot Lead Radar Bot/i)).toBeInTheDocument();
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
});

