/**
 * Thư viện media — kho ảnh và clip dùng lại được của workspace.
 *
 * Có kho riêng thay vì tải lên mỗi lần soạn bài, vì một cơ sở dùng đi dùng lại
 * cùng vài chục tấm ảnh: mặt tiền, thực đơn, đội ngũ, không gian. Bắt tải lại mỗi lần
 * là bắt họ đi tìm file trong điện thoại giữa lúc đang muốn đăng.
 */

import { apiClient } from "@/lib/api-client/client";
import { NETWORK_ERROR_MESSAGE, detailToMessage } from "@/features/auth/auth.api";
import type { components } from "@/lib/api-client/schema";

export type MediaAsset = components["schemas"]["MediaAsset"];
export type MediaType = components["schemas"]["MediaType"];

export type Result<T> = { ok: true; data: T } | { ok: false; message: string };

export type MediaPage = { items: MediaAsset[]; total: number };

export async function listMedia(params: {
  type?: MediaType;
  limit?: number;
  offset?: number;
} = {}): Promise<Result<MediaPage>> {
  try {
    const { data, error } = await apiClient.GET("/media", {
      params: {
        query: {
          ...(params.type ? { type: params.type } : {}),
          limit: params.limit ?? 50,
          offset: params.offset ?? 0,
          // Chỉ lấy asset đã upload xong. Bản ghi `pending` là vé upload chưa
          // dùng — hiện nó lên thư viện là hiện một ô trống không mở được.
          status: "raw",
        },
      },
    });
    if (error || !data) {
      return { ok: false, message: detailToMessage(error, "Không tải được thư viện") };
    }
    return { ok: true, data: { items: data.items ?? [], total: data.total ?? 0 } };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

export async function deleteMedia(assetId: string): Promise<Result<null>> {
  try {
    const { error } = await apiClient.DELETE("/media/{asset_id}", {
      params: { path: { asset_id: assetId } },
    } as any); // Using 'any' since we haven't regenerated schema.d.ts yet
    if (error) {
      return { ok: false, message: detailToMessage(error, "Không xoá được ảnh/video") };
    }
    return { ok: true, data: null };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}
