"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/input";
import {
  listVersions,
  updateItemText,
  type ContentItem,
  type ContentItemVersion,
} from "./content-creation.api";
import styles from "./content-creation.module.css";

const vnDateTime = new Intl.DateTimeFormat("vi-VN", {
  timeZone: "Asia/Ho_Chi_Minh",
  day: "2-digit",
  month: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});

type Props = {
  item: ContentItem;
  onSaved: (item: ContentItem) => void;
  onClose: () => void;
};

export function DraftEditor({ item, onSaved, onClose }: Props) {
  const [text, setText] = useState(item.text);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [versions, setVersions] = useState<ContentItemVersion[] | null>(null);
  const [loadingVersions, setLoadingVersions] = useState(false);

  const dirty = text.trim() !== item.text.trim();

  async function save() {
    if (!dirty || !text.trim()) return;
    setSaving(true);
    setError(null);
    const result = await updateItemText(item.id, text.trim());
    setSaving(false);
    if (!result.ok) {
      setError(result.message);
      return;
    }
    // Lịch sử vừa có thêm bản mới — bỏ cache để lần mở sau đọc lại từ server.
    setVersions(null);
    onSaved(result.data);
  }

  async function toggleVersions() {
    if (versions) {
      setVersions(null);
      return;
    }
    setLoadingVersions(true);
    const result = await listVersions(item.id);
    setLoadingVersions(false);
    if (result.ok) setVersions(result.data);
    else setError(result.message);
  }

  return (
    <div className={styles.editor}>
      <Textarea
        aria-label="Nội dung bài"
        rows={6}
        value={text}
        onChange={(e) => setText(e.target.value)}
      />

      {error ? (
        <p className={styles.editorError} role="alert">
          {error}
        </p>
      ) : null}

      <div className={styles.editorActions}>
        <Button variant="primary" onClick={save} disabled={!dirty || saving}>
          {saving ? "Đang lưu…" : "Lưu bản sửa"}
        </Button>
        <Button variant="outline" onClick={onClose}>
          Đóng
        </Button>
        <Button variant="outline" onClick={toggleVersions}>
          {versions ? "Ẩn lịch sử" : `Lịch sử (bản ${item.version_no})`}
        </Button>
      </div>

      {loadingVersions ? (
        <p className={styles.editorHint}>Đang tải lịch sử…</p>
      ) : null}

      {versions ? (
        versions.length === 0 ? (
          <p className={styles.editorHint}>Bài này chưa từng được sửa.</p>
        ) : (
          <ol className={styles.versionList}>
            {versions.map((v) => (
              <li key={v.version_no} className={styles.versionItem}>
                <div className={styles.versionMeta}>
                  Bản {v.version_no} · {vnDateTime.format(new Date(v.edited_at))}
                </div>
                <p className={styles.versionText}>{v.text}</p>
              </li>
            ))}
          </ol>
        )
      ) : null}
    </div>
  );
}
