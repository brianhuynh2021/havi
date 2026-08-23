import { readTokens } from "@/lib/auth/token-store";
import { authedFetch } from "@/lib/api-client/client";
import { NETWORK_ERROR_MESSAGE, detailToMessage } from "@/features/auth/auth.api";

export type Result<T> = { ok: true; data: T } | { ok: false; message: string };

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function fetchWithAuth(path: string, init?: RequestInit): Promise<Response> {
  const tokens = readTokens();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init?.headers as Record<string, string>),
  };
  if (tokens?.accessToken) headers.Authorization = `Bearer ${tokens.accessToken}`;
  if (tokens?.activeWorkspaceId) headers["X-Workspace-Id"] = tokens.activeWorkspaceId;

  const req = new Request(BASE_URL + path, { ...init, headers });
  return authedFetch(req);
}


export type CampaignSimulationInput = {
  objective?: "messages" | "reach" | "leads" | "store_visits";
  radius_km?: number;
  daily_budget_vnd?: number;
  duration_days?: number;
  target_audience?: string;
};

export type CampaignSimulationResult = {
  objective: string;
  radius_km: number;
  daily_budget_vnd: number;
  duration_days: number;
  total_budget_vnd: number;
  estimated_reach_min: number;
  estimated_reach_max: number;
  estimated_conversations_min: number;
  estimated_conversations_max: number;
  estimated_cpm_vnd: number;
  disclaimer: string;
  safety_guardrails: string[];
};

export async function simulateCampaign(
  params: CampaignSimulationInput
): Promise<Result<CampaignSimulationResult>> {
  try {
    const res = await fetchWithAuth("/campaigns/simulate", {
      method: "POST",
      body: JSON.stringify(params),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      return { ok: false, message: detailToMessage(body?.detail, "Không mô phỏng được chiến dịch") };
    }
    const data = await res.json();
    return { ok: true, data };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}
