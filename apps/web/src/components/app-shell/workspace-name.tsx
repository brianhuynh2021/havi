"use client";
import { useLanguage } from "@/lib/i18n/language-context";

import { useEffect, useRef, useState } from "react";
import { apiClient } from "@/lib/api-client/client";
import { readTokens, writeTokens } from "@/lib/auth/token-store";
import styles from "./app-shell.module.css";

type WorkspaceItem = {
  id: string;
  name: string;
  industry: string;
  plan: string;
};

function getIndustryIcon(industry?: string) {
  switch (industry) {
    case "spa":
      return "💆‍♀️";
    case "salon":
      return "💇‍♂️";
    case "clinic":
    case "dentistry":
      return "🦷";
    case "restaurant":
    case "cafe":
      return "☕";
    case "education":
    case "training":
      return "🏫";
    default:
      return "🏢";
  }
}

/**
 * Tên tiệm trong thẻ workspace kèm Dropdown chuyển đổi không gian làm việc.
 */
type BrandGroup = { organizationName: string; brands: WorkspaceItem[] };

export function WorkspaceName() {
  const {
    t
  } = useLanguage();

  const [workspaces, setWorkspaces] = useState<WorkspaceItem[]>([]);
  /** Thương hiệu gom theo tổ chức — để chuỗi nhiều chi nhánh không thành một
   *  danh sách phẳng dài dằng dặc không biết cái nào thuộc công ty nào. */
  const [groups, setGroups] = useState<BrandGroup[]>([]);
  const [activeWorkspace, setActiveWorkspace] = useState<WorkspaceItem | null>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [isSwitching, setIsSwitching] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    const activeId = readTokens()?.activeWorkspaceId;

    // Đọc từ `/organizations`: nó trả sẵn thương hiệu của từng tổ chức, nên
    // dựng menu chỉ tốn một request thay vì N+1.
    apiClient
      .GET("/organizations")
      .then(({ data }) => {
        if (cancelled || !data) return;
        const orgGroups: BrandGroup[] = data.map((entry) => ({
          organizationName: entry.organization.name,
          brands: entry.brands as unknown as WorkspaceItem[],
        }));
        const flat = orgGroups.flatMap((g) => g.brands);
        setGroups(orgGroups);
        setWorkspaces(flat);
        const active = flat.find((w) => w.id === activeId) ?? flat[0];
        if (active) setActiveWorkspace(active);
      })
      .catch(() => {
        // Tên tiệm là thông tin phụ — hỏng thì để trống, không chặn cả app.
      });

    return () => {
      cancelled = true;
    };
  }, []);

  // Đóng dropdown khi click ra ngoài
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSelectWorkspace = async (w: WorkspaceItem) => {
    if (w.id === activeWorkspace?.id) {
      setIsOpen(false);
      return;
    }
    setIsSwitching(true);
    try {
      const res = await apiClient.POST("/workspaces/{workspace_id}/activate", {
        params: { path: { workspace_id: w.id } },
      });
      if (res.data) {
        writeTokens({
          accessToken: res.data.access_token,
          refreshToken: res.data.refresh_token,
          activeWorkspaceId: res.data.active_workspace_id ?? w.id,
          needsOnboarding: res.data.needs_onboarding ?? false,
        });
        window.location.reload();
      }
    } catch (err) {
      console.error("Failed to activate workspace", err);
      setIsSwitching(false);
    }
  };

  if (!activeWorkspace) {
    return <p className={styles.workspaceName}>&nbsp;</p>;
  }

  return (
    <div ref={containerRef} style={{ position: "relative", width: "100%" }}>
      <button
        type="button"
        className={styles.workspaceSwitcherBtn}
        onClick={() => setIsOpen(!isOpen)}
        title={t("Bấm để đổi tiệm / không gian làm việc")}
        disabled={isSwitching}
      >
        <div className={styles.workspaceAvatar}>
          {getIndustryIcon(activeWorkspace.industry)}
        </div>
        <div className={styles.workspaceTextCol}>
          {/* `title` để rê chuột đọc đủ: chuỗi nhiều chi nhánh có tên gần
              giống nhau, và cắt ở giữa làm mất đúng phần phân biệt. */}
          <span className={styles.workspaceNameText} title={activeWorkspace.name}>
            {isSwitching ? "Đang chuyển…" : activeWorkspace.name}
          </span>
          <span className={styles.workspaceSubText}>
            {workspaces.length > 1 ? `${workspaces.length} thương hiệu` : "Thương hiệu"}
          </span>
        </div>
        {workspaces.length > 1 && (
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            style={{
              transform: isOpen ? "rotate(180deg)" : "none",
              transition: "transform 0.2s ease",
              opacity: 0.7,
              flexShrink: 0,
            }}
          >
            <polyline points="6 9 12 15 18 9" />
          </svg>
        )}
      </button>

      {isOpen && workspaces.length > 0 && (
        <div className={styles.workspaceSwitcherDropdown}>
          {/* Chỉ hiện tên tổ chức khi thật sự có nhiều — với chủ tiệm đơn lẻ,
              một tiêu đề "Spa An Nhiên" phía trên đúng một mục tên "Spa An
              Nhiên" là nhiễu thuần tuý. */}
          {groups.length > 1 || workspaces.length > 1 ? (
            groups.map((group) => (
              <div key={group.organizationName}>
                <div className={styles.dropdownHeader}>{group.organizationName}</div>
                {group.brands.map((w) => (
                  <button
                    key={w.id}
                    type="button"
                    className={`${styles.workspaceOption} ${
                      w.id === activeWorkspace.id ? styles.workspaceOptionActive : ""
                    }`}
                    onClick={() => handleSelectWorkspace(w)}
                  >
                    <span className={styles.workspaceAvatar}>
                      {getIndustryIcon(w.industry)}
                    </span>
                    <span className={styles.workspaceOptionName}>{w.name}</span>
                    {w.id === activeWorkspace.id ? <span>✓</span> : null}
                  </button>
                ))}
              </div>
            ))
          ) : null}
          {groups.length > 1 || workspaces.length > 1 ? null : workspaces.map((w) => {
            const isActive = w.id === activeWorkspace.id;
            return (
              <button
                key={w.id}
                type="button"
                className={`${styles.workspaceOption} ${isActive ? styles.workspaceOptionActive : ""}`}
                onClick={() => handleSelectWorkspace(w)}
              >
                <div style={{ display: "flex", flexDirection: "column", gap: "2px", textAlign: "left" }}>
                  <span style={{ fontSize: "13px", fontWeight: isActive ? 700 : 500 }}>{w.name}</span>
                  <span style={{ fontSize: "10.5px", opacity: 0.6 }}>
                    {w.plan === "TOAN_DIEN" ? "Gói Toàn Diện" : "Bản Dùng Thử"}
                  </span>
                </div>
                {isActive && (
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" strokeWidth="3">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                )}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
