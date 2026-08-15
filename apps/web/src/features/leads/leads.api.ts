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

export async function listNudges(workspaceId: string): Promise<Result<{ items: CrmNudge[]; total: number }>> {
  try {
    const { data, error } = await apiClient.GET("/workspaces/{workspace_id}/crm/nudges" as any, {
      params: { path: { workspace_id: workspaceId } },
    } as any);
    if (error || !data) return { ok: false, message: GENERIC_ERROR };
    return { ok: true, data: data as any };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

export async function triggerNudgeScan(workspaceId: string, inactiveDays: number = 30): Promise<Result<CrmNudge[]>> {
  try {
    const { data, error } = await apiClient.POST("/workspaces/{workspace_id}/crm/nudges/scan" as any, {
      params: {
        path: { workspace_id: workspaceId },
        query: { inactive_days: inactiveDays },
      },
    } as any);
    if (error || !data) return { ok: false, message: GENERIC_ERROR };
    return { ok: true, data: data as any };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

export async function approveNudge(workspaceId: string, nudgeId: string): Promise<Result<CrmNudge>> {
  try {
    const { data, error } = await apiClient.POST("/workspaces/{workspace_id}/crm/nudges/{nudge_id}/approve" as any, {
      params: { path: { workspace_id: workspaceId, nudge_id: nudgeId } },
    } as any);
    if (error || !data) return { ok: false, message: GENERIC_ERROR };
    return { ok: true, data: data as any };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

export async function dismissNudge(workspaceId: string, nudgeId: string): Promise<Result<CrmNudge>> {
  try {
    const { data, error } = await apiClient.POST("/workspaces/{workspace_id}/crm/nudges/{nudge_id}/dismiss" as any, {
      params: { path: { workspace_id: workspaceId, nudge_id: nudgeId } },
    } as any);
    if (error || !data) return { ok: false, message: GENERIC_ERROR };
    return { ok: true, data: data as any };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}
