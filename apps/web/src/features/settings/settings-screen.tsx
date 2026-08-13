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

  async function handleDeleteWorkspace() {
    if (!form.workspaceId) return;
    const confirmed = window.confirm(
      t({
        vi: "Bạn có chắc chắn muốn xoá workspace này? Tất cả kênh đã kết nối và dữ liệu bài đăng sẽ bị xoá.",
        en: "Are you sure you want to delete this workspace? Connected channels and post history will be deleted.",
      }),
    );
    if (!confirmed) return;

    setDeletingWorkspace(true);
    setError("");
    const result = await deleteWorkspace(form.workspaceId);
    if (result.ok) {
      clearTokens();
      window.location.href = "/onboarding";
    } else {
      setError(result.message);
      setDeletingWorkspace(false);
    }
  }

  async function handleDeleteAccount() {
    const confirmed = window.confirm(
      t({
        vi: "Bạn có chắc chắn muốn xoá tài khoản Havi? Hành động này không thể hoàn tác.",
        en: "Are you sure you want to delete your Havi account? This action cannot be undone.",
      }),
    );
    if (!confirmed) return;

    setDeletingAccount(true);
    setError("");
    const result = await deleteAccount();
    if (result.ok) {
      clearTokens();
      window.location.href = "/login";
    } else {
      setError(result.message);
      setDeletingAccount(false);
    }
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>{t("settings.title", "Cài Đặt Hệ Thống")}</h1>
        <p className={styles.subtitle}>
          {t("settings.subtitle", "Quản lý doanh nghiệp, tài khoản và kết nối kênh")}
        </p>
      </header>

      <section className={styles.section} aria-labelledby="brand-voice-title">
        <h2 className={styles.sectionTitle} id="brand-voice-title">
          {t("settings.brandKitTab", "Bộ nhận diện thương hiệu")}
        </h2>
        <p className={styles.sectionHint}>
          {t({
            vi: "Nội dung đã duyệt vẫn là quyết định cuối cùng; Havi chỉ dùng phần này làm nền khi tạo bản nháp mới.",
            en: "Havi uses brand voice guidelines when generating drafts for your review.",
          })}
        </p>

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
                vi: "Ví dụ: thân thiện, gần gũi, nói ngắn gọn...",
                en: "e.g., professional yet warm, concise and engaging...",
              })}
              onChange={(event) =>
                setForm((current) => ({ ...current, tone: event.target.value }))
              }
            />
          </label>

          <label className={styles.field}>
            <span className={styles.label}>Không được hứa</span>
            <Textarea
              value={form.bannedClaimsText}
              disabled={loading || saving}
              placeholder={"Mỗi dòng một câu, ví dụ:\ncam kết trắng da sau 1 lần\nđảm bảo tăng doanh thu"}
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

      <section className={styles.section} aria-labelledby="connections-title">
        <h2 className={styles.sectionTitle} id="connections-title">
          Kênh đã nối
        </h2>
        <p className={styles.sectionHint}>
          Kênh nào hết hạn hoặc mất quyền, chị nối lại ở đây để lịch đăng chạy tiếp.
        </p>
        <ConnectionList returnTo="settings" />
      </section>

      <section className={`${styles.section} ${styles.dangerSection}`} aria-labelledby="danger-title">
        <h2 className={styles.sectionTitle} id="danger-title">
          Vùng nguy hiểm
        </h2>
        <p className={styles.sectionHint}>
          Xoá tiệm hoặc tài khoản sẽ gỡ bỏ dữ liệu vĩnh viễn và không thể khôi phục.
        </p>

        <div className={styles.dangerCard}>
          <div className={styles.dangerTitle}>Xoá tiệm hiện tại</div>
          <div className={styles.dangerText}>
            Xoá toàn bộ bài nháp, kết nối Facebook, hình ảnh và cài đặt của tiệm này.
          </div>
          <div className={styles.dangerActions}>
            <button
              type="button"
              className={styles.dangerButtonOutline}
              disabled={loading || deletingWorkspace || deletingAccount}
              onClick={handleDeleteWorkspace}
            >
              {deletingWorkspace ? "Đang xoá tiệm..." : "Xoá tiệm này"}
            </button>
          </div>
        </div>

        <div className={styles.dangerCard}>
          <div className={styles.dangerTitle}>Xoá tài khoản người dùng</div>
          <div className={styles.dangerText}>
            Xoá vĩnh viễn tài khoản Havi của chị và thu hồi toàn bộ đăng nhập.
          </div>
          <div className={styles.dangerActions}>
            <button
              type="button"
              className={styles.dangerButton}
              disabled={loading || deletingWorkspace || deletingAccount}
              onClick={handleDeleteAccount}
            >
              {deletingAccount ? "Đang xoá tài khoản..." : "Xoá tài khoản"}
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}

