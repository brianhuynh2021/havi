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

function PlatformIcon({ platform }: { platform: Platform }) {
  switch (platform) {
    case "facebook":
      return (
        <div className={styles.platformIcon} style={{ background: "#1877F2" }}>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
            <path
              d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"
              fill="#FFFFFF"
            />
          </svg>
        </div>
      );
    case "zalo_oa":
      return (
        <div className={styles.platformIcon} style={{ background: "#0068FF" }}>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
            <rect width="24" height="24" rx="6" fill="#0068FF" />
            <path
              d="M17.5 13.5c0 2.2-2.5 4-5.5 4-1 0-1.9-.2-2.7-.6L6.5 18l.8-2.2C6.5 15 6 14.3 6 13.5c0-2.2 2.5-4 5.5-4s6 1.8 6 4z"
              fill="#FFFFFF"
            />
            <path
              d="M9.5 12h5M9.5 14h3"
              stroke="#0068FF"
              strokeWidth="1.2"
              strokeLinecap="round"
            />
          </svg>
        </div>
      );
    case "google_business":
      return (
        <div className={styles.platformIcon} style={{ background: "#F8FAFC", border: "1px solid #E2E8F0" }}>
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
            <path
              d="M17.64 12.2c0-.63-.06-1.25-.16-1.84H12v3.49h3.19c-.14.72-.56 1.34-1.19 1.76v1.45h1.92c1.12-1.04 1.72-2.57 1.72-4.86z"
              fill="#4285F4"
            />
            <path
              d="M12 18c1.62 0 2.98-.54 3.97-1.46l-1.92-1.45c-.54.36-1.23.57-2.05.57-1.57 0-2.91-1.06-3.38-2.49H6.64v1.5C7.63 16.65 9.65 18 12 18z"
              fill="#34A853"
            />
            <path
              d="M8.62 13.17c-.12-.36-.19-.75-.19-1.17s.07-.81.19-1.17V9.33H6.64C6.23 10.14 6 11.05 6 12s.23 1.86.64 2.67l1.98-1.5z"
              fill="#FBBC05"
            />
            <path
              d="M12 7.38c.88 0 1.67.3 2.3.9l1.72-1.72C14.98 5.54 13.62 5 12 5 9.65 5 7.63 6.35 6.64 8.33l1.98 1.5c.47-1.43 1.81-2.45 3.38-2.45z"
              fill="#EA4335"
            />
          </svg>
        </div>
      );
    case "youtube":
      return (
        <div className={styles.platformIcon} style={{ background: "#FF0000" }}>
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
            <path d="M10 8.5v7l6-3.5-6-3.5z" fill="#FFFFFF" />
          </svg>
        </div>
      );
    case "tiktok":
      return (
        <div className={styles.platformIcon} style={{ background: "#0F172A" }}>
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
            <path
              d="M15.5 8.2c-.8-.5-1.3-1.4-1.4-2.4h-2.1v9.2a2.3 2.3 0 11-2.3-2.3c.3 0 .6.1.9.2v-2.2c-.3 0-.6-.1-.9-.1a4.5 4.5 0 104.5 4.5V10.7c1 .7 2.1 1.1 3.3 1.1V9.7c-.7 0-1.4-.6-2-1.5z"
              fill="#25F4EE"
            />
            <path
              d="M15.3 8.4c-.8-.5-1.3-1.4-1.4-2.4h-1.9v9.2a2.3 2.3 0 11-2.3-2.3c.3 0 .6.1.9.2v-2c-.3 0-.6-.1-.9-.1a4.5 4.5 0 104.5 4.5V10.9c1 .7 2.1 1.1 3.3 1.1V9.9c-.7 0-1.5-.6-2.2-1.5z"
              fill="#FE2C55"
            />
            <path
              d="M15.4 8.3c-.8-.5-1.3-1.4-1.4-2.4h-2v9.2a2.3 2.3 0 11-2.3-2.3c.3 0 .6.1.9.2v-2.1c-.3 0-.6-.1-.9-.1a4.5 4.5 0 104.5 4.5V10.8c1 .7 2.1 1.1 3.3 1.1V9.8c-.7 0-1.4-.6-2.1-1.5z"
              fill="#FFFFFF"
            />
          </svg>
        </div>
      );
    default:
      return null;
  }
}

function getPlatformDescription(platform: Platform): string {
  switch (platform) {
    case "facebook":
      return "Tự động đăng bài viết, hình ảnh và Reels lên Fanpage chính thức.";
    case "google_business":
      return "Đăng bài và cập nhật thông tin cơ sở lên hồ sơ Google Business.";
    case "tiktok":
      return "Kết nối tài khoản TikTok để xuất bản video ngắn.";
    case "youtube":
      return "Tự động xuất bản video ngắn lên YouTube Shorts để phủ sóng tìm kiếm.";
    case "zalo_oa":
      return "Gửi bài viết và tin nhắn chăm sóc qua Zalo Official Account.";
  }
}

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
  const isConnected = connection?.status === "connected";

  async function connect() {
    setError(null);
    setBusy(true);
    const result = await startConnect(platform, returnTo, { openPopup: true });
    if (!result.ok) {
      setError(result.message);
      setBusy(false);
      return;
    }
    if (result.data?.popupOpened) {
      let attempts = 0;
      const interval = setInterval(() => {
        attempts += 1;
        onChanged();
        if (attempts >= 8) {
          clearInterval(interval);
          setBusy(false);
        }
      }, 2000);
    } else {
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
    <div className={`${styles.row} ${isConnected ? styles.rowConnected : ""}`}>
      <div className={styles.rowContent}>
        <div className={styles.rowLeft}>
          <PlatformIcon platform={platform} />
          <div className={styles.platformInfo}>
            <div className={styles.rowHeader}>
              <div className={styles.rowLabel}>{label}</div>
              {connection && copy ? (
                <>
                  <Badge tone={copy.needsReconnect ? "warning" : "success"}>
                    {t({
                      vi: copy.label,
                      en:
                        copy.label === "Đã nối"
                          ? "Connected"
                          : copy.label === "Hết hạn"
                            ? "Expired"
                            : "Revoked",
                    })}
                  </Badge>
                  {connection.account_name ? (
                    <span className={styles.accountName}>
                      <span className={styles.accountPrefix}>
                        {platform === "facebook"
                          ? "Fanpage: "
                          : platform === "google_business"
                            ? "Địa điểm: "
                            : platform === "tiktok"
                              ? "Kênh: "
                              : "Tài khoản: "}
                      </span>
                      <strong>{connection.account_name}</strong>
                    </span>
                  ) : null}
                </>
              ) : (
                <Badge tone="neutral">{t("settings.notConnected", "Chưa kết nối")}</Badge>
              )}
            </div>
            <p className={styles.hint}>
              {copy?.hint || getPlatformDescription(platform)}
            </p>
          </div>
        </div>

        <div className={styles.rowRight}>
          {connection ? (
            <>
              {copy?.needsReconnect ? (
                <Button variant="primary" onClick={connect} disabled={busy}>
                  {busy
                    ? t({ vi: "Đang mở…", en: "Connecting…" })
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
                ? t({ vi: "Đang mở…", en: "Opening…" })
                : t({ vi: "Kết nối", en: "Connect" })}
            </Button>
          )}
        </div>
      </div>

      {error ? (
        <div className={styles.error} role="alert">
          {error}
        </div>
      ) : null}
    </div>
  );
}
