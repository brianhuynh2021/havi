import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { writeTokens } from "@/lib/auth/token-store";
import { LanguageProvider } from "@/lib/i18n/language-context";
import { EvidenceScreen } from "./evidence-screen";

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

function renderEvidence() {
  return render(
    <LanguageProvider>
      <EvidenceScreen />
    </LanguageProvider>
  );
}

describe("EvidenceScreen (Phase 2)", () => {
  beforeEach(() => {
    window.localStorage.clear();
    signedIn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("hiển thị danh sách bằng chứng và độ tin cậy từ API", async () => {
    const mockGoal = {
      id: "g1",
      workspace_id: "w1",
      title: "Tuyển sinh 20 học viên AI",
      category: "acquire_customers",
      evidence_definition: "Học viên đóng tiền VietQR",
      status: "active",
      weekly_capacity_hours: 10,
    };

    const mockEvidence = [
      {
        id: "ev1",
        workspace_id: "w1",
        goal_id: "g1",
        task_id: null,
        source: "vietqr",
        evidence_type: "transfer",
        value_text: "Học viên Nguyễn Văn A chuyển khoản học phí",
        value_number: 4500000,
        media_asset_id: null,
        confidence: 1.0,
        created_at: "2026-08-23T10:00:00Z",
      },
    ];

    vi.spyOn(globalThis, "fetch").mockImplementation(async (input: RequestInfo | URL) => {
      const url = new URL(input instanceof Request ? input.url : String(input), "http://localhost:8000");
      if (url.pathname.includes("/goals/active")) {
        return jsonResponse(mockGoal);
      }
      if (url.pathname.includes("/roadmaps/active")) {
        return jsonResponse({
          roadmap: { id: "r1", goal_id: "g1", version: 1 },
          tasks: [],
        });
      }
      if (url.pathname.includes("/roadmaps/evidence")) {
        return jsonResponse(mockEvidence);
      }
      return jsonResponse({});
    });

    renderEvidence();

    expect(await screen.findByText(/Bằng Chứng & Kết Quả Thực Tế/i)).toBeInTheDocument();
    expect(screen.getByText(/Học viên Nguyễn Văn A chuyển khoản học phí/i)).toBeInTheDocument();
    expect(screen.getByText(/Độ tin cậy 100%/i)).toBeInTheDocument();
    expect(screen.getByText(/4.500.000/i)).toBeInTheDocument();
  });
});
