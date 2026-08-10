"use client";

import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Input, Textarea } from "@/components/ui/input";
import { ConnectionList } from "@/features/connections/connection-list";
import { industryOptions } from "@/features/onboarding/onboarding.fixture";
import {
  formatBannedClaims,
  loadSettings,
  parseBannedClaims,
  saveSettings,
  type Industry,
  type SettingsData,
} from "./settings.api";
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
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

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
      setError("Tên tiệm cần ít nhất 2 ký tự.");
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
    if (result.ok) {
      setForm(toFormState(result.data));
      setSuccess("Đã lưu giọng thương hiệu.");
    } else {
      setError(result.message);
    }
    setSaving(false);
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>Cài đặt</h1>
        <p className={styles.subtitle}>
          Những thông tin này giúp Havi viết đúng cách xưng hô, ngành hàng và
          tránh các câu cam kết quá mức.
        </p>
      </header>

      <section className={styles.section} aria-labelledby="brand-voice-title">
        <h2 className={styles.sectionTitle} id="brand-voice-title">
          Giọng thương hiệu
        </h2>
        <p className={styles.sectionHint}>
          Nội dung đã duyệt vẫn là quyết định cuối cùng; Havi chỉ dùng phần này
          làm nền khi tạo bản nháp mới.
        </p>

        {error ? (
          <p className={styles.alert} role="alert">
            {error}
          </p>
        ) : null}

        <form className={styles.form} onSubmit={handleSubmit}>
          <div className={styles.grid}>
            <label className={styles.field}>
              <span className={styles.label}>Tên tiệm</span>
              <Input
                value={form.name}
                disabled={loading || saving}
                onChange={(event) =>
                  setForm((current) => ({ ...current, name: event.target.value }))
                }
              />
            </label>

            <label className={styles.field}>
              <span className={styles.label}>Ngành</span>
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
            <span className={styles.label}>Cách Havi nên viết</span>
            <Textarea
              value={form.tone}
              disabled={loading || saving}
              placeholder="Ví dụ: thân thiện, gọi khách là chị/em, nói ngắn gọn và không dùng từ quá chuyên môn."
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
    </div>
  );
}
