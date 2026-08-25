"use client";

/**
 * Danh sách bản nháp — sửa, bỏ bài, xem lại trước khi duyệt.
 *
 * Ở đây **không có nút duyệt nào**, và đó là chủ ý. Quyết định "đưa lên Trang
 * lúc nào" nằm gọn ở `SchedulePicker` ngay dưới danh sách, đúng một chỗ. Bản
 * trước rải nút duyệt trên từng thẻ *và* một cặp nút duyệt-tất-cả ở cuối: chủ
 * tiệm không biết bấm cái nào, và bấm nhầm cái trên từng thẻ thì bài lên ngay
 * thay vì vào lịch của tuần.
 */

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/state-views";
import type { ContentItem } from "./content-creation.api";
import { channelLabels, type ChannelKey } from "./content-creation.fixture";
import { DraftEditor } from "./draft-editor";
import styles from "./content-creation.module.css";

const CHANNEL_ICONS: Record<string, string> = {
  facebook_page: "📘",
  google_business: "📍",
  zalo_oa: "💬",
};

type DraftListProps = {
  items: ContentItem[];
  busyIds: string[];
  editingId: string | null;
  onEdit: (id: string | null) => void;
  onSaved: (item: ContentItem) => void;
  onDismiss: (id: string) => void;
  onDismissAll: () => void;
  onGenerateImage: (id: string) => void;
  generatingImageId: string | null;
};

export function DraftList({
  items,
  busyIds,
  editingId,
  onEdit,
  onSaved,
  onDismiss,
  onDismissAll,
  onGenerateImage,
  generatingImageId,
}: DraftListProps) {
  if (!items.length) {
    return (
      <EmptyState
        title="Chưa có bản nháp nào"
        body="Kể cho Havi vài dòng hoặc nạp một tấm ảnh, rồi bấm “Để Havi viết bài”."
      />
    );
  }

  const anyBusy = busyIds.length > 0;

  return (
    <section aria-labelledby="drafts-title">
      <div className={styles.draftsHeader}>
        <h2 id="drafts-title" className={styles.draftsTitle}>
          {items.length} bản nháp chờ bạn duyệt
        </h2>
        <button type="button" className={styles.linkDanger} onClick={onDismissAll} disabled={anyBusy}>
          Xoá hết
        </button>
      </div>

      <div className={styles.draftsGrid}>
        {items.map((item) => {
          const busy = busyIds.includes(item.id);
          const channelLabel =
            channelLabels[item.channel as ChannelKey] ?? item.channel;

          return (
            <article key={item.id} className={styles.draftCard}>
              <div className={styles.draftMeta}>
                <span className={styles.channelTag}>
                  <span aria-hidden="true">{CHANNEL_ICONS[item.channel] ?? "📄"}</span>
                  {channelLabel}
                </span>
              </div>

              {editingId === item.id ? (
                <DraftEditor item={item} onClose={() => onEdit(null)} onSaved={onSaved} />
              ) : (
                <>
                  {item.media_url ? (
                    /* eslint-disable-next-line @next/next/no-img-element */
                    <img className={styles.draftImage} src={item.media_url} alt="" />
                  ) : null}

                  <p className={styles.draftText}>{item.text}</p>

                  <div className={styles.draftActions}>
                    <Button variant="outline" onClick={() => onEdit(item.id)} disabled={busy}>
                      Sửa
                    </Button>
                    {!item.media_url ? (
                      <Button
                        variant="outline"
                        onClick={() => onGenerateImage(item.id)}
                        disabled={busy || generatingImageId === item.id}
                      >
                        {generatingImageId === item.id ? "Đang tìm ảnh…" : "Thêm ảnh minh hoạ"}
                      </Button>
                    ) : null}
                    <button
                      type="button"
                      className={styles.linkDanger}
                      onClick={() => onDismiss(item.id)}
                      disabled={busy}
                    >
                      Bỏ bài này
                    </button>
                  </div>
                </>
              )}
            </article>
          );
        })}
      </div>
    </section>
  );
}
