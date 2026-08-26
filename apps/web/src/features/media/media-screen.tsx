"use client";

/**
 * Thư viện media — xem lại mọi ảnh và clip đã tải lên workspace.
 *
 * Màn này chỉ *quản trị kho*: xem có gì, thuộc loại nào, clip dài bao nhiêu,
 * khung hình ra sao. Không sửa ảnh, không dựng video, không gợi ý nội dung —
 * việc soạn bài nằm ở mục Nội dung.
 */

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/state-views";
import { DangerConfirmModal } from "@/features/settings/danger-confirm-modal";
import { deleteMedia, listMedia, type MediaAsset, type MediaType } from "./media.api";
import styles from "./media.module.css";

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
function describeShape(width?: number | null, height?: number | null): string | null {
  if (!width || !height) return null;
  const ratio = width / height;
  if (ratio < 1) return `dọc ${+(((1 / ratio) * 9).toFixed(1))}:9`;
  if (ratio === 1) return "vuông 1:1";
  return `ngang ${+((ratio * 9).toFixed(1))}:9`;
}

function describeAsset(asset: MediaAsset): string {
  const parts: string[] = [];
  const shape = describeShape(asset.width, asset.height);
  if (shape) parts.push(shape);
  if (typeof asset.duration_seconds === "number") {
    parts.push(`${Math.round(asset.duration_seconds)} giây`);
  }
  const size = formatSize(asset.size_bytes);
  if (size) parts.push(size);
  return parts.join(" · ");
}

export function MediaScreen() {
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
      <header className={styles.header}>
        <h1 className={styles.title}>Thư viện media</h1>
        <p className={styles.subtitle}>
          Mọi ảnh và clip đã tải lên workspace. Dùng lại khi soạn bài thay vì tải
          lên từ đầu mỗi lần.
        </p>
      </header>

      <div className={styles.filterRow} role="group" aria-label="Lọc theo loại">
        {FILTERS.map((item) => (
          <button
            key={item.key}
            type="button"
            aria-pressed={filter === item.key}
            className={`${styles.filterChip} ${filter === item.key ? styles.filterChipActive : ""}`}
            onClick={() => setFilter(item.key)}
          >
            {item.label}
          </button>
        ))}
        {!loading && !error ? (
          <span className={styles.countHint}>{total} mục</span>
        ) : null}
      </div>

      {error ? (
        <ErrorState title={error} action={<Button variant="outline" onClick={load}>Thử lại</Button>} />
      ) : loading ? (
        <LoadingState title="Đang tải thư viện…" />
      ) : assets.length === 0 ? (
        <EmptyState
          title="Thư viện còn trống"
          body="Ảnh và clip bạn tải lên khi soạn bài sẽ tự động nằm ở đây."
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
                  {asset.type === "video" ? "Video" : "Ảnh"}
                </span>
              </div>

              <p className={styles.filename} title={asset.filename}>
                {asset.filename}
              </p>
              <p className={styles.meta}>{describeAsset(asset) || "—"}</p>
              
              <button 
                type="button"
                className={styles.deleteButton}
                onClick={() => setDeletingId(asset.id)}
                aria-label={`Xoá ${asset.filename}`}
              >
                Xoá
              </button>
            </li>
          ))}
        </ul>
      )}

      <DangerConfirmModal
        isOpen={deletingId !== null}
        type="custom"
        isDeleting={isDeleting}
        customKeyword="XOA"
        customTitle="Xoá media khỏi thư viện"
        customLostItems={[
          "File này sẽ bị xóa vĩnh viễn khỏi hệ thống.",
          "Nếu có bài viết (nháp) đang dùng file này, hình/video trong bài đó sẽ bị lỗi hiển thị.",
        ]}
        onClose={() => setDeletingId(null)}
        onConfirm={handleDeleteConfirm}
      />
    </>
  );
}
