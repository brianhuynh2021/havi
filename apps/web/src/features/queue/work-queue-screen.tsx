"use client";

/**
 * Hàng đợi việc — **màn làm việc chính**, không phải một bảng tổng quan.
 *
 * Havi bán một câu: *"khỏi phải mở 5 tab"*. Nhưng bản trước thay 5 tab trình
 * duyệt bằng 10 mục nav: người trực ca vẫn phải vào Hội thoại xem tin nhắn, vào
 * Nội dung xem nháp chờ duyệt, vào Lịch đăng xem bài nào hỏng, vào Kênh kết nối
 * xem có kênh nào mất quyền. Bốn chỗ, và vẫn sót.
 *
 * Ở đây bốn nguồn là **một danh sách**, xếp theo thiệt hại khi bỏ sót — không
 * theo thời gian. Xếp theo thời gian thì câu hỏi giá của khách nằm dưới ba câu
 * hỏi giờ mở cửa đến sau, và người trực ca hết giờ trước khi tới nó.
 *
 * Mỗi việc có hai đường đi ra, và **cả hai đều đúng**: xử lý trong Havi, hoặc
 * bấm sang thẳng nền tảng. Thứ tốn thời gian không phải lúc trả lời — mà là lúc
 * đi tìm xem có gì cần trả lời.
 */

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { ErrorState, LoadingState } from "@/components/ui/state-views";
import { useLanguage } from "@/lib/i18n/language-context";
import { apiClient } from "@/lib/api-client/client";
import {
  assignInboxItem,
  fetchQueue,
  isOverdue,
  waitedFor,
  CATEGORY_LABELS,
  CHANNEL_LABELS,
  KIND_LABELS,
  type WorkItem,
} from "./queue.api";
import styles from "./work-queue.module.css";

/** Bộ lọc: nhóm loại việc, không phải nhóm màn hình. */
const FILTERS: Array<{ key: string; label: string; kinds: string[] }> = [
  { key: "all", label: "Tất cả", kinds: [] },
  { key: "inbox", label: "Khách nhắn", kinds: ["inbox"] },
  { key: "content", label: "Nội dung", kinds: ["approval", "publish_failure"] },
  { key: "connection", label: "Kênh", kinds: ["connection"] },
];

export function WorkQueueScreen() {
  const { t } = useLanguage();
  const [items, setItems] = useState<WorkItem[]>([]);
  const [total, setTotal] = useState(0);
  const [filter, setFilter] = useState("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [meId, setMeId] = useState<string | null>(null);

  const load = useCallback(async () => {
    const result = await fetchQueue();
    if (result.ok) {
      setItems(result.data.items);
      setTotal(result.data.total);
      setError(null);
    } else {
      setError(result.message);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    void load();
    // Cần id của chính mình để nút "Tôi nhận" biết gán cho ai, và để phân biệt
    // "việc của tôi" với "việc người khác đang làm".
    apiClient
      .GET("/auth/me")
      .then(({ data }) => setMeId(data?.id ?? null))
      .catch(() => setMeId(null));
  }, [load]);

  async function toggleAssign(item: WorkItem) {
    if (!meId) return;
    const mine = item.assigned_to_user_id === meId;
    setBusyId(item.id);
    const result = await assignInboxItem(item.id, mine ? null : meId);
    setBusyId(null);
    if (!result.ok) {
      setError(result.message);
      return;
    }
    setItems((prev) => prev.map((row) => (row.id === item.id ? result.data : row)));
  }

  if (loading) {
    return <LoadingState title={t({ vi: "Đang tải danh sách việc…", en: "Loading work queue…" })} />;
  }
  if (error && items.length === 0) {
    return (
      <ErrorState
        title={error}
        action={
          <Button variant="outline" onClick={() => void load()}>
            {t({ vi: "Thử lại", en: "Retry" })}
          </Button>
        }
      />
    );
  }

  const active = FILTERS.find((f) => f.key === filter) ?? FILTERS[0];
  const visible = active.kinds.length
    ? items.filter((item) => active.kinds.includes(item.kind))
    : items;
  const overdueCount = items.filter((item) => isOverdue(item)).length;

  return (
    <>
      <header className={styles.header}>
        <h1 className={styles.title}>{t({ vi: "Việc cần làm", en: "Work queue" })}</h1>
        <p className={styles.subtitle}>
          {total === 0
            ? t({ vi: "Không còn việc nào đang chờ.", en: "Nothing waiting." })
            : overdueCount > 0
              ? `${total} việc đang chờ — ${overdueCount} việc đã để lâu`
              : `${total} việc đang chờ`}
        </p>
      </header>

      {error ? (
        <p className={styles.partialError} role="status">
          {error}
        </p>
      ) : null}

      {/* Bộ lọc, không phải điều hướng. Người trực ca ở nguyên một chỗ và thu hẹp
          danh sách; họ không đi sang màn khác rồi tìm đường quay lại. */}
      <div className={styles.filterRow} role="group" aria-label="Lọc loại việc">
        {FILTERS.map((item) => {
          const count = item.kinds.length
            ? items.filter((row) => item.kinds.includes(row.kind)).length
            : items.length;
          return (
            <button
              key={item.key}
              type="button"
              aria-pressed={filter === item.key}
              className={`${styles.filterChip} ${filter === item.key ? styles.filterChipActive : ""}`}
              onClick={() => setFilter(item.key)}
            >
              {item.label}
              {count > 0 ? <span className={styles.filterCount}>{count}</span> : null}
            </button>
          );
        })}
      </div>

      {visible.length === 0 ? (
        <section className={styles.allClear} aria-label="Tình trạng">
          <span className={styles.allClearMark} aria-hidden="true">
            ✓
          </span>
          <div>
            <p className={styles.allClearTitle}>
              {total === 0 ? "Hết việc rồi" : "Không có việc nào trong nhóm này"}
            </p>
            <p className={styles.allClearBody}>
              {total === 0
                ? "Kênh đang hoạt động, mọi tin khách đã được trả lời, không bài nào lỗi."
                : "Chọn “Tất cả” để xem những việc còn lại."}
            </p>
          </div>
        </section>
      ) : (
        <ul className={styles.queue} aria-label="Danh sách việc">
          {visible.map((item) => {
            const overdue = isOverdue(item);
            const mine = Boolean(meId) && item.assigned_to_user_id === meId;
            const takenByOther =
              Boolean(item.assigned_to_user_id) && !mine;

            return (
              <li
                key={`${item.kind}-${item.id}`}
                className={`${styles.card} ${overdue ? styles.cardOverdue : ""}`}
              >
                <div className={styles.cardMeta}>
                  <span className={styles.kindTag}>{KIND_LABELS[item.kind] ?? item.kind}</span>
                  {item.category && CATEGORY_LABELS[item.category] ? (
                    <span className={styles.categoryTag}>{CATEGORY_LABELS[item.category]}</span>
                  ) : null}
                  {item.channel ? (
                    <span className={styles.channelTag}>
                      {CHANNEL_LABELS[item.channel] ?? item.channel}
                    </span>
                  ) : null}
                  <span className={overdue ? styles.waitedLong : styles.waited}>
                    {t({ vi: "chờ", en: "waited" })} {waitedFor(item.waiting_since)}
                  </span>
                </div>

                <p className={styles.cardTitle}>{item.title}</p>
                <p className={styles.cardDetail}>{item.detail}</p>

                {takenByOther ? (
                  <p className={styles.assignedNote}>
                    {item.assigned_to_name ?? "Một người khác"} đang xử lý
                  </p>
                ) : null}

                <div className={styles.cardActions}>
                  <Link href={item.href} className={styles.primaryAction}>
                    {t({ vi: "Xử lý", en: "Handle" })}
                  </Link>

                  {/* Chỉ hiện khi dựng được link đúng chỗ. `platform_url` là
                      `null` nghĩa là ẩn nút — một nút dẫn tới trang chủ tệ hơn
                      không có nút. */}
                  {item.platform_url ? (
                    <a
                      className={styles.secondaryAction}
                      href={item.platform_url}
                      target="_blank"
                      rel="noreferrer noopener"
                    >
                      {t({ vi: "Mở trên nền tảng ↗", en: "Open on platform ↗" })}
                    </a>
                  ) : null}

                  {/* Việc người khác đã nhận vẫn phải nhận thay được: hết ca
                      nhân viên về nhà, không giao lại được thì việc kẹt vĩnh
                      viễn — hỏng nặng hơn một lần nhận thay không cần thiết.
                      Nhãn khác nhau để không ai nhận thay do bấm nhầm. */}
                  {item.kind === "inbox" && meId ? (
                    <button
                      type="button"
                      className={mine ? styles.assignedButton : styles.assignButton}
                      onClick={() => void toggleAssign(item)}
                      disabled={busyId === item.id}
                    >
                      {busyId === item.id
                        ? "…"
                        : mine
                          ? t({ vi: "Bỏ nhận", en: "Release" })
                          : takenByOther
                            ? t({ vi: "Nhận thay", en: "Take over" })
                            : t({ vi: "Tôi nhận", en: "Claim" })}
                    </button>
                  ) : null}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </>
  );
}
