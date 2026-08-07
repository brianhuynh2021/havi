"use client";

import { useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  channelLabels,
  draftsFixture,
  generatingJobFixture,
  rawInputsFixture,
  type DraftStatus,
  type PublishMode,
} from "./content-creation.fixture";
import styles from "./content-creation.module.css";

type LocalStatus = DraftStatus | "rejected";

const inputKindLabel: Record<string, string> = {
  photo: "Ảnh",
  voice: "Ghi âm",
  text: "Ghi chú",
};

export function ContentCreationScreen() {
  const [publishMode, setPublishMode] = useState<PublishMode>("review_first");
  const [statuses, setStatuses] = useState<Record<string, LocalStatus>>(() =>
    Object.fromEntries(draftsFixture.map((d) => [d.id, d.status])),
  );

  const pendingCount = useMemo(
    () => Object.values(statuses).filter((s) => s === "pending_approval").length,
    [statuses],
  );

  function approve(id: string) {
    setStatuses((prev) => ({ ...prev, [id]: "approved" }));
  }

  function reject(id: string) {
    setStatuses((prev) => ({ ...prev, [id]: "rejected" }));
  }

  function approveAll() {
    setStatuses((prev) => {
      const next = { ...prev };
      for (const draft of draftsFixture) {
        if (next[draft.id] === "pending_approval") next[draft.id] = "approved";
      }
      return next;
    });
  }

  return (
    <>
      <header className={styles.header}>
        <h1 className={styles.title}>Tạo nội dung</h1>
        <p className={styles.subtitle}>
          Nạp ảnh, ghi âm hoặc vài dòng — Havi viết bài theo từng kênh, chị chỉ
          cần duyệt.
        </p>
      </header>

      <section className={styles.dropZone} aria-label="Nạp liệu mới">
        <p className={styles.dropTitle}>Thả ảnh vào đây, hoặc</p>
        <div className={styles.dropActions}>
          <Button variant="primary">+ Tải ảnh lên</Button>
          <Button variant="outline">Ghi âm nhanh</Button>
          <Button variant="outline">Gõ vài dòng</Button>
        </div>
      </section>

      <section className={styles.chipRow} aria-label="Liệu thô vừa nạp">
        {rawInputsFixture.map((item) => (
          <span key={item.id} className={styles.chip}>
            <span className={styles.chipKind}>{inputKindLabel[item.kind]}</span>
            {item.label}
          </span>
        ))}
      </section>

      <section className={styles.modeToggle} aria-label="Chế độ đăng bài">
        <div className={styles.modeButtons} role="group">
          <button
            type="button"
            className={`${styles.modeButton} ${
              publishMode === "review_first" ? styles.modeButtonActive : ""
            }`}
            aria-pressed={publishMode === "review_first"}
            onClick={() => setPublishMode("review_first")}
          >
            Duyệt trước khi đăng
          </button>
          <button
            type="button"
            className={`${styles.modeButton} ${
              publishMode === "full_auto" ? styles.modeButtonActive : ""
            }`}
            aria-pressed={publishMode === "full_auto"}
            onClick={() => setPublishMode("full_auto")}
          >
            Tự động đăng
          </button>
        </div>
        {publishMode === "full_auto" ? (
          <p className={styles.modeWarning}>
            Chế độ này đang khoá trong bản pilot — mọi bài vẫn sẽ chờ chị duyệt
            trước khi lên mạng.
          </p>
        ) : (
          <p className={styles.modeHint}>
            Mặc định của Havi — không có bài nào lên mạng khi chị chưa duyệt.
          </p>
        )}
      </section>

      <section className={styles.processingCard} aria-label="Đang xử lý">
        <span className={styles.spinner} aria-hidden="true" />
        <div>
          <p className={styles.processingTitle}>{generatingJobFixture.progressLabel}</p>
          <p className={styles.processingMeta}>
            Thường xong trong dưới 90 giây — chị có thể rời màn này.
          </p>
        </div>
      </section>

      <section className={styles.draftsSection} aria-label="Bản nháp đã sẵn sàng">
        <div className={styles.draftsHeader}>
          <h2 className={styles.draftsTitle}>
            {draftsFixture.length} bản nháp đã sẵn sàng
          </h2>
          <Button variant="primary" onClick={approveAll} disabled={pendingCount === 0}>
            Duyệt & đăng hết
          </Button>
        </div>

        <div className={styles.draftsGrid}>
          {draftsFixture.map((draft) => {
            const status = statuses[draft.id];
            return (
              <article key={draft.id} className={styles.draftCard}>
                <div className={styles.draftMeta}>
                  <Badge tone="neutral">{channelLabels[draft.channel]}</Badge>
                  <span className={styles.draftKind}>{draft.kindLabel}</span>
                </div>
                <p className={styles.draftBody}>{draft.body}</p>
                <div className={styles.draftFooter}>
                  {status === "approved" ? (
                    <Badge tone="success">Đã duyệt</Badge>
                  ) : status === "rejected" ? (
                    <Badge tone="warning">Đã từ chối — quay về bản nháp</Badge>
                  ) : (
                    <div className={styles.draftActions}>
                      <Button variant="primary" onClick={() => approve(draft.id)}>
                        Duyệt
                      </Button>
                      <Button variant="outline" onClick={() => reject(draft.id)}>
                        Từ chối
                      </Button>
                    </div>
                  )}
                </div>
              </article>
            );
          })}
        </div>
      </section>
    </>
  );
}
