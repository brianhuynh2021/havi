import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { writeTokens } from "@/lib/auth/token-store";
import { LanguageProvider } from "@/lib/i18n/language-context";
import { VoiceRecorderModal } from "./voice-recorder-modal";
import { transcribeVoice, voiceToContent } from "./voice-note.api";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function signedIn() {
  writeTokens({
    accessToken: "at",
    refreshToken: "rt",
    activeWorkspaceId: "w1",
    needsOnboarding: false,
  });
}

describe("VoiceNote API and Modal", () => {
  beforeEach(() => {
    window.localStorage.clear();
    signedIn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("API methods", () => {
    it("transcribeVoice gửi base64 và nhận văn bản tiếng Việt", async () => {
      vi.spyOn(globalThis, "fetch").mockImplementation(async () => {
        return jsonResponse({
          text: "Hôm nay tiệm em giảm 30% gói gội đầu dưỡng sinh.",
          summary: "Giảm 30% gội đầu dưỡng sinh",
          detected_intent: "promotion",
        });
      });

      const res = await transcribeVoice("fake-base64-audio", "audio/webm");
      expect(res.ok).toBe(true);
      if (res.ok) {
        expect(res.data.text).toContain("giảm 30%");
        expect(res.data.detected_intent).toBe("promotion");
      }
    });

    it("voiceToContent tạo trực tiếp job sinh bài", async () => {
      vi.spyOn(globalThis, "fetch").mockImplementation(async () => {
        return jsonResponse({
          text: "Chương trình tri ân khách hàng tháng 8",
          summary: "Tri ân tháng 8",
          detected_intent: "announcement",
          job_id: "job-123",
          job_status: "queued",
        });
      });

      const res = await voiceToContent("fake-base64-audio", "audio/mp4");
      expect(res.ok).toBe(true);
      if (res.ok) {
        expect(res.data.job_id).toBe("job-123");
        expect(res.data.job_status).toBe("queued");
      }
    });
  });

  describe("VoiceRecorderModal Component", () => {
    it("hiển thị modal khi isOpen = true", () => {
      render(
        <LanguageProvider>
          <VoiceRecorderModal
            isOpen={true}
            onClose={() => {}}
            onInsertNote={() => {}}
            onDirectGenerate={async () => {}}
          />
        </LanguageProvider>
      );

      expect(screen.getByText("🎙️ Ghi âm ý tưởng bài viết")).toBeInTheDocument();
      expect(screen.getByTestId("mic-toggle-btn")).toBeInTheDocument();
    });

    it("không render gì khi isOpen = false", () => {
      const { container } = render(
        <LanguageProvider>
          <VoiceRecorderModal
            isOpen={false}
            onClose={() => {}}
            onInsertNote={() => {}}
            onDirectGenerate={async () => {}}
          />
        </LanguageProvider>
      );

      expect(container.firstChild).toBeNull();
    });
  });
});
