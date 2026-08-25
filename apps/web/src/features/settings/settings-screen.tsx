"use client";

import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Input, Textarea } from "@/components/ui/input";
import { ConnectionList } from "@/features/connections/connection-list";
import { industryOptions } from "@/features/onboarding/onboarding.fixture";
import { clearTokens } from "@/lib/auth/token-store";
import {
  deleteAccount,
  deleteWorkspace,
  formatBannedClaims,
  loadSettings,
  parseBannedClaims,
  saveSettings,
  type Industry,
  type SettingsData,
} from "./settings.api";
import { useLanguage } from "@/lib/i18n/language-context";
import { DangerConfirmModal, type DangerActionType } from "./danger-confirm-modal";
import styles from "./settings-screen.module.css";

type FormState = {
  workspaceId: string;
  name: string;
  industry: Industry;
  tone: string;
  bannedClaimsText: string;
};

const EMPTY_FORM: FormState = {
  workspaceId: "",
  name: "",
  industry: "spa",
  tone: "",
  bannedClaimsText: "",
};

function getBannedClaimsPlaceholder(industry?: string): string {
  const ind = (industry || "").toLowerCase();
  if (ind.includes("education") || ind.includes("giáo dục") || ind.includes("đào tạo")) {
    return "Mỗi dòng một câu cấm kỵ, ví dụ:\ncam kết học xong lương nghìn đô\nbao đậu chứng chỉ 100% không cần học";
  }
  if (ind.includes("restaurant") || ind.includes("fnb") || ind.includes("ăn uống") || ind.includes("cà phê")) {
    return "Mỗi dòng một câu cấm kỵ, ví dụ:\nquán ăn ngon số 1 Việt Nam\nchữa dứt điểm mọi cơn đói";
  }
  if (ind.includes("clinic") || ind.includes("y tế") || ind.includes("phòng khám") || ind.includes("nha khoa")) {
    return "Mỗi dòng một câu cấm kỵ, ví dụ:\nchữa khỏi dứt điểm 100%\nkhông bao giờ tái phát";
  }
  if (ind.includes("spa") || ind.includes("beauty") || ind.includes("làm đẹp") || ind.includes("salon")) {
    return "Mỗi dòng một câu cấm kỵ, ví dụ:\ncam kết trắng da sau 1 lần\nđảm bảo trị mụn dứt điểm 100%";
  }
  return "Mỗi dòng một câu cấm kỵ, ví dụ:\ncam kết hiệu quả 100% sau 1 ngày\nđảm bảo hoàn tiền vô điều kiện trọn đời";
}

function toFormState(data: SettingsData): FormState {
  return {
    workspaceId: data.workspace.id,
    name: data.workspace.name,
    industry: data.workspace.industry,
    tone: data.profile.tone,
    bannedClaimsText: formatBannedClaims(data.profile.banned_claims),
  };
}

export function SettingsScreen() {
  const { t } = useLanguage();
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const [deletingWorkspace, setDeletingWorkspace] = useState(false);
  const [deletingAccount, setDeletingAccount] = useState(false);
  const [dangerModal, setDangerModal] = useState<DangerActionType | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError("");
      const result = await loadSettings();
      if (cancelled) return;
      if (result.ok) {
        setForm(toFormState(result.data));
      } else {
        setError(result.message);
      }
      setLoading(false);
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  const canSave = useMemo(
    () => form.workspaceId && form.name.trim().length >= 2 && !saving && !loading,
    [form.name, form.workspaceId, loading, saving],
  );

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSuccess("");

    const name = form.name.trim();
    if (name.length < 2) {
      setError(t({ vi: "Tên tiệm cần ít nhất 2 ký tự.", en: "Business name must be at least 2 characters." }));
      return;
    }

    setSaving(true);
    const result = await saveSettings({
      workspaceId: form.workspaceId,
      name,
      industry: form.industry,
      tone: form.tone.trim(),
      bannedClaims: parseBannedClaims(form.bannedClaimsText),
    });
    setSaving(false);

    if (result.ok) {
      setForm(toFormState(result.data));
      setSuccess(t({ vi: "Đã lưu cài đặt giọng thương hiệu thành công.", en: "Settings updated successfully." }));
    } else {
      setError(result.message);
    }
  }

  async function handleConfirmDeleteWorkspace() {
    if (!form.workspaceId) return;
    setDeletingWorkspace(true);
    setError("");
    const result = await deleteWorkspace(form.workspaceId);
    if (result.ok) {
      clearTokens();
      window.location.href = "/onboarding";
    } else {
      setError(result.message);
      setDeletingWorkspace(false);
      setDangerModal(null);
    }
  }

  async function handleConfirmDeleteAccount() {
    setDeletingAccount(true);
    setError("");
    const result = await deleteAccount();
    if (result.ok) {
      clearTokens();
      window.location.href = "/login";
    } else {
      setError(result.message);
      setDeletingAccount(false);
      setDangerModal(null);
    }
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.headerBadge}>⚙️ Thiết lập hệ thống</div>
        <h1 className={styles.title}>{t("settings.title", "Cài Đặt Hệ Thống")}</h1>
        <p className={styles.subtitle}>
          {t("settings.subtitle", "Quản lý hồ sơ thương hiệu, phong cách viết bài của AI và các kênh xuất bản")}
        </p>
      </header>

      {/* Card 1: Bộ nhận diện thương hiệu */}
      <section className={styles.sectionCard} aria-labelledby="brand-voice-title">
        <div className={styles.cardHeader}>
          <div className={styles.cardIcon}>
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 20h9" />
              <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" />
            </svg>
          </div>
          <div className={styles.cardHeaderText}>
            <h2 className={styles.sectionTitle} id="brand-voice-title">
              {t("settings.brandKitTab", "Bộ nhận diện thương hiệu")}
            </h2>
            <p className={styles.sectionHint}>
              {t({
                vi: "Nội dung đã duyệt vẫn là quyết định cuối cùng; Havi dùng thông tin này làm nền tảng khi AI sáng tạo nội dung.",
                en: "Havi uses brand voice guidelines when generating drafts for your review.",
              })}
            </p>
          </div>
        </div>

        {error ? (
          <p className={styles.alert} role="alert">
            {error}
          </p>
        ) : null}

        <form className={styles.form} onSubmit={handleSubmit}>
          <div className={styles.grid}>
            <label className={styles.field}>
              <span className={styles.label}>{t("auth.businessName", "Tên doanh nghiệp / Cửa hàng")}</span>
              <Input
                value={form.name}
                disabled={loading || saving}
                onChange={(event) =>
                  setForm((current) => ({ ...current, name: event.target.value }))
                }
              />
            </label>

            <label className={styles.field}>
              <span className={styles.label}>{t({ vi: "Ngành nghề", en: "Industry" })}</span>
              <select
                className={styles.select}
                value={form.industry}
                disabled={loading || saving}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    industry: event.target.value as Industry,
                  }))
                }
              >
                {industryOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <label className={styles.field}>
            <span className={styles.label}>{t({ vi: "Giọng văn của Havi", en: "Tone of Voice" })}</span>
            <Textarea
              value={form.tone}
              disabled={loading || saving}
              placeholder={t({
                vi: "Ví dụ: thân thiện, gần gũi, ấm áp, xưng hô thân mật, ngắn gọn súc tích...",
                en: "e.g., professional yet warm, concise and engaging...",
              })}
              onChange={(event) =>
                setForm((current) => ({ ...current, tone: event.target.value }))
              }
            />
          </label>

          <label className={styles.field}>
            <span className={styles.label}>Không được hứa (Banned Claims)</span>
            <Textarea
              value={form.bannedClaimsText}
              disabled={loading || saving}
              placeholder={getBannedClaimsPlaceholder(form.industry)}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  bannedClaimsText: event.target.value,
                }))
              }
            />
          </label>

          <div className={styles.actions}>
            <Button type="submit" disabled={!canSave}>
              {saving ? "Đang lưu..." : "Lưu thay đổi"}
            </Button>
            {loading ? <span className={styles.status}>Đang tải...</span> : null}
            {success ? (
              <span className={`${styles.status} ${styles.success}`}>{success}</span>
            ) : null}
          </div>
        </form>
      </section>

      {/* Card 2: Kênh đã nối */}
      <section className={styles.sectionCard} aria-labelledby="connections-title">
        <div className={styles.cardHeader}>
          <div className={styles.cardIcon}>
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
              <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
            </svg>
          </div>
          <div className={styles.cardHeaderText}>
            <h2 className={styles.sectionTitle} id="connections-title">
              Kênh xuất bản đã kết nối
            </h2>
            <p className={styles.sectionHint}>
              Kênh nào hết hạn hoặc mất quyền, bạn kết nối lại ở đây để lịch tự động đăng tiếp tục hoạt động.
            </p>
          </div>
        </div>
        <ConnectionList returnTo="settings" />
      </section>

      {/* Card 3: Vùng nguy hiểm */}
      <section className={`${styles.sectionCard} ${styles.dangerCardContainer}`} aria-labelledby="danger-title">
        <div className={styles.cardHeader}>
          <div className={`${styles.cardIcon} ${styles.dangerIcon}`}>
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
              <line x1="12" y1="9" x2="12" y2="13" />
              <line x1="12" y1="17" x2="12.01" y2="17" />
            </svg>
          </div>
          <div className={styles.cardHeaderText}>
            <h2 className={styles.sectionTitle} id="danger-title">
              Vùng nguy hiểm
            </h2>
            <p className={styles.sectionHint}>
              Chỉ xoá dữ liệu và ngắt kết nối bên trong ứng dụng Havi. Fanpage, kênh TikTok/YouTube và các bài đã đăng trên mạng xã hội của bạn KHÔNG bị ảnh hưởng.
            </p>
          </div>
        </div>

        <div className={styles.dangerGrid}>
          <div className={styles.dangerSubCard}>
            <div className={styles.dangerSubInfo}>
              <div className={styles.dangerTitle}>Xoá tiệm trên Havi</div>
              <div className={styles.dangerText}>
                Xoá toàn bộ bài nháp, ngắt kết nối các kênh và xoá cài đặt của tiệm này trên Havi. Thao tác không xoá Fanpage hoặc tài khoản mạng xã hội tại nền tảng bên ngoài.
              </div>
            </div>
            <button
              type="button"
              className={styles.dangerButtonOutline}
              disabled={loading || deletingWorkspace || deletingAccount}
              onClick={() => setDangerModal("workspace")}
            >
              {deletingWorkspace ? "Đang xoá tiệm..." : "Xoá tiệm này"}
            </button>
          </div>

          <div className={styles.dangerSubCard}>
            <div className={styles.dangerSubInfo}>
              <div className={styles.dangerTitle}>Xoá tài khoản Havi</div>
              <div className={styles.dangerText}>
                Xoá vĩnh viễn tài khoản đăng nhập Havi của bạn và thu hồi mọi phiên đăng nhập trên hệ thống Havi.
              </div>
            </div>
            <button
              type="button"
              className={styles.dangerButton}
              disabled={loading || deletingWorkspace || deletingAccount}
              onClick={() => setDangerModal("account")}
            >
              {deletingAccount ? "Đang xoá tài khoản..." : "Xoá tài khoản"}
            </button>
          </div>
        </div>
      </section>

      {/* Stanford / MIT Danger Confirm Modal */}
      {dangerModal && (
        <DangerConfirmModal
          key={dangerModal}
          isOpen={Boolean(dangerModal)}
          type={dangerModal}
          targetName={form.name || "tiệm này"}
          isDeleting={dangerModal === "workspace" ? deletingWorkspace : deletingAccount}
          onClose={() => setDangerModal(null)}
          onConfirm={dangerModal === "workspace" ? handleConfirmDeleteWorkspace : handleConfirmDeleteAccount}
        />
      )}
    </div>
  );
}
