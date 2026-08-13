"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useLanguage } from "@/lib/i18n/language-context";
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
  connection: PlatformConnection | undefined;
  returnTo: OAuthReturnTarget;
  onChanged: () => void;
};

export function ConnectionCard({
  platform,
  label,
  connection,
  returnTo,
  onChanged,
}: Props) {
  const { t } = useLanguage();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const copy = connection ? statusCopy(connection.status) : null;

  async function connect() {
    setError(null);
    setBusy(true);
    const result = await startConnect(platform, returnTo);
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
              {t({ vi: copy.label, en: copy.label === "Đã nối" ? "Connected" : copy.label === "Hết hạn" ? "Expired" : "Revoked" })}
            </Badge>
            {connection.account_name ? (
              <span className={styles.accountName}>{connection.account_name}</span>
            ) : null}
          </>
        ) : (
          <Badge tone="neutral">{t("settings.notConnected", "Chưa kết nối")}</Badge>
        )}
      </div>

      {copy?.hint ? <p className={styles.hint}>{copy.hint}</p> : null}

      <div className={styles.rowActions}>
        {connection ? (
          <>
            {copy?.needsReconnect ? (
              <Button variant="primary" onClick={connect} disabled={busy}>
                {busy
                  ? t({ vi: `Đang mở ${label}…`, en: `Connecting ${label}…` })
                  : t({ vi: "Nối lại", en: "Reconnect" })}
              </Button>
            ) : null}
            <Button variant="outline" onClick={remove} disabled={busy}>
              {t({ vi: "Ngắt kết nối", en: "Disconnect" })}
            </Button>
          </>
        ) : (
          <Button variant="primary" onClick={connect} disabled={busy}>
            {busy
              ? t({ vi: `Đang mở ${label}…`, en: `Connecting ${label}…` })
              : t({ vi: `Kết nối ${label}`, en: `Connect ${label}` })}
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

