import { render, screen } from "@testing-library/react";
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

  it("B2B chỉ mở kênh liên hệ thật, không diễn gửi biểu mẫu thành công", async () => {
    renderLanding();
    const user = userEvent.setup();

    const b2bButton = screen.getByRole("button", { name: /liên hệ chuyên viên b2b/i });
    await user.click(b2bButton);

    expect(screen.getByText(/Tư Vấn Giải Pháp Havi Enterprise/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Gọi 0984 883 750/i })).toHaveAttribute(
      "href",
      "tel:0984883750",
    );
    expect(screen.getByRole("link", { name: /Mở Zalo trực tiếp/i })).toHaveAttribute(
      "href",
      "https://zalo.me/0984883750",
    );
    expect(screen.queryByRole("button", { name: /Gửi Yêu Cầu/i })).toBeNull();
    expect(screen.queryByText(/Gửi Yêu Cầu Thành Công/i)).toBeNull();
  });

  it("không dựng testimonial hoặc ROI khi pilot chưa có bằng chứng", () => {
    renderLanding();
    expect(screen.getByText(/Bằng chứng từ vận hành thực tế/i)).toBeInTheDocument();
    expect(screen.getByText(/chỉ công bố phản hồi khách hàng hoặc hiệu quả đầu tư/i)).toBeInTheDocument();
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

  it("KHÔNG có nút nào hứa video — vì không có video nào", async () => {
    renderLanding();

    // Nút cũ mở một modal giả lập video: đồng hồ đếm giây giả, comment tự thú
    // "Simulated live visual", và ảnh Unsplash gán nhãn "Cơ sở Spa thẩm mỹ
    // thực tế". Hứa video rồi đưa ảnh stock là cùng loại sai với báo "đã đăng"
    // khi chưa gửi đi.
    const body = document.body.textContent ?? "";
    expect(body).not.toContain("Video Thực Chiến");
    expect(body).not.toContain("DEMO THỰC CHIẾN 60S");
    expect(screen.queryByTestId("video-demo-modal-backdrop")).toBeNull();
  });

  it("nút phụ ở hero dẫn xuống demo thật trên chính trang này", async () => {
    renderLanding();

    const link = screen.getByRole("link", { name: /Xem demo bên dưới/i });
    expect(link).toHaveAttribute("href", "#demo-studio");
  });

  it("không tải ảnh từ bên thứ ba", async () => {
    renderLanding();

    // Ảnh Unsplash là một request ra ngoài: bên đó xuống hoặc bị chặn thì
    // landing vỡ, và Havi không kiểm soát được nội dung đó.
    const external = [...document.querySelectorAll("img")].filter((img) =>
      /^https?:\/\//.test(img.getAttribute("src") ?? ""),
    );
    expect(external).toHaveLength(0);
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

  it("demo sản phẩm chạy được và đổi bước bằng cách bấm", async () => {
    renderLanding();
    const user = userEvent.setup();

    // Cảnh 1 hiện sẵn.
    expect(screen.getByText(/Một tấm ảnh và vài dòng/i)).toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: /Đọc lại Trang để xác nhận/i }));

    expect(
      screen.getByText(/chỉ báo “đã đăng” sau khi thấy bài có thật/i),
    ).toBeInTheDocument();
  });

  it("demo KHÔNG hứa tính năng đã bỏ và không tự nhận là dữ liệu thật", async () => {
    renderLanding();

    const body = document.body.textContent ?? "";
    // Khối cũ dùng ảnh AI theo ngành kèm nhãn "HAVI VISION AI · 0.34s" và một
    // dòng tự thú "Bản nháp minh hoạ — cần thay bằng dữ liệu thật".
    for (const gone of [
      "HAVI VISION AI",
      "Bản nháp minh hoạ",
      "kịch bản video",
      "Kịch bản video",
      "TikTok Video 9:16",
    ]) {
      expect(body).not.toContain(gone);
    }
  });

  it("điểm khác biệt — xác minh bài đã lên — được nêu rõ", async () => {
    renderLanding();
    const user = userEvent.setup();

    await user.click(screen.getByRole("tab", { name: /Đọc lại Trang để xác nhận/i }));

    expect(screen.getByText(/Xác nhận bằng dữ liệu Facebook trả về/i)).toBeInTheDocument();
  });
});
