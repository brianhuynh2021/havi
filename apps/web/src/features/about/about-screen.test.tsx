import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AboutScreen } from "./about-screen";
import { LanguageProvider } from "@/lib/i18n/language-context";

function renderAbout() {
  return render(
    <LanguageProvider>
      <AboutScreen />
    </LanguageProvider>,
  );
}

describe("AboutScreen", () => {
  it("hiển thị tiêu đề, linh hồn thương hiệu Havi = Harry + Vietnam", () => {
    renderAbout();
    expect(screen.getByRole("heading", { name: /linh hồn thương hiệu/i })).toBeInTheDocument();
    expect(screen.getAllByText(/harry/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/vietnam/i).length).toBeGreaterThan(0);
  });

  it("hiển thị 3 giá trị cốt lõi và câu trích dẫn của đội ngũ sáng lập", () => {
    renderAbout();
    expect(screen.getByText(/an tâm & có quyền kiểm soát/i)).toBeInTheDocument();
    expect(screen.getByText(/chuẩn kỹ thuật đỉnh cao/i)).toBeInTheDocument();
    expect(screen.getByText(/sự tử tế & phụng sự/i)).toBeInTheDocument();
    expect(screen.getByText(/công nghệ chỉ thực sự có giá trị/i)).toBeInTheDocument();
  });

  it("có các link điều hướng về trang chủ, đăng ký, terms và privacy", () => {
    renderAbout();
    expect(screen.getByRole("link", { name: /về trang chủ/i })).toHaveAttribute("href", "/");
    expect(screen.getAllByRole("link", { name: /dùng thử 7 ngày/i }).length).toBeGreaterThan(0);
    expect(screen.getByRole("link", { name: /điều khoản sử dụng/i })).toHaveAttribute("href", "/terms");
    expect(screen.getByRole("link", { name: /chính sách bảo mật/i })).toHaveAttribute("href", "/privacy");
  });
});
