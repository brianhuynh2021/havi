"use client";

/**
 * Quyền của người đang đăng nhập trong workspace đang mở.
 *
 * Dùng để **không hiện nút người dùng không bấm được**. Đây thuần tuý là trải
 * nghiệm — backend vẫn kiểm lại ở từng endpoint, vì ẩn nút không phải là phân
 * quyền: ai cũng gọi thẳng API được. Nếu hook này hỏng, hậu quả là một nút thừa
 * và một thông báo 403, không phải một lỗ hổng.
 *
 * Vì vậy trạng thái "chưa biết" (`loading`) **hiện nút** thay vì ẩn: ẩn rồi mới
 * hiện gây nháy, và người có quyền sẽ thấy nút biến mất ngay sau khi vào trang.
 */

import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api-client/client";

export const PERMISSIONS = {
  draftContent: "draft_content",
  approveContent: "approve_content",
  replyConversation: "reply_conversation",
  manageConnections: "manage_connections",
  manageMembers: "manage_members",
  viewAuditLog: "view_audit_log",
} as const;

export type PermissionKey = (typeof PERMISSIONS)[keyof typeof PERMISSIONS];

type State = {
  /** `false` cho tới khi đọc được vai thật. "Chưa biết" ≠ "không có quyền". */
  known: boolean;
  role: string | null;
  permissions: string[];
};

export function usePermissions(): State & { can: (permission: PermissionKey) => boolean } {
  const [state, setState] = useState<State>({
    known: false,
    role: null,
    permissions: [],
  });

  useEffect(() => {
    let cancelled = false;
    apiClient
      .GET("/auth/me")
      .then(({ data }) => {
        if (cancelled) return;
        setState({
          // Chỉ coi là "đã biết" khi thật sự có vai. Tài khoản chưa chọn
          // workspace trả `role: null` — lúc đó vẫn là chưa biết.
          known: Boolean(data?.role),
          role: data?.role ?? null,
          permissions: data?.permissions ?? [],
        });
      })
      .catch(() => {
        // Hỏng thì vẫn là chưa biết — và chưa biết nghĩa là vẫn hiện nút.
        if (!cancelled) setState((prev) => ({ ...prev, known: false }));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return {
    ...state,
    can: (permission) => (state.known ? state.permissions.includes(permission) : true),
  };
}
