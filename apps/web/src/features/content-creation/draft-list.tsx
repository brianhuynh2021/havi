"use client";

/**
 * Danh sách bản nháp — sửa, bỏ bài, duyệt lẻ một bài, hoặc bỏ qua.
 *
 * Nút duyệt trên từng thẻ **chỉ hiện với người có quyền duyệt**. Ẩn nút không
 * phải là phân quyền — backend vẫn kiểm lại — nhưng bày ra một nút mà người
 * soạn bấm vào chỉ nhận 403 thì tệ hơn không bày.
 *
 * Nút này và nút duyệt cả loạt ở `SchedulePicker` **luôn cùng nghĩa**, chỉ khác
 * phạm vi: cách xử lý do `plan` dưới danh sách quyết định, và nhãn nút đổi theo
 * `publishNow` để nói đúng việc sắp xảy ra. Bản trước hardcode "Đăng ngay"
 * trong khi nút dưới xếp lịch — hai nút trông giống nhau làm hai việc trái
 * ngược, và đó là lý do nút trên thẻ từng bị gỡ hẳn một lần.
 *
 * Nếu lần sau cần đổi, giữ nguyên bất biến: một nghĩa, hai phạm vi.
 */

import { useLanguage } from "@/lib/i18n/language-context";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/state-views";
import { PERMISSIONS, usePermissions } from "@/lib/auth/use-permissions";
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
  onApproveSingle: (id: string) => void;
  /** Từ `plan` dưới danh sách — quyết định nhãn nút duyệt lẻ. */
  publishNow: boolean;
  onDismiss: (id: string) => void;
  onDismissAll: () => void;
};

export function DraftList({
  items,
  busyIds,
  editingId,
  onEdit,
  onSaved,
  onApproveSingle,
  publishNow,
  onDismiss,
  onDismissAll,
}: DraftListProps) {
  const {
    t
  } = useLanguage();

  const { can } = usePermissions();
  const mayApprove = can(PERMISSIONS.approveContent);

  if (!items.length) {
    return (
      <EmptyState
        title={t("Chưa có bản nháp nào")}
        body={t("Kể cho Havi vài dòng hoặc nạp một tấm ảnh, rồi bấm “Để Havi viết bài”.")}
      />
    );
  }

  const anyBusy = busyIds.length > 0;

  return (
    <section aria-labelledby="drafts-title">
      <div className={styles.draftsHeader}>
        <h2 id="drafts-title" className={styles.draftsTitle}>
          {items.length}{" "}{t("bản nháp chờ bạn duyệt")}</h2>
        <button type="button" className={styles.linkDanger} onClick={onDismissAll} disabled={anyBusy}>{t("Xoá hết")}</button>
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
                    <Button variant="outline" onClick={() => onEdit(item.id)} disabled={busy}>{t("Sửa")}</Button>
                    {mayApprove ? (
                      <Button
                        variant="primary"
                        onClick={() => onApproveSingle(item.id)}
                        disabled={busy}
                      >
                        {t(publishNow ? "Duyệt & đăng ngay" : "Duyệt & xếp lịch")}
                      </Button>
                    ) : null}
                    <button
                      type="button"
                      className={styles.linkDanger}
                      onClick={() => onDismiss(item.id)}
                      disabled={busy}
                    >{t("Bỏ bài này")}</button>
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
