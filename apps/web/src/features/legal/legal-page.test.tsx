import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { LegalPage } from "./legal-page";
import {
  CONTACT_EMAIL,
  privacySections,
  termsSections,
} from "./legal.content";

function renderPrivacy() {
  return render(
    <LegalPage title="Chính sách bảo mật" intro="intro" sections={privacySections} />,
  );
}

function renderTerms() {
  return render(
    <LegalPage title="Điều khoản sử dụng" intro="intro" sections={termsSections} />,
  );
}

describe("Trang pháp lý", () => {
  it("hiện đủ mọi mục và đoạn văn", () => {
    const { container } = renderPrivacy();
    for (const section of privacySections) {
      expect(
        screen.getByRole("heading", { name: section.heading }),
      ).toBeInTheDocument();
      for (const p of section.paragraphs) {
        expect(container.textContent).toContain(p);
      }
    }
  });

  it("có email liên hệ bấm được — đây là đường duy nhất để xoá tài khoản", () => {
    renderPrivacy();
    expect(screen.getByRole("link", { name: CONTACT_EMAIL })).toHaveAttribute(
      "href",
      `mailto:${CONTACT_EMAIL}`,
    );
  });

  it("link chéo giữa hai trang pháp lý", () => {
    renderTerms();
    expect(
      screen.getByRole("link", { name: /điều khoản sử dụng/i }),
    ).toHaveAttribute("href", "/terms");
    expect(
      screen.getByRole("link", { name: /chính sách bảo mật/i }),
    ).toHaveAttribute("href", "/privacy");
  });
});

/**
 * Chính sách bảo mật là cam kết pháp lý — hứa một tính năng chưa code xong ở
 * đây tệ hơn nhiều so với hứa trên landing. Test chặn hai chiều: không được
 * hứa thừa, và phải nói đủ những thứ luật VN yêu cầu.
 */
describe("Chính sách bảo mật không hứa quá capability", () => {
  function privacyText() {
    const { container } = renderPrivacy();
    return container.textContent ?? "";
  }

  it("không nói người dùng tự xoá tài khoản được trong app", () => {
    // Chưa có endpoint xoá tài khoản — mọi yêu cầu xử lý thủ công qua email.
    const text = privacyText();
    expect(text).toMatch(/gửi email/i);
    expect(text).toMatch(/xử lý thủ công|thủ công trong vòng/i);
    expect(text).not.toMatch(/nút xoá tài khoản|tự xoá tài khoản trong/i);
  });

  it("không hứa mã hoá đầu-cuối hay tuyệt đối an toàn", () => {
    const text = privacyText();
    expect(text).not.toMatch(/mã hoá đầu[- ]cuối|end-to-end/i);
    expect(text).not.toMatch(/an toàn tuyệt đối(?!\.)/i);
    // Phải thừa nhận giới hạn thay vì im lặng.
    expect(text).toMatch(/không hệ thống nào an toàn tuyệt đối/i);
  });

  it("nói rõ dữ liệu được gửi cho nhà cung cấp AI bên thứ ba", () => {
    // Người dùng có quyền biết liệu thô của họ rời khỏi Havi đi đâu.
    const text = privacyText();
    expect(text).toMatch(/google.*gemini/i);
    expect(text).toMatch(/anthropic|openai/i);
  });

  it("nêu đủ quyền của chủ thể dữ liệu theo luật VN", () => {
    const text = privacyText();
    for (const quyen of [/quyền biết/i, /yêu cầu sửa/i, /yêu cầu xoá/i, /rút lại sự đồng ý/i]) {
      expect(text).toMatch(quyen);
    }
    expect(text).toMatch(/khiếu nại/i);
  });

  it("nói rõ trách nhiệm xin phép ảnh khách hàng thuộc về chủ tiệm", () => {
    const text = privacyText();
    expect(text).toMatch(/ảnh có (mặt |hình )?khách hàng|ảnh có hình khách/i);
    expect(text).toMatch(/phải được họ đồng ý/i);
  });

  it("nói rõ thời hạn lưu và xoá dữ liệu", () => {
    expect(privacyText()).toMatch(/30 ngày/);
  });
});

describe("Điều khoản nói rõ ai chịu trách nhiệm nội dung AI", () => {
  function termsText() {
    const { container } = renderTerms();
    return container.textContent ?? "";
  }

  it("cảnh báo AI có thể viết sai", () => {
    const text = termsText();
    expect(text).toMatch(/có thể viết sai/i);
    // Không được hứa bộ lọc bắt hết — nó không bắt hết.
    expect(text).toMatch(/không thể bắt hết/i);
  });

  it("nói rõ duyệt là chịu trách nhiệm, và bài luôn chờ duyệt", () => {
    const text = termsText();
    expect(text).toMatch(/chờ duyệt/i);
    expect(text).toMatch(/chịu trách nhiệm về nội dung/i);
  });

  it("khẳng định người dùng giữ quyền với nội dung của mình", () => {
    expect(termsText()).toMatch(/không đòi quyền sở hữu/i);
  });

  it("nói rõ chỉ dùng API chính thức, không crawl", () => {
    const text = termsText();
    expect(text).toMatch(/api chính thức/i);
    expect(text).toMatch(/không thu thập dữ liệu bằng cách crawl|không.*crawl/i);
  });
});
