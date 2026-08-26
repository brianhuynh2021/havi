"use client";

/**
 * Danh sách bản nháp — sửa, bỏ bài, duyệt lẻ một bài, hoặc bỏ qua.
 *
 * Nút duyệt trên từng thẻ **chỉ hiện với người có quyền duyệt**. Ẩn nút không
 * phải là phân quyền — backend vẫn kiểm lại — nhưng bày ra một nút mà người
 * soạn bấm vào chỉ nhận 403 thì tệ hơn không bày.
 *
 * Cảnh báo cho lần sửa sau: nút này ("Đăng ngay") và `SchedulePicker` ngay dưới
 * ("xếp lịch") làm hai việc khác nhau trên cùng một đống nháp. Bản trước từng
 * gỡ hẳn nút trên thẻ vì chủ tiệm bấm nhầm rồi bài lên ngay thay vì vào lịch
 * tuần. Nếu thấy lại triệu chứng đó, sửa bằng cách cho hai nút cùng nghĩa —
 * đừng cho hai nghĩa vào hai nút trông giống nhau.
 */

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
  onDismiss,
  onDismissAll,
}: DraftListProps) {
  const { can } = usePermissions();
  const mayApprove = can(PERMISSIONS.approveContent);

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
                    {mayApprove ? (
                      <Button
                        variant="primary"
                        onClick={() => onApproveSingle(item.id)}
                        disabled={busy}
                      >
                        Duyệt & Đăng ngay
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
