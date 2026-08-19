import { apiClient } from "@/lib/api-client/client";
import { readTokens } from "@/lib/auth/token-store";
import { NETWORK_ERROR_MESSAGE } from "@/features/auth/auth.api";
import type { components } from "@/lib/api-client/schema";

export type InboxItem = components["schemas"]["InboxItem"];
export type Lead = components["schemas"]["Lead"];
export type LeadReplyStatus = components["schemas"]["LeadReplyStatus"];

export function getActiveWorkspaceId(): string | null {
  return readTokens()?.activeWorkspaceId ?? null;
}

export interface CrmNudge {
  id: string;
  workspace_id: string;
  lead_id: string;
  nudge_type: "inactive_30_days" | "followup_14_days" | "birthday_special";
  status: "pending_approval" | "sent" | "dismissed";
  message: string;
  created_at: string;
  sent_at?: string | null;
}

export type Result<T> = { ok: true; data: T } | { ok: false; message: string };

const GENERIC_ERROR = "Có lỗi xảy ra, thử lại giúp chị nhé.";

export async function listInbox(): Promise<Result<InboxItem[]>> {
  try {
    const { data, error } = await apiClient.GET("/inbox");
    if (error || !data) return { ok: false, message: GENERIC_ERROR };
    const items = data.items || [];
    return { ok: true, data: items };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

export async function sendInboxReply(id: string, text: string): Promise<Result<InboxItem>> {
  try {
    const { data, error } = await apiClient.POST("/inbox/{item_id}/reply", {
      params: { path: { item_id: id } },
      body: { text },
    });
    if (error || !data) return { ok: false, message: GENERIC_ERROR };
    return { ok: true, data };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

export async function listLeads(): Promise<Result<Lead[]>> {
  try {
    const { data, error } = await apiClient.GET("/leads");
    if (error || !data) return { ok: false, message: GENERIC_ERROR };
    const items = data.items || [];
    return { ok: true, data: items };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

export async function dismissInboxItem(id: string): Promise<Result<void>> {
  try {
    const { error } = await apiClient.POST("/inbox/{item_id}/dismiss", {
      params: { path: { item_id: id } },
    });
    if (error) return { ok: false, message: GENERIC_ERROR };
    return { ok: true, data: undefined };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function nudgeFetch(path: string, options: RequestInit = {}): Promise<Response> {
  const tokens = readTokens();
  const headers = new Headers(options.headers || {});
  if (tokens?.accessToken) {
    headers.set("Authorization", `Bearer ${tokens.accessToken}`);
  }
  if (!headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }
  return fetch(`${baseUrl}${path}`, { ...options, headers });
}

export async function listNudges(workspaceId: string): Promise<Result<{ items: CrmNudge[]; total: number }>> {
  try {
    const res = await nudgeFetch(`/workspaces/${workspaceId}/crm/nudges`);
    if (!res.ok) return { ok: false, message: GENERIC_ERROR };
    const data = (await res.json()) as { items: CrmNudge[]; total: number };
    return { ok: true, data };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

export async function triggerNudgeScan(workspaceId: string, inactiveDays: number = 30): Promise<Result<CrmNudge[]>> {
  try {
    const res = await nudgeFetch(
      `/workspaces/${workspaceId}/crm/nudges/scan?inactive_days=${inactiveDays}`,
      { method: "POST" }
    );
    if (!res.ok) return { ok: false, message: GENERIC_ERROR };
    const data = (await res.json()) as CrmNudge[];
    return { ok: true, data };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

export async function approveNudge(workspaceId: string, nudgeId: string): Promise<Result<CrmNudge>> {
  try {
    const res = await nudgeFetch(
      `/workspaces/${workspaceId}/crm/nudges/${nudgeId}/approve`,
      { method: "POST" }
    );
    if (!res.ok) return { ok: false, message: GENERIC_ERROR };
    const data = (await res.json()) as CrmNudge;
    return { ok: true, data };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

export async function dismissNudge(
  workspaceId: string,
  nudgeId: string,
): Promise<Result<void>> {
  try {
    const res = await nudgeFetch(
      `/workspaces/${workspaceId}/crm/nudges/${nudgeId}/dismiss`,
      { method: "POST" },
    );
    if (!res.ok) return { ok: false, message: GENERIC_ERROR };
    return { ok: true, data: undefined };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

export async function testTelegramAlert(): Promise<Result<string>> {
  try {
    const res = await nudgeFetch("/leads/test-telegram", { method: "POST" });
    if (!res.ok) return { ok: false, message: GENERIC_ERROR };
    const data = (await res.json()) as { status: string; message: string };
    return { ok: true, data: data.message };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}
