/**
 * Tổ chức và thương hiệu — tầng doanh nghiệp phía trên workspace.
 *
 * Một workspace **là** một thương hiệu hoặc một chi nhánh: kênh riêng, nội dung
 * riêng, kho media riêng, thành viên riêng. Tổ chức chỉ gom chúng lại và cho
 * mời người một lần cho cả công ty.
 *
 * Dữ liệu **không** chảy chéo giữa các thương hiệu — đó là điểm khiến
 * multi-brand khác với việc gắn nhãn.
 */

import { apiClient } from "@/lib/api-client/client";
import { NETWORK_ERROR_MESSAGE, detailToMessage } from "@/features/auth/auth.api";
import type { components } from "@/lib/api-client/schema";

export type Organization = components["schemas"]["Organization"];
export type OrganizationBrand = components["schemas"]["OrganizationBrand"];
export type OrganizationWithBrands = components["schemas"]["OrganizationWithBrands"];
export type Industry = components["schemas"]["Industry"];

export type Result<T> = { ok: true; data: T } | { ok: false; message: string };

export async function listOrganizations(): Promise<Result<OrganizationWithBrands[]>> {
  try {
    const { data, error } = await apiClient.GET("/organizations");
    if (error || !data) {
      return { ok: false, message: detailToMessage(error, "Không tải được danh sách thương hiệu") };
    }
    return { ok: true, data };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

export async function createBrand(
  organizationId: string,
  params: { name: string; industry: Industry },
): Promise<Result<OrganizationBrand>> {
  try {
    const { data, error } = await apiClient.POST("/organizations/{organization_id}/brands", {
      params: { path: { organization_id: organizationId } },
      body: params,
    });
    if (error || !data) {
      return { ok: false, message: detailToMessage(error, "Không mở được thương hiệu mới") };
    }
    return { ok: true, data };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

export async function inviteToOrganization(
  organizationId: string,
  email: string,
): Promise<Result<null>> {
  try {
    const { error } = await apiClient.POST("/organizations/{organization_id}/members", {
      params: { path: { organization_id: organizationId } },
      body: { email },
    });
    if (error) {
      return { ok: false, message: detailToMessage(error, "Không thêm được người vào tổ chức") };
    }
    return { ok: true, data: null };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}
