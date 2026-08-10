"use client";

/* eslint-disable @next/next/no-img-element */

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
import { DraftEditor } from "./draft-editor";
import { useJobPolling } from "./use-job-polling";
import { QuotaBanner } from "./quota-banner";
import styles from "./content-creation.module.css";

type RawChip = {
  key: string;
  kind: "photo" | "text";
  label: string;
  input: RawInput;
  previewUrl?: string;
};

type UploadRow = {
  key: string;
  fileName: string;
  previewUrl: string;
  progress: number;
  status: "uploading" | "complete" | "cancelled" | "failed";
  message?: string;
  assetId?: string;
  controller: AbortController;
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
  const [uploads, setUploads] = useState<UploadRow[]>([]);
  const [jobId, setJobId] = useState<string | null>(null);
  const [items, setItems] = useState<ContentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // Đổi giá trị này để QuotaBanner nạp lại số token còn lại.
  const [quotaKey, setQuotaKey] = useState(0);
  const [notice, setNotice] = useState<string | null>(null);
  const [busyIds, setBusyIds] = useState<string[]>([]);
  const [editingId, setEditingId] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const previewUrlsRef = useRef(new Set<string>());

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

  useEffect(() => {
    const previewUrls = previewUrlsRef.current;
    return () => {
      for (const url of previewUrls) URL.revokeObjectURL(url);
      previewUrls.clear();
    };
  }, []);

  function rememberPreviewUrl(url: string) {
    previewUrlsRef.current.add(url);
  }

  function forgetPreviewUrl(url: string | undefined) {
    if (!url || !previewUrlsRef.current.has(url)) return;
    URL.revokeObjectURL(url);
    previewUrlsRef.current.delete(url);
  }

  // Job xong thì nạp lại hàng chờ duyệt và xoá chip — liệu thô đã thành bài rồi.
  const onJobReady = useCallback(() => {
    setJobId(null);
    for (const chip of chips) forgetPreviewUrl(chip.previewUrl);
    setChips([]);
    setUploads([]);
    setNote("");
    setNoteOpen(false);
    loadItems();
  }, [chips, loadItems]);

  const poll = useJobPolling(jobId, onJobReady);

  async function onPickFiles(files: FileList | null) {
    if (!files?.length) return;
    setError(null);
    const pendingUploads = Array.from(files).map((file, index) => {
      const previewUrl = URL.createObjectURL(file);
      const key = `upload-${Date.now()}-${index}-${file.name}`;
      rememberPreviewUrl(previewUrl);
      return {
        file,
        row: {
          key,
          fileName: file.name,
          previewUrl,
          progress: 0,
          status: "uploading" as const,
          controller: new AbortController(),
        },
      };
    });

    setUploads((prev) => [...prev, ...pendingUploads.map((upload) => upload.row)]);

    await Promise.all(
      pendingUploads.map(async ({ file, row }) => {
        const result = await uploadImage(file, {
          signal: row.controller.signal,
          onProgress: (progress) => {
            setUploads((prev) =>
              prev.map((upload) =>
                upload.key === row.key
                  ? { ...upload, progress: Math.max(upload.progress, progress) }
                  : upload,
              ),
            );
          },
        });

        if (row.controller.signal.aborted) {
          setUploads((prev) =>
            prev.map((upload) =>
              upload.key === row.key
                ? { ...upload, progress: 0, status: "cancelled", message: "Đã huỷ" }
                : upload,
            ),
          );
          return;
        }

        if (!result.ok) {
          setUploads((prev) =>
            prev.map((upload) =>
              upload.key === row.key
                ? {
                    ...upload,
                    status: "failed",
                    message: result.message,
                  }
                : upload,
            ),
          );
          setError(result.message);
          return;
        }

        setUploads((prev) =>
          prev.map((upload) =>
            upload.key === row.key
              ? { ...upload, progress: 100, status: "complete", assetId: result.data }
              : upload,
          ),
        );
        setChips((prev) => [
          ...prev,
          {
            key: result.data,
            kind: "photo",
            label: file.name,
            previewUrl: row.previewUrl,
            input: { kind: "photo", media_asset_id: result.data },
          },
        ]);
      }),
    );
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
    const removed = chips.find((chip) => chip.key === key);
    forgetPreviewUrl(removed?.previewUrl);
    setChips((prev) => prev.filter((c) => c.key !== key));
    setUploads((prev) => prev.filter((upload) => upload.assetId !== key));
  }

  function cancelUpload(key: string) {
    const upload = uploads.find((item) => item.key === key);
    upload?.controller.abort();
  }

  const generating = poll.status === "queued" || poll.status === "processing";
  const uploading = uploads.some((upload) => upload.status === "uploading");

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
      // Nạp lại quota: nếu vừa bị chặn vì hết lượt thì banner phải hiện ngay,
      // đừng để chủ tiệm bấm lại lần nữa mới hiểu chuyện gì.
      setQuotaKey((k) => k + 1);
      return;
    }
    setJobId(result.data.id);
    // Job vừa tạo sẽ tiêu token — nạp lại số còn lại sau khi worker chạy xong.
    setQuotaKey((k) => k + 1);
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

      {/* Trên ô nạp liệu: chủ tiệm phải biết còn bao nhiêu lượt TRƯỚC khi bỏ công
          nạp ảnh, không phải sau khi bấm "Để Havi viết" rồi bị chặn. */}
      <QuotaBanner reloadKey={quotaKey} />

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

      {uploads.length ? (
        <section className={styles.uploadList} aria-label="Ảnh đang nạp">
          {uploads.map((upload) => (
            <article key={upload.key} className={styles.uploadItem}>
              <img
                className={styles.uploadPreview}
                src={upload.previewUrl}
                alt={`Xem trước ${upload.fileName}`}
              />
              <div className={styles.uploadBody}>
                <div className={styles.uploadTopline}>
                  <span className={styles.uploadName}>{upload.fileName}</span>
                  <span className={styles.uploadPercent}>
                    {upload.status === "uploading"
                      ? `${upload.progress}%`
                      : upload.status === "complete"
                        ? "Xong"
                        : upload.message}
                  </span>
                </div>
                <div
                  className={styles.progressTrack}
                  role="progressbar"
                  aria-label={`Tiến độ tải ${upload.fileName}`}
                  aria-valuenow={upload.progress}
                  aria-valuemin={0}
                  aria-valuemax={100}
                >
                  <span
                    className={styles.progressBar}
                    style={{ width: `${upload.progress}%` }}
                  />
                </div>
              </div>
              {upload.status === "uploading" ? (
                <button
                  type="button"
                  className={styles.cancelUpload}
                  onClick={() => cancelUpload(upload.key)}
                >
                  Huỷ
                </button>
              ) : null}
            </article>
          ))}
        </section>
      ) : null}

      {chips.length ? (
        <section className={styles.chipRow} aria-label="Liệu thô vừa nạp">
          {chips.map((chip) => (
            <span key={chip.key} className={styles.chip}>
              {chip.previewUrl ? (
                <img
                  className={styles.chipPreview}
                  src={chip.previewUrl}
                  alt=""
                  aria-hidden="true"
                />
              ) : null}
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
                  {editingId === item.id ? (
                    <DraftEditor
                      item={item}
                      onClose={() => setEditingId(null)}
                      onSaved={(saved) => {
                        setItems((prev) =>
                          prev.map((i) => (i.id === saved.id ? saved : i)),
                        );
                        setNotice("Đã lưu bản sửa — bài vẫn đang chờ chị duyệt.");
                      }}
                    />
                  ) : (
                    <p className={styles.draftBody}>{item.text}</p>
                  )}
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
                        onClick={() =>
                          setEditingId(editingId === item.id ? null : item.id)
                        }
                      >
                        {editingId === item.id ? "Đang sửa" : "Sửa"}
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
