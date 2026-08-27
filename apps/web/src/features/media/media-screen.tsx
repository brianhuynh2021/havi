"use client";

/**
 * Thư viện media — xem lại mọi ảnh và clip đã tải lên workspace.
 *
 * Màn này chỉ *quản trị kho*: xem có gì, thuộc loại nào, clip dài bao nhiêu,
 * khung hình ra sao. Không sửa ảnh, không dựng video, không gợi ý nội dung —
 * việc soạn bài nằm ở mục Nội dung.
 */

import Link from "next/link";
import { useLanguage, type Translate } from "@/lib/i18n/language-context";
import { useCallback, useEffect, useState } from "react";
import { IconArrowLeft } from "@/components/app-shell/nav-icons";
import { Button } from "@/components/ui/button";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/state-views";
import { DangerConfirmModal } from "@/features/settings/danger-confirm-modal";
import { deleteMedia, listMedia, type MediaAsset, type MediaType } from "./media.api";
import styles from "./media.module.css";

// i18n-data: nhãn bộ lọc thư viện, `t()` dịch ở chỗ render
const FILTERS: Array<{ key: "all" | MediaType; label: string }> = [
  { key: "all", label: "Tất cả" },
  { key: "image", label: "Ảnh" },
  { key: "video", label: "Video" },
];

function formatSize(bytes: number | null | undefined): string | null {
  if (!bytes) return null;
  const mb = bytes / (1024 * 1024);
  return mb >= 1 ? `${mb.toFixed(1)} MB` : `${Math.round(bytes / 1024)} KB`;
}

/**
 * Khung hình nói bằng hình dạng, không bằng số pixel.
 *
 * "720:1648" không cho biết dọc hay ngang; "dọc 20.6:9" thì có. Khớp với
 * `describe_shape` ở `domain/policies/video_constraints.py`.
 */
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

export function MediaScreen() {
  const {
    t
  } = useLanguage();

  const [assets, setAssets] = useState<MediaAsset[]>([]);
  const [total, setTotal] = useState(0);
  const [filter, setFilter] = useState<"all" | MediaType>("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    const result = await listMedia(filter === "all" ? {} : { type: filter });
    if (result.ok) {
      setAssets(result.data.items);
      setTotal(result.data.total);
      setError(null);
    } else {
      setError(result.message);
    }
    setLoading(false);
  }, [filter]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleDeleteConfirm() {
    if (!deletingId) return;
    setIsDeleting(true);
    const result = await deleteMedia(deletingId);
    setIsDeleting(false);
    
    if (result.ok) {
      setAssets((prev) => prev.filter(a => a.id !== deletingId));
      setTotal((prev) => Math.max(0, prev - 1));
      setDeletingId(null);
    } else {
      setError(result.message);
      setDeletingId(null);
    }
  }

  return (
    <>
      <div className={styles.backLinkWrap}>
        <Link href="/app/content" className={styles.backLink}>
          <IconArrowLeft size={15} aria-hidden="true" />
          <span>{t("Quay lại Nội dung")}</span>
        </Link>
      </div>

      <header className={styles.header}>
        <h1 className={styles.title}>{t("Thư viện media")}</h1>
        <p className={styles.subtitle}>{t(
          "Mọi ảnh và clip đã tải lên workspace. Dùng lại khi soạn bài thay vì tải\n          lên từ đầu mỗi lần."
        )}</p>
      </header>

      <div className={styles.filterRow} role="group" aria-label={t("Lọc theo loại")}>
        {FILTERS.map((item) => (
          <button
            key={item.key}
            type="button"
            aria-pressed={filter === item.key}
            className={`${styles.filterChip} ${filter === item.key ? styles.filterChipActive : ""}`}
            onClick={() => setFilter(item.key)}
          >
            {t(item.label)}
          </button>
        ))}
        {!loading && !error ? (
          <span className={styles.countHint}>{total}{" "}{t("mục")}</span>
        ) : null}
      </div>

      {error ? (
        <ErrorState title={t(error)} action={<Button variant="outline" onClick={load}>{t("Thử lại")}</Button>} />
      ) : loading ? (
        <LoadingState title={t("Đang tải thư viện…")} />
      ) : assets.length === 0 ? (
        <EmptyState
          title={t("Thư viện còn trống")}
          body={t("Ảnh và clip bạn tải lên khi soạn bài sẽ tự động nằm ở đây.")}
        />
      ) : (
        <ul className={styles.grid}>
          {assets.map((asset) => (
            <li key={asset.id} className={styles.card}>
              <div className={styles.thumbWrap}>
                {asset.type === "video" ? (
                  asset.thumbnail_url ? (
                    /* eslint-disable-next-line @next/next/no-img-element */
                    <img className={styles.thumb} src={asset.thumbnail_url} alt="" />
                  ) : (
                    // Ảnh bìa lấy lúc upload; không lấy được thì hiện nhãn rõ
                    // ràng thay vì ô trắng trông như ảnh hỏng.
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
              
              <button 
                type="button"
                className={styles.deleteButton}
                onClick={() => setDeletingId(asset.id)}
                aria-label={t("Xoá {filename}", { filename: asset.filename })}
              >{t("Xoá")}</button>
            </li>
          ))}
        </ul>
      )}

      <DangerConfirmModal
        isOpen={deletingId !== null}
        type="custom"
        isDeleting={isDeleting}
        customKeyword="XOA"
        customTitle={t("Xoá media khỏi thư viện")}
        customLostItems={[
          t("File này sẽ bị xóa vĩnh viễn khỏi hệ thống."),
          t("Nếu có bài viết (nháp) đang dùng file này, hình/video trong bài đó sẽ bị lỗi hiển thị."),
        ]}
        onClose={() => setDeletingId(null)}
        onConfirm={handleDeleteConfirm}
      />
    </>
  );
}
