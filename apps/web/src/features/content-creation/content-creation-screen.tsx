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
  mediaTypeOf,
  rejectItem,
  uploadMedia,
  type Channel,
  type ContentItem,
  type MediaAsset,
  type RawInput,
} from "./content-creation.api";
import { channelLabels, type PublishMode } from "./content-creation.fixture";
import { DraftEditor } from "./draft-editor";
import { useJobPolling } from "./use-job-polling";
import { QuotaBanner } from "./quota-banner";
import { ToastContainer, type ToastItem } from "@/components/ui/toast";
import { pushNotification } from "@/components/notifications/notification-store";
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
  isVideo: boolean;
  progress: number;
  status: "uploading" | "complete" | "cancelled" | "failed";
  message?: string;
  assetId?: string;
  /** Chỉ có với video, và chỉ sau khi backend probe xong ở lượt `complete`. */
  asset?: MediaAsset;
  controller: AbortController;
};

/** Kênh video Havi kiểm ràng buộc — khớp `VIDEO_REQUIREMENTS` ở backend. */
const VIDEO_CHANNEL_LABELS: Record<string, string> = {
  reels: "Facebook Reels",
  tiktok: "TikTok",
  youtube: "YouTube Shorts",
};

function isEligible(asset: MediaAsset, channel: string): boolean {
  return (asset.eligible_channels ?? []).includes(channel as Channel);
}

/** Mô tả clip bằng thứ chủ tiệm nhìn thấy được, không phải bằng tên trường. */
function describeClip(asset: MediaAsset): string {
  const parts: string[] = [];
  if (asset.aspect_ratio) parts.push(`khung ${asset.aspect_ratio}`);
  if (typeof asset.duration_seconds === "number") {
    parts.push(`${Math.round(asset.duration_seconds)} giây`);
  }
  if (asset.has_audio === false) parts.push("không có tiếng");
  return parts.join(" · ");
}

/** "Clip này đăng được Reels nhưng không đăng được Shorts" — ngay lúc upload.
 *
 * Kiểm ngay bây giờ vì bây giờ là lúc còn quay lại được. Nếu ràng buộc chỉ lộ ra
 * lúc scheduler gọi API nền tảng thì chủ tiệm biết mình quay ngang sau khi đã lỡ
 * giờ đăng tối thứ Bảy (`domain/policies/video_constraints.py`).
 *
 * `aspect_ratio == null` nghĩa là chưa probe được, KHÔNG phải không hợp kênh nào:
 * nói "clip này không đăng được đâu cả" về một clip Havi chưa đọc nổi là bịa ra
 * một kết luận từ chỗ không có dữ liệu.
 */
function renderClipEligibility(asset: MediaAsset | undefined) {
  if (!asset) return null;
  if (!asset.aspect_ratio) {
    return (
      <p className={styles.clipUnknown} role="status">
        Havi chưa đọc được thông số clip này nên chưa kiểm được kênh nào đăng
        được. Clip vẫn nằm trong thư viện của chị.
      </p>
    );
  }

  const description = describeClip(asset);
  const channels = Object.entries(VIDEO_CHANNEL_LABELS);
  const fitCount = channels.filter(([channel]) => isEligible(asset, channel)).length;

  return (
    <div className={styles.clipEligibility}>
      <p className={styles.clipSpec}>
        {description}
        {fitCount === 0 ? " — chưa hợp kênh video nào" : null}
      </p>
      <ul className={styles.clipChannelList}>
        {channels.map(([channel, label]) => {
          const fits = isEligible(asset, channel);
          return (
            <li
              key={channel}
              className={fits ? styles.clipChannelFits : styles.clipChannelUnfit}
            >
              {/* Dấu ✓/✕ là trang trí; câu đầy đủ nằm trong một text node duy
                  nhất để trình đọc màn hình không phải ghép từ màu sắc. */}
              <span aria-hidden="true">{fits ? "✓" : "✕"}</span>
              <span>{`${label}: ${fits ? "đăng được" : "không đăng được"}`}</span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function getTopicImage(mediaNote?: string | null, text?: string | null): string {
  const combined = `${mediaNote || ""} ${text || ""}`.toLowerCase();
  if (
    combined.includes("quà") ||
    combined.includes("gift") ||
    combined.includes("thưởng") ||
    combined.includes("khuyến mãi") ||
    combined.includes("ưu đãi") ||
    combined.includes("bốc thăm") ||
    combined.includes("voucher") ||
    combined.includes("trò chơi") ||
    combined.includes("game")
  ) {
    return "https://images.unsplash.com/photo-1513151233558-d860c5398176?w=1200&q=80";
  }
  if (
    combined.includes("tóc") ||
    combined.includes("hair") ||
    combined.includes("gội") ||
    combined.includes("cắt") ||
    combined.includes("uốn") ||
    combined.includes("nhuộm") ||
    combined.includes("styling")
  ) {
    return "https://images.unsplash.com/photo-1560066984-138dadb4c035?w=1200&q=80";
  }
  if (
    combined.includes("cafe") ||
    combined.includes("cà phê") ||
    combined.includes("trà") ||
    combined.includes("ăn") ||
    combined.includes("uống") ||
    combined.includes("food")
  ) {
    return "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=1200&q=80";
  }
  if (
    combined.includes("da") ||
    combined.includes("dưỡng") ||
    combined.includes("mặt") ||
    combined.includes("trị liệu") ||
    combined.includes("massage") ||
    combined.includes("facial") ||
    combined.includes("chân")
  ) {
    return "https://images.unsplash.com/photo-1512290900673-7002b54177b5?w=1200&q=80";
  }
  return "https://images.unsplash.com/photo-1540555700478-4be289fbecef?w=1200&q=80";
}

const jobProgressLabel: Record<string, string> = {
  queued: "Havi đã nhận, đang xếp hàng…",
  processing: "Havi đang viết bài từ liệu chị vừa nạp…",
};

function makeNoteChipKey(chipCount: number): string {
  return `note-${chipCount}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
}

function makeJobKey(chips: RawChip[]): string {
  return `job-${Date.now()}-${chips.map((c) => c.key).join("|")}`;
}

export function ContentCreationScreen() {
  const [publishMode, setPublishMode] = useState<PublishMode>("review_first");
  const [chips, setChips] = useState<RawChip[]>([]);
  const [note, setNote] = useState("");
  const [noteOpen, setNoteOpen] = useState(true);
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
  const [publishedModal, setPublishedModal] = useState<{
    title: string;
    body: string;
    isInstant: boolean;
  } | null>(null);
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

  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const addToast = useCallback((toast: Omit<ToastItem, "id">) => {
    const id = `toast-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
    setToasts((prev) => [...prev, { ...toast, id }]);
    if (toast.type !== "loading") {
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, 6000);
    }
    return id;
  }, []);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  // Job xong thì nạp lại hàng chờ duyệt và hiển thị thông báo Toast + Chuông thông báo ở góc phải.
  const onJobReady = useCallback(() => {
    setNotice("⚡ Havi vừa viết xong bài mới! Đã nạp vào danh sách chờ duyệt bên dưới.");
    pushNotification({
      type: "draft_ready",
      title: "⚡ Havi vừa tạo xong các bản nháp mới",
      description: "Bài viết mới cho Facebook, Zalo, Google Business đã sẵn sàng cho chị duyệt.",
    });
    setToasts((prev) => prev.filter((t) => t.type !== "loading"));
    addToast({
      type: "success",
      title: "🎉 Havi đã sáng tạo xong bài mới!",
      description: "Đã nạp vào danh sách bên dưới — mời chị cuộn xuống duyệt nhé.",
    });
    loadItems();
  }, [addToast, loadItems]);

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
          isVideo: mediaTypeOf(file) === "video",
          progress: 0,
          status: "uploading" as const,
          controller: new AbortController(),
        },
      };
    });

    setUploads((prev) => [...prev, ...pendingUploads.map((upload) => upload.row)]);

    await Promise.all(
      pendingUploads.map(async ({ file, row }) => {
        const result = await uploadMedia(file, {
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

        const asset = result.data;
        setUploads((prev) =>
          prev.map((upload) =>
            upload.key === row.key
              ? {
                  ...upload,
                  progress: 100,
                  status: "complete",
                  assetId: asset.id,
                  asset,
                }
              : upload,
          ),
        );
        // Chỉ ảnh thành chip liệu thô: `RawInputKind` chưa có `video`, và Havi
        // chưa đăng được kênh video nào (ROADMAP §17). Clip upload lên là để vào
        // thư viện và để chủ tiệm biết nó có hợp khung/độ dài hay không — hứa nó
        // sẽ được đưa vào bài viết ngay bây giờ là hứa thứ chưa có.
        if (row.isVideo) return;
        setChips((prev) => [
          ...prev,
          {
            key: asset.id,
            kind: "photo",
            label: file.name,
            previewUrl: row.previewUrl,
            input: { kind: "photo", media_asset_id: asset.id },
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
        key: `note-${prev.length}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
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

  function removeUpload(key: string) {
    const upload = uploads.find((item) => item.key === key);
    if (upload?.status === "uploading") {
      upload.controller.abort();
    }
    forgetPreviewUrl(upload?.previewUrl);
    setUploads((prev) => prev.filter((item) => item.key !== key));
    if (upload?.assetId) {
      setChips((prev) => prev.filter((c) => c.key !== upload.assetId));
    }
  }

  const generating = poll.activeCount > 0 || poll.status === "queued" || poll.status === "processing";
  const uploading = uploads.some((upload) => upload.status === "uploading");

  async function generate() {
    let currentChips = [...chips];
    if (!currentChips.length && note.trim()) {
      const text = note.trim();
      const newChip: RawChip = {
        key: makeNoteChipKey(chips.length),
        kind: "text",
        label: text.length > 40 ? `${text.slice(0, 40)}…` : text,
        input: { kind: "text", text },
      };
      currentChips = [newChip];
    }
    if (!currentChips.length) return;
    setError(null);
    setNotice(null);

    // Key gắn với bộ liệu thô và thời điểm gửi để tạo được nhiều job liên tiếp
    const key = makeJobKey(currentChips);
    const result = await createJob(
      currentChips.map((c) => c.input),
      key,
    );
    if (!result.ok) {
      setError(result.message);
      // Nạp lại quota: nếu vừa bị chặn vì hết lượt thì banner phải hiện ngay,
      // đừng để chủ tiệm bấm lại lần nữa mới hiểu chuyện gì.
      setQuotaKey((k) => k + 1);
      return;
    }
    // Async Non-blocking: Xóa sạch nạp liệu ngay lập tức để chủ tiệm có thể
    // nạp tiếp liệu thô khác hoặc thao tác thoải mái không phải ngồi chờ.
    for (const chip of currentChips) forgetPreviewUrl(chip.previewUrl);
    setChips([]);
    setUploads([]);
    setNote("");
    setNoteOpen(true);

    poll.addJobId(result.data.id);
    setJobId(result.data.id);
    // Job vừa tạo sẽ tiêu token — nạp lại số còn lại sau khi worker chạy xong.
    setQuotaKey((k) => k + 1);

    // Hiển thị Toast góc phải màn hình theo chuẩn MIT
    addToast({
      type: "loading",
      title: "⚡ Havi đang viết bài cho tiệm",
      description: "Đang chạy ngầm trong nền — Chị có thể tạo tiếp bài khác hoặc chuyển màn hình thoải mái.",
    });
  }

  async function onApprove(id: string, scheduledAt?: string) {
    setBusyIds((prev) => [...prev, id]);
    const result = await approveItem(id, scheduledAt);
    setBusyIds((prev) => prev.filter((b) => b !== id));
    if (!result.ok) {
      setError(result.message);
      // Backend từ chối thì trạng thái trên màn đang sai — nạp lại cho khớp.
      loadItems(true);
      return;
    }
    setItems((prev) => prev.filter((i) => i.id !== id));
    setPublishedModal({
      title: scheduledAt
        ? "🚀 Đã phát lệnh đăng bài thành công!"
        : "📅 Đã xếp bài vào Lịch đăng!",
      body: scheduledAt
        ? "Bài viết đang được Havi gửi trực tiếp lên trang Facebook Fanpage của tiệm chị. Chị có thể sang Facebook kiểm tra hoặc chuyển sang tab Lịch đăng nhé!"
        : "Bài viết đã được duyệt và xếp lịch tự động. Havi sẽ tự động xuất bản bài viết đúng giờ chị đã chọn.",
      isInstant: !!scheduledAt,
    });
    setNotice(
      scheduledAt
        ? "⚡ Đã phát lệnh đăng bài thành công!"
        : "📅 Đã duyệt — bài sẽ lên đúng lịch ở tab Lịch đăng.",
    );
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
        <p className={styles.dropTitle}>Thả ảnh hoặc clip vào đây, hoặc</p>
        <div className={styles.dropActions}>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*,video/mp4,video/quicktime,video/webm"
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
            {uploading ? "Đang tải lên…" : "+ Tải ảnh / clip lên"}
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
        <section className={styles.uploadList} aria-label="Ảnh và clip đang nạp">
          {uploads.map((upload) => (
            <article
              key={upload.key}
              className={`${styles.uploadItem} ${
                upload.status === "failed" ? styles.uploadItemFailed : ""
              }`}
            >
              {upload.isVideo ? (
                <video
                  className={styles.uploadPreview}
                  src={upload.previewUrl}
                  muted
                  playsInline
                  preload="metadata"
                  aria-label={`Xem trước ${upload.fileName}`}
                />
              ) : (
                <img
                  className={styles.uploadPreview}
                  src={upload.previewUrl}
                  alt={`Xem trước ${upload.fileName}`}
                />
              )}
              <div className={styles.uploadBody}>
                <div className={styles.uploadTopline}>
                  <span className={styles.uploadName}>{upload.fileName}</span>
                  <span
                    className={`${styles.uploadPercent} ${
                      upload.status === "failed" ? styles.uploadPercentFailed : ""
                    }`}
                  >
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
                    className={`${styles.progressBar} ${
                      upload.status === "failed" ? styles.progressBarFailed : ""
                    }`}
                    style={{
                      width: `${upload.status === "failed" ? 100 : upload.progress}%`,
                    }}
                  />
                </div>
                {upload.isVideo && upload.status === "complete"
                  ? renderClipEligibility(upload.asset)
                  : null}
              </div>
              {upload.status === "uploading" ? (
                <button
                  type="button"
                  className={styles.cancelUpload}
                  onClick={() => cancelUpload(upload.key)}
                >
                  Huỷ
                </button>
              ) : (
                <button
                  type="button"
                  className={styles.removeUpload}
                  onClick={() => removeUpload(upload.key)}
                  aria-label={`Xoá ${upload.fileName}`}
                  title="Xoá mục này"
                >
                  Xoá
                </button>
              )}
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
          disabled={(!chips.length && !note.trim()) || uploading}
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



      {poll.status === "failed" ? (
        <ErrorState
          title="Havi chưa viết được lần này"
          body="Chị bấm viết lại giúp em nhé — liệu thô vẫn còn nguyên."
          action={
            <Button
              variant="outline"
              onClick={() => {
                poll.resetJob();
              }}
            >
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
                    <>
                      <div className={styles.generatedAiImageBox}>
                        <img
                          src={getTopicImage(item.media_note, item.text)}
                          alt="Ảnh minh hoạ do Havi AI tự tạo"
                          className={styles.generatedAiImage}
                        />
                        <span className={styles.aiImageBadge}>✨ Ảnh minh hoạ AI đính kèm</span>
                      </div>
                      <p className={styles.draftBody}>{item.text}</p>
                      {item.media_note ? (
                        <div className={styles.mediaNoteBox}>
                          <p className={styles.mediaNoteText}>
                            💡 <strong>Gợi ý ảnh/video:</strong> {item.media_note}
                          </p>
                        </div>
                      ) : null}
                    </>
                  )}
                  <div className={styles.draftFooter}>
                    <div className={styles.draftActions}>
                      <Button
                        variant="primary"
                        disabled={busy}
                        onClick={() => onApprove(item.id, new Date().toISOString())}
                      >
                        {busyIds.includes(item.id) ? "⚡ Đang đăng…" : "⚡ Đăng ngay"}
                      </Button>
                      <Button
                        variant="outline"
                        disabled={busy}
                        onClick={() => onApprove(item.id)}
                      >
                        📅 Lên lịch
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

      {/* Popup Modal Thông Báo Đã Đăng Bài Thành Công */}
      {publishedModal ? (
        <div
          className={styles.modalOverlay}
          onClick={(e) => {
            if (e.target === e.currentTarget) setPublishedModal(null);
          }}
        >
          <div className={styles.publishModalCard} role="dialog" aria-modal="true">
            <div className={styles.publishModalHeader}>
              <span className={styles.publishModalIcon}>
                {publishedModal.isInstant ? "🚀" : "📅"}
              </span>
              <h3 className={styles.publishModalTitle}>{publishedModal.title}</h3>
            </div>
            <p className={styles.publishModalBody}>{publishedModal.body}</p>
            <div className={styles.publishModalActions}>
              <Button variant="outline" onClick={() => setPublishedModal(null)}>
                Đóng
              </Button>
              <Button
                variant="primary"
                onClick={() => {
                  setPublishedModal(null);
                  window.location.href = "/lich-dang";
                }}
              >
                Xem Lịch Đăng →
              </Button>
            </div>
          </div>
        </div>
      ) : null}

      {/* Floating Toast Notification ở góc phải màn hình theo chuẩn MIT */}
      <ToastContainer toasts={toasts} onDismiss={removeToast} />
    </>
  );
}
