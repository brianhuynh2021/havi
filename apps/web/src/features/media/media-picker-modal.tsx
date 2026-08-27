"use client";
import { useLanguage, type Translate } from "@/lib/i18n/language-context";

import React, { useEffect, useState, useCallback } from "react";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/state-views";
import { listMedia, type MediaAsset } from "./media.api";
import styles from "./media-picker-modal.module.css";

interface MediaPickerModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelect: (asset: MediaAsset) => void;
}

function formatSize(bytes: number | null | undefined): string | null {
  if (!bytes) return null;
  const mb = bytes / (1024 * 1024);
  return mb >= 1 ? `${mb.toFixed(1)} MB` : `${Math.round(bytes / 1024)} KB`;
}

function describeShape(
  width: number | null | undefined,
  height: number | null | undefined,
  t: Translate,
): string | null {
  if (!width || !height) return null;
  const ratio = width / height;
  if (ratio < 1) return t("dọc {value}:9", { value: +(((1 / ratio) * 9).toFixed(1)) });
  if (ratio === 1) return t("vuông 1:1");
  return t("ngang {value}:9", { value: +(ratio * 9).toFixed(1) });
}

function describeAsset(asset: MediaAsset, t: Translate): string {
  const parts: string[] = [];
  const shape = describeShape(asset.width, asset.height, t);
  if (shape) parts.push(shape);
  if (typeof asset.duration_seconds === "number") {
    parts.push(t("{value} giây", { value: Math.round(asset.duration_seconds) }));
  }
  const size = formatSize(asset.size_bytes);
  if (size) parts.push(size);
  return parts.join(" · ");
}

export function MediaPickerModal({ isOpen, onClose, onSelect }: MediaPickerModalProps) {
  const {
    t
  } = useLanguage();

  const [assets, setAssets] = useState<MediaAsset[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    const result = await listMedia();
    if (result.ok) {
      setAssets(result.data.items);
      setError(null);
    } else {
      setError(result.message);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    if (isOpen) {
      load();
    }
  }, [isOpen, load]);

  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className={styles.overlay} onClick={onClose} role="dialog" aria-modal="true">
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <h3 className={styles.title}>{t("Chọn ảnh/video từ thư viện")}</h3>
          <button type="button" className={styles.closeBtn} onClick={onClose} aria-label={t("Đóng")}>
            ✕
          </button>
        </div>

        <div className={styles.body}>
          {error ? (
            <ErrorState title={t(error)} action={<button onClick={load}>{t("Thử lại")}</button>} />
          ) : loading ? (
            <LoadingState title={t("Đang tải thư viện…")} />
          ) : assets.length === 0 ? (
            <EmptyState
              title={t("Thư viện còn trống")}
              body={t("Hãy tải ảnh hoặc clip lên khi soạn bài để lưu vào thư viện.")}
            />
          ) : (
            <ul className={styles.grid}>
              {assets.map((asset) => (
                <li key={asset.id} className={styles.card} onClick={() => onSelect(asset)}>
                  <div className={styles.thumbWrap}>
                    {asset.type === "video" ? (
                      asset.thumbnail_url ? (
                        /* eslint-disable-next-line @next/next/no-img-element */
                        <img className={styles.thumb} src={asset.thumbnail_url} alt="" />
                      ) : (
                        <div className={styles.thumbFallback} aria-hidden="true">
                          🎬
                        </div>
                      )
                    ) : (
                      /* eslint-disable-next-line @next/next/no-img-element */
                      <img className={styles.thumb} src={asset.url} alt="" loading="lazy" />
                    )}
                    <span className={styles.typeTag}>
                      {t(asset.type === "video" ? "Video" : "Ảnh")}
                    </span>
                  </div>

                  <p className={styles.filename} title={asset.filename}>
                    {asset.filename}
                  </p>
                  <p className={styles.meta}>{describeAsset(asset, t) || "—"}</p>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
