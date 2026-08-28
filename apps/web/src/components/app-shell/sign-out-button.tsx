"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api-client/client";
import { readTokens } from "@/lib/auth/token-store";
import { useSession } from "@/lib/auth/session";
import { useLanguage } from "@/lib/i18n/language-context";
import styles from "./app-shell.module.css";

type WorkspaceInfo = {
  id: string;
  name: string;
  industry: string;
  plan: string;
};

// i18n-data: tên gói hiện trên thanh bên, `t()` dịch ở chỗ render
const PLAN_META: Record<string, { label: string; icon: string; styleClass: string }> = {
  trial: { label: "Gói Trải Nghiệm", icon: "🌱", styleClass: styles.tierTrial },
  tiem_nho: { label: "Gói Khởi Nghiệp", icon: "⚡", styleClass: styles.tierStarter },
  toan_dien: { label: "Gói Chuyên Nghiệp", icon: "💎", styleClass: styles.tierGrowth },
  doanh_nghiep: { label: "Chuỗi Doanh Nghiệp", icon: "👑", styleClass: styles.tierEnterprise },
};

function getInitials(name?: string): string {
  if (!name || !name.trim()) return "H";
  const words = name.trim().split(/\s+/);
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
  return (words[0][0] + words[words.length - 1][0]).toUpperCase();
}

export function SignOutButton() {
  const { signOut } = useSession();
  const { t } = useLanguage();
  const [workspace, setWorkspace] = useState<WorkspaceInfo | null>(null);

  useEffect(() => {
    let cancelled = false;
    const activeId = readTokens()?.activeWorkspaceId;

    apiClient
      .GET("/workspaces")
      .then(({ data }) => {
        if (cancelled || !data) return;
        const list = data as WorkspaceInfo[];
        const active = list.find((w) => w.id === activeId) ?? list[0];
        if (active) setWorkspace(active);
      })
      .catch(() => {});

    return () => {
      cancelled = true;
    };
  }, []);

  const planInfo = workspace?.plan ? PLAN_META[workspace.plan] ?? {
    label: workspace.plan,
    icon: "💎",
    styleClass: styles.tierDefault,
  } : {
    label: "Gói Trải Nghiệm",
    icon: "🌱",
    styleClass: styles.tierTrial,
  };

  const initial = getInitials(workspace?.name);
  const displayName = workspace?.name
    ? t("Chủ tiệm {name}", { name: workspace.name })
    : t("Chủ cơ sở");

  return (
    <div className={styles.userProfileRow}>
      <Link
        href="/app/billing"
        className={styles.userProfileInfoLink}
        title={t("Gói cước")}
      >
        <div className={styles.userAvatar}>
          {initial}
        </div>
        <div className={styles.userMeta}>
          <span className={styles.userEmail} title={displayName}>
            {displayName}
          </span>
          <span className={`${styles.userTier} ${planInfo.styleClass}`}>
            {planInfo.icon} {t(planInfo.label)}
          </span>
        </div>
      </Link>

      <button
        type="button"
        className={styles.signOutIconBtn}
        onClick={() => void signOut()}
        title={t("Đăng xuất")}
        aria-label={t("Đăng xuất")}
      >
        <svg
          width="15"
          height="15"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
          <polyline points="16 17 21 12 16 7" />
          <line x1="21" y1="12" x2="9" y2="12" />
        </svg>
      </button>
    </div>
  );
}
