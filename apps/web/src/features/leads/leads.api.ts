import { apiClient } from "@/lib/api-client/client";
import { NETWORK_ERROR_MESSAGE } from "@/features/auth/auth.api";
import type { components } from "@/lib/api-client/schema";

export type InboxItem = components["schemas"]["InboxItem"];
export type Lead = components["schemas"]["Lead"];
export type LeadReplyStatus = components["schemas"]["LeadReplyStatus"];

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

