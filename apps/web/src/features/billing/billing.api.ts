import { apiClient } from "@/lib/api-client/client";
import { readTokens } from "@/lib/auth/token-store";
import { NETWORK_ERROR_MESSAGE } from "@/features/auth/auth.api";
import type { components } from "@/lib/api-client/schema";

export type Subscription = components["schemas"]["Subscription"];
export type Invoice = components["schemas"]["Invoice"];
export type Plan = components["schemas"]["Plan"] | "doanh_nghiep";

export type Result<T> = { ok: true; data: T } | { ok: false; message: string };

export type CheckoutData = {
  invoice_id: string;
  plan: Plan;
  amount_vnd: number;
  transfer_content: string;
  bank_id: string;
  account_no: string;
  account_name: string;
  qr_code_url: string;
};

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

export type CheckoutOptions = {
  /** `annual` thu 10 tháng cho 12 tháng dùng. */
  cycle?: "monthly" | "annual";
  extraSeats?: number;
  extraChannels?: number;
};

export async function changePlan(
  plan: Plan,
  options: CheckoutOptions = {},
): Promise<Result<Subscription>> {
  try {
    const { data, error } = await apiClient.POST("/billing/plan", {
      // `openapi-typescript` coi field có `default` là bắt buộc trong request
      // body, nên truyền thẳng cả ba dù backend đã có mặc định.
      body: {
        plan,
        cycle: options.cycle ?? "monthly",
        extra_seats: options.extraSeats ?? 0,
        extra_channels: options.extraChannels ?? 0,
      },
    });
    if (error || !data) return { ok: false, message: GENERIC_ERROR };
    return { ok: true, data };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

export async function createCheckout(
  plan: Plan,
  options: CheckoutOptions = {},
): Promise<Result<CheckoutData>> {
  try {
    const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
    const tokens = readTokens();
    const res = await fetch(`${baseUrl}/billing/checkout`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${tokens?.accessToken}`,
      },
      body: JSON.stringify({
        plan,
        cycle: options.cycle ?? "monthly",
        extra_seats: options.extraSeats ?? 0,
        extra_channels: options.extraChannels ?? 0,
      }),
    });
    if (!res.ok) {
      return { ok: false, message: "Không thể tạo mã VietQR lúc này." };
    }
    const data = await res.json();
    return { ok: true, data };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

export async function checkInvoiceStatus(invoiceId: string): Promise<Result<{ status: string }>> {
  try {
    const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
    const tokens = readTokens();
    const res = await fetch(`${baseUrl}/billing/invoices/${invoiceId}/status`, {
      headers: {
        Authorization: `Bearer ${tokens?.accessToken}`,
      },
    });
    if (!res.ok) {
      return { ok: false, message: "Không thể kiểm tra trạng thái hoá đơn." };
    }
    const data = await res.json();
    return { ok: true, data };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}
