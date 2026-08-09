"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  disconnect,
  startConnect,
  statusCopy,
  type OAuthReturnTarget,
  type Platform,
  type PlatformConnection,
} from "./connections.api";
import styles from "./connections.module.css";

type Props = {
  platform: Platform;
  label: string;
  /** `undefined` = chưa nối bao giờ. Khác `revoked` (đã nối rồi mất quyền) — hai
   * trạng thái này cần hai câu khác nhau, nên không gộp thành boolean. */
  connection: PlatformConnection | undefined;
  /** Màn đang đứng, để cấp quyền xong quay về đúng đây. */
  returnTo: OAuthReturnTarget;
  onChanged: () => void;
};

/**
 * Một hàng kênh: trạng thái + hành động tương ứng.
 *
 * Dùng chung cho onboarding bước 2 và trang Cài đặt — cùng một kênh không được
 * hiện hai kiểu ở hai chỗ, nhất là khi một chỗ nói "Đã nối" mà chỗ kia nói "Hết
 * hạn".
 */
export function ConnectionCard({
  platform,
  label,
  connection,
  returnTo,
  onChanged,
}: Props) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const copy = connection ? statusCopy(connection.status) : null;

  async function connect() {
    setError(null);
    setBusy(true);
    const result = await startConnect(platform, returnTo);
    // Thành công thì trang đang điều hướng sang Facebook — giữ `busy` để chủ
    // tiệm không bấm lần nữa trong lúc chờ chuyển trang.
    if (!result.ok) {
      setError(result.message);
      setBusy(false);
    }
  }

  async function remove() {
    setError(null);
    setBusy(true);
    const result = await disconnect(platform);
    setBusy(false);
    if (!result.ok) {
      setError(result.message);
      return;
    }
    onChanged();
  }

  return (
    <div className={styles.row}>
      <div className={styles.rowMain}>
        <div className={styles.rowLabel}>{label}</div>
        {connection && copy ? (
          <>
            <Badge tone={copy.needsReconnect ? "warning" : "success"}>
              {copy.label}
            </Badge>
            {connection.account_name ? (
              <span className={styles.accountName}>{connection.account_name}</span>
            ) : null}
          </>
        ) : (
          <Badge tone="neutral">Chưa nối</Badge>
        )}
      </div>

      {copy?.hint ? <p className={styles.hint}>{copy.hint}</p> : null}

      <div className={styles.rowActions}>
        {connection ? (
          <>
            {copy?.needsReconnect ? (
              <Button variant="primary" onClick={connect} disabled={busy}>
                {busy ? "Đang mở Facebook…" : "Nối lại"}
              </Button>
            ) : null}
            <Button variant="outline" onClick={remove} disabled={busy}>
              Ngắt kênh
            </Button>
          </>
        ) : (
          <Button variant="primary" onClick={connect} disabled={busy}>
            {busy ? "Đang mở Facebook…" : `Kết nối ${label}`}
          </Button>
        )}
      </div>

      {error ? (
        <p className={styles.error} role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}
