"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/input";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/state-views";
import {
  approveAll,
  approveItem,
  createJob,
  listPendingItems,
  rejectItem,
  uploadImage,
  type ContentItem,
  type RawInput,
} from "./content-creation.api";
import { channelLabels, type PublishMode } from "./content-creation.fixture";
import { useJobPolling } from "./use-job-polling";
import styles from "./content-creation.module.css";

type RawChip = {
  key: string;
  kind: "photo" | "text";
  label: string;
  input: RawInput;
};

const jobProgressLabel: Record<string, string> = {
  queued: "Havi đã nhận, đang xếp hàng…",
  processing: "Havi đang viết bài từ liệu chị vừa nạp…",
};

export function ContentCreationScreen() {
  const [publishMode, setPublishMode] = useState<PublishMode>("review_first");
  const [chips, setChips] = useState<RawChip[]>([]);
  const [note, setNote] = useState("");
  const [noteOpen, setNoteOpen] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [items, setItems] = useState<ContentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busyIds, setBusyIds] = useState<string[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  /** `keepError` cho lượt nạp lại *sau khi* một hành động thất bại: nạp lại
   * thành công không có nghĩa là lỗi vừa rồi biến mất, và xoá nó đi thì chủ
   * tiệm thấy bài tự nhiên đổi trạng thái mà không biết vì sao. */
  const loadItems = useCallback(async (keepError = false) => {
    const result = await listPendingItems();
    if (result.ok) {
      setItems(result.data);
      if (!keepError) setError(null);
    } else {
      setError(result.message);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    let cancelled = false;
    // Bọc trong hàm async: mọi setState nằm sau `await`, không chạy đồng bộ
    // trong thân effect. `cancelled` chặn setState sau khi component đã unmount
    // — chủ tiệm đổi tab giữa lúc đang tải là chuyện thường.
    async function load() {
      const result = await listPendingItems();
      if (cancelled) return;
      if (result.ok) setItems(result.data);
      else setError(result.message);
      setLoading(false);
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  // Job xong thì nạp lại hàng chờ duyệt và xoá chip — liệu thô đã thành bài rồi.
  const onJobReady = useCallback(() => {
    setJobId(null);
    setChips([]);
    setNote("");
    setNoteOpen(false);
    loadItems();
  }, [loadItems]);

  const poll = useJobPolling(jobId, onJobReady);

  async function onPickFiles(files: FileList | null) {
    if (!files?.length) return;
    setError(null);
    setUploading(true);
    for (const file of Array.from(files)) {
      const result = await uploadImage(file);
      if (!result.ok) {
        setError(result.message);
        continue;
      }
      setChips((prev) => [
        ...prev,
        {
          key: result.data,
          kind: "photo",
          label: file.name,
          input: { kind: "photo", media_asset_id: result.data },
        },
      ]);
    }
    setUploading(false);
    // Cho phép chọn lại đúng file vừa bỏ ra: input file không bắn `change` nếu
    // value không đổi.
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  function addNote() {
    const text = note.trim();
    if (!text) return;
    setChips((prev) => [
      ...prev,
      {
        key: `note-${prev.length}-${text.slice(0, 12)}`,
        kind: "text",
        label: text.length > 40 ? `${text.slice(0, 40)}…` : text,
        input: { kind: "text", text },
      },
    ]);
    setNote("");
    setNoteOpen(false);
  }

  function removeChip(key: string) {
    setChips((prev) => prev.filter((c) => c.key !== key));
  }

  const generating = poll.status === "queued" || poll.status === "processing";

  async function generate() {
    if (!chips.length || generating) return;
    setError(null);
    setNotice(null);

    // Key gắn với đúng bộ liệu thô đang có: bấm hai lần cùng một bộ chỉ tốn một
    // lần tiền LLM, còn đổi liệu rồi bấm lại thì phải ra job mới.
    const key = `job-${chips.map((c) => c.key).join("|")}`;
    const result = await createJob(
      chips.map((c) => c.input),
      key,
    );
    if (!result.ok) {
      setError(result.message);
      return;
    }
    setJobId(result.data.id);
  }

  async function onApprove(id: string) {
    setBusyIds((prev) => [...prev, id]);
    const result = await approveItem(id);
    setBusyIds((prev) => prev.filter((b) => b !== id));
    if (!result.ok) {
      setError(result.message);
      // Backend từ chối thì trạng thái trên màn đang sai — nạp lại cho khớp.
      loadItems(true);
      return;
    }
    setItems((prev) => prev.filter((i) => i.id !== id));
    setNotice("Đã duyệt — bài sẽ lên đúng lịch ở tab Lịch đăng.");
  }

  async function onReject(id: string) {
    setBusyIds((prev) => [...prev, id]);
    const result = await rejectItem(id);
    setBusyIds((prev) => prev.filter((b) => b !== id));
    if (!result.ok) {
      setError(result.message);
      loadItems(true);
      return;
    }
    setItems((prev) => prev.filter((i) => i.id !== id));
    setNotice("Đã trả bài về bản nháp.");
  }

  async function onApproveAll() {
    const ids = items.map((i) => i.id);
    if (!ids.length) return;
    setBusyIds(ids);
    const result = await approveAll(ids);
    setBusyIds([]);
    if (!result.ok) {
      setError(result.message);
      return;
    }
    // Một bài hỏng không làm fail cả lô — nói rõ bài nào chưa duyệt được thay
    // vì im lặng để chủ tiệm tưởng đã duyệt hết.
    const failed = result.data.rejected;
    setNotice(
      failed.length
        ? `Đã duyệt ${result.data.approved.length} bài. ${failed.length} bài chưa duyệt được: ${failed[0].reason}`
        : `Đã duyệt ${result.data.approved.length} bài.`,
    );
    loadItems();
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
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            multiple
            hidden
            data-testid="file-input"
            onChange={(e) => onPickFiles(e.target.files)}
          />
          <Button
            variant="primary"
            disabled={uploading}
            onClick={() => fileInputRef.current?.click()}
          >
            {uploading ? "Đang tải ảnh…" : "+ Tải ảnh lên"}
          </Button>
          {/* Ghi âm là P1 (ROADMAP §4): ảnh/text ổn định trước đã. */}
          <Button variant="outline" disabled title="Havi sẽ mở tính năng này sau">
            Ghi âm nhanh
          </Button>
          <Button variant="outline" onClick={() => setNoteOpen((v) => !v)}>
            Gõ vài dòng
          </Button>
        </div>

        {noteOpen ? (
          <div className={styles.noteBox}>
            <label className={styles.noteLabel} htmlFor="raw-note">
              Chị muốn Havi kể chuyện gì?
            </label>
            <Textarea
              id="raw-note"
              rows={3}
              placeholder="Tuần này giảm 20% gói gội đầu thảo dược cho khách quen"
              value={note}
              onChange={(e) => setNote(e.target.value)}
            />
            <Button variant="outline" onClick={addNote} disabled={!note.trim()}>
              Thêm ghi chú
            </Button>
          </div>
        ) : null}
      </section>

      {chips.length ? (
        <section className={styles.chipRow} aria-label="Liệu thô vừa nạp">
          {chips.map((chip) => (
            <span key={chip.key} className={styles.chip}>
              <span className={styles.chipKind}>
                {chip.kind === "photo" ? "Ảnh" : "Ghi chú"}
              </span>
              {chip.label}
              <button
                type="button"
                className={styles.chipRemove}
                aria-label={`Bỏ ${chip.label}`}
                onClick={() => removeChip(chip.key)}
              >
                ×
              </button>
            </span>
          ))}
        </section>
      ) : null}

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

      <div className={styles.generateRow}>
        <Button
          variant="primary"
          onClick={generate}
          disabled={!chips.length || generating}
        >
          Để Havi viết cho chị
        </Button>
      </div>

      {error ? <ErrorState title={error} /> : null}
      {notice ? (
        <p className={styles.notice} role="status">
          {notice}
        </p>
      ) : null}

      {generating ? (
        <section className={styles.processingCard} aria-label="Đang xử lý">
          <span className={styles.spinner} aria-hidden="true" />
          <div>
            <p className={styles.processingTitle}>
              {jobProgressLabel[poll.status ?? "queued"]}
            </p>
            <p className={styles.processingMeta}>
              Thường xong trong dưới 90 giây — chị có thể rời màn này.
            </p>
          </div>
        </section>
      ) : null}

      {poll.status === "failed" ? (
        <ErrorState
          title="Havi chưa viết được lần này"
          body="Chị bấm viết lại giúp em nhé — liệu thô vẫn còn nguyên."
          action={
            <Button variant="outline" onClick={() => setJobId(null)}>
              Thử lại
            </Button>
          }
        />
      ) : null}
      {poll.error ? <ErrorState title={poll.error} /> : null}

      <section className={styles.draftsSection} aria-label="Bản nháp đã sẵn sàng">
        <div className={styles.draftsHeader}>
          <h2 className={styles.draftsTitle}>
            {items.length} bản nháp chờ chị duyệt
          </h2>
          <Button
            variant="primary"
            onClick={onApproveAll}
            disabled={!items.length || busyIds.length > 0}
          >
            Duyệt &amp; đăng hết
          </Button>
        </div>

        {loading ? (
          <LoadingState title="Đang tải bản nháp…" />
        ) : items.length === 0 ? (
          <EmptyState
            title="Chưa có bản nháp nào chờ duyệt"
            body="Nạp vài tấm ảnh hoặc gõ vài dòng, Havi sẽ viết bài cho chị."
          />
        ) : (
          <div className={styles.draftsGrid}>
            {items.map((item) => {
              const busy = busyIds.includes(item.id);
              return (
                <article key={item.id} className={styles.draftCard}>
                  <div className={styles.draftMeta}>
                    <Badge tone="neutral">
                      {channelLabels[item.channel as keyof typeof channelLabels] ??
                        item.channel}
                    </Badge>
                    <span className={styles.draftKind}>{item.kind}</span>
                  </div>
                  <p className={styles.draftBody}>{item.text}</p>
                  <div className={styles.draftFooter}>
                    <div className={styles.draftActions}>
                      <Button
                        variant="primary"
                        disabled={busy}
                        onClick={() => onApprove(item.id)}
                      >
                        Duyệt
                      </Button>
                      <Button
                        variant="outline"
                        disabled={busy}
                        onClick={() => onReject(item.id)}
                      >
                        Từ chối
                      </Button>
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </section>
    </>
  );
}
