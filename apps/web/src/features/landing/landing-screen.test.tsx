import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { LandingScreen } from "./landing-screen";

/** Claim công khai phải bám capability thật (ROADMAP §2, §10).
 *
 * Test này là chốt chặn: ai đó copy câu chữ từ prototype sang mà quên rằng
 * tính năng chưa làm thì test đỏ ngay, thay vì phát hiện sau khi landing đã
 * public và có người đăng ký vì lời hứa đó.
 */
const CAM_KHONG_DUOC_HUA = [
  // Publish thật là Tuần 7 — pilot chưa đăng được kênh nào.
  /tự động đăng/i,
  /tự đăng/i,
  /4 kênh/i,
  // P2, và §4 cấm crawl group.
  /lắng nghe hội nhóm/i,
  /săn khách/i,
  // P2.
  /crm/i,
  // Chưa có, vision là P1/P2.
  /làm đẹp ảnh/i,
  /gắn logo/i,
  // §12: giá chỉ public sau khi đo cost trên khách Việt thật.
  /299k/i,
  /599k/i,
  /14 ngày/i,
  // Kênh chưa hỗ trợ.
  /linkedin/i,
  /youtube/i,
  /google maps/i,
  /tiktok/i,
];

describe("LandingScreen", () => {
  it("không hứa capability chưa có", () => {
    const { container } = render(<LandingScreen />);
    const text = container.textContent ?? "";

    for (const pattern of CAM_KHONG_DUOC_HUA) {
      expect(text, `Landing đang hứa thứ chưa làm được: ${pattern}`).not.toMatch(
        pattern,
      );
    }
  });

  it("chỉ nêu đúng 3 kênh pilot", () => {
    render(<LandingScreen />);
    expect(screen.getAllByText(/facebook/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/zalo oa/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/google business/i).length).toBeGreaterThan(0);
  });

  it("nói rõ nguyên tắc duyệt-trước — điểm bán hàng chính", () => {
    render(<LandingScreen />);
    expect(screen.getByText(/bạn duyệt trước, luôn luôn/i)).toBeInTheDocument();
    expect(screen.getByText(/chỉ dùng api chính thức/i)).toBeInTheDocument();
  });

  it("CTA dẫn tới đăng ký và đăng nhập thật", () => {
    render(<LandingScreen />);
    const signup = screen.getAllByRole("link", { name: /tạo tài khoản/i });
    expect(signup.length).toBeGreaterThan(0);
    for (const link of signup) {
      expect(link).toHaveAttribute("href", "/dang-ky");
    }
    // Hai link đăng nhập (header + footer) là cố ý — người cuộn hết trang
    // không phải cuộn ngược lên đầu.
    const login = screen.getAllByRole("link", { name: /^đăng nhập$/i });
    expect(login.length).toBeGreaterThan(0);
    for (const link of login) {
      expect(link).toHaveAttribute("href", "/dang-nhap");
    }
  });

  it("có anchor navigation tới các section", () => {
    const { container } = render(<LandingScreen />);
    for (const id of ["cach-hoat-dong", "nganh", "nguyen-tac"]) {
      expect(container.querySelector(`#${id}`)).not.toBeNull();
      expect(
        container.querySelector(`a[href="#${id}"]`),
        `thiếu link tới #${id}`,
      ).not.toBeNull();
    }
  });

  it("nói rõ đang thử nghiệm, chưa công bố giá", () => {
    render(<LandingScreen />);
    expect(screen.getAllByText(/giai đoạn thử nghiệm/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/bảng giá sẽ công bố sau/i)).toBeInTheDocument();
  });
});
