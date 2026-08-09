"use client";

import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api-client/client";
import { readTokens } from "@/lib/auth/token-store";
import styles from "./app-shell.module.css";

/**
 * Tên tiệm trong thẻ workspace.
 *
 * Trước đây hardcode "Spa An Nhiên" — tên tiệm mẫu trong prototype. Chủ tiệm
 * thật đăng nhập vào thấy tên tiệm người khác trên sidebar là lỗi mất niềm tin
 * nặng, kể cả khi mọi thứ khác đúng.
 *
 * Đọc `GET /workspaces` rồi lọc theo `activeWorkspaceId` trong JWT: danh sách
 * này đã được backend scope theo user, nên không có đường thấy tiệm người khác.
 */
export function WorkspaceName() {
  const [name, setName] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const activeId = readTokens()?.activeWorkspaceId;

    apiClient
      .GET("/workspaces")
      .then(({ data }) => {
        if (cancelled || !data) return;
        const active = data.find((w) => w.id === activeId) ?? data[0];
        if (active) setName(active.name);
      })
      .catch(() => {
        // Tên tiệm là thông tin phụ — hỏng thì để trống, không chặn cả app.
      });

    return () => {
      cancelled = true;
    };
  }, []);

  // Chưa có tên thì để trống chỗ đó thay vì hiện placeholder: một cái tên sai
  // đọc như thật, còn khoảng trắng thì rõ ràng là đang tải.
  return <p className={styles.workspaceName}>{name ?? " "}</p>;
}
