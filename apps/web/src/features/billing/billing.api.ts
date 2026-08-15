import { apiClient } from "@/lib/api-client/client";
import { NETWORK_ERROR_MESSAGE } from "@/features/auth/auth.api";
import type { components } from "@/lib/api-client/schema";

export type Subscription = components["schemas"]["Subscription"];
export type Invoice = components["schemas"]["Invoice"];
export type Plan = components["schemas"]["Plan"];

export type Result<T> = { ok: true; data: T } | { ok: false; message: string };

const GENERIC_ERROR = "Không thể tải thông tin gói cước. Vui lòng thử lại.";

export async function fetchSubscription(): Promise<Result<Subscription>> {
  try {
    const { data, error } = await apiClient.GET("/billing/subscription");
    if (error || !data) return { ok: false, message: GENERIC_ERROR };
    return { ok: true, data };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

export async function fetchInvoices(): Promise<Result<Invoice[]>> {
  try {
    const { data, error } = await apiClient.GET("/billing/invoices");
    if (error || !data) return { ok: false, message: GENERIC_ERROR };
    return { ok: true, data };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

export async function changePlan(plan: Plan): Promise<Result<Subscription>> {
  try {
    const { data, error } = await apiClient.POST("/billing/plan", {
      body: { plan },
    });
    if (error || !data) return { ok: false, message: GENERIC_ERROR };
    return { ok: true, data };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}
