import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { writeTokens } from "@/lib/auth/token-store";
import { LanguageProvider } from "@/lib/i18n/language-context";
import { AuthenticVideoDropzone } from "./authentic-video-dropzone";

function signedIn() {
  writeTokens({
    accessToken: "at",
    refreshToken: "rt",
    activeWorkspaceId: "w1",
    needsOnboarding: false,
  });
}

function renderDropzone(industry = "education") {
  return render(
    <LanguageProvider>
      <AuthenticVideoDropzone industry={industry} />
    </LanguageProvider>
  );
}

describe("AuthenticVideoDropzone", () => {
  beforeEach(() => {
    window.localStorage.clear();
    signedIn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("hiển thị ô dropzone rỗng và cho phép chọn clip mẫu", async () => {
    renderDropzone("education");

    expect(screen.getByText(/Quay 10-15s clip thật tại cơ sở và thả vào đây/i)).toBeInTheDocument();
    expect(screen.getByText(/Dùng clip mẫu thực hành \(Thử ngay\)/i)).toBeInTheDocument();

    const sampleBtn = screen.getByText(/Dùng clip mẫu thực hành \(Thử ngay\)/i);
    fireEvent.click(sampleBtn);

    // After clicking sample, AI hook options for Education should appear
    expect(screen.getByText(/Chọn 1 câu Hook giật tít 3 giây đầu/i)).toBeInTheDocument();
    expect(screen.getByText(/Bé 8 tuổi tự tay ráp xe Robot thông minh/i)).toBeInTheDocument();
    expect(screen.getByText(/Caption chân thực & Lời mời nhận vé trải nghiệm/i)).toBeInTheDocument();
    expect(screen.getByText(/Xuất bản Video & Đăng Reels \+ TikTok \+ Google Maps/i)).toBeInTheDocument();
  });

  it("cho phép đổi Hook và kích hoạt xuất bản 1-chạm", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async () => {
      return new Response(JSON.stringify({ id: "job-1", status: "completed" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    });

    renderDropzone("education");

    fireEvent.click(screen.getByText(/Dùng clip mẫu thực hành \(Thử ngay\)/i));

    // Choose alternative hook
    const altHook = screen.getByText(/Đừng cấm con nghịch điện thoại/i);
    fireEvent.click(altHook);

    const publishBtn = screen.getByText(/Xuất bản Video & Đăng Reels \+ TikTok \+ Google Maps/i);
    fireEvent.click(publishBtn);

    await waitFor(() => {
      expect(screen.getByText(/Video Đã Sẵn Sàng & Lên Lịch Đa Kênh/i)).toBeInTheDocument();
    });
    expect(screen.getByText(/Ném thêm 1 clip khác/i)).toBeInTheDocument();
  });
});
