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
  dismissAllItems,
  dismissItem,
  generateItemImage,
  generateItemVideo,
  listPendingItems,
  mediaTypeOf,
  rejectItem,
  updateItemMedia,
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
import { VoiceRecorderModal } from "@/features/voice-note/voice-recorder-modal";
import { generateKineticShortVideo } from "./kinetic-video-generator";
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
    combined.includes("công nghệ") ||
    combined.includes("tech") ||
    combined.includes("ai") ||
    combined.includes("agent") ||
    combined.includes("lập trình") ||
    combined.includes("máy tính") ||
    combined.includes("khóa học") ||
    combined.includes("đào tạo") ||
    combined.includes("nhật minh")
  ) {
    return "https://images.unsplash.com/photo-1531482615713-2afd69097998?w=1200&q=80";
  }
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
  const [voiceModalOpen, setVoiceModalOpen] = useState(false);
  const [publishedModal, setPublishedModal] = useState<{
    title: string;
    body: string;
    isInstant: boolean;
  } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);
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
      title: "Havi vừa tạo 5 bản nháp mới đa kênh",
      description: "Các bản nháp bài đăng Facebook, Google Maps SEO, TikTok, YouTube Shorts, Facebook Reels đã sẵn sàng cho bạn duyệt.",
    });
    setToasts((prev) => prev.filter((t) => t.type !== "loading"));
    addToast({
      type: "success",
      title: "Havi đã sáng tạo xong bài mới!",
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
        // Đưa media vừa upload vào chip liệu thô
        setChips((prev) => [
          ...prev,
          {
            key: asset.id,
            kind: "photo",
            label: file.name,
            previewUrl: row.previewUrl,
            input: {
              kind: "photo",
              media_asset_id: asset.id,
              preview_url: row.previewUrl,
            },
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

    // Hiển thị Toast góc phải màn hình
    addToast({
      type: "loading",
      title: "Havi đang viết bài cho tiệm...",
      description: "Đang hoàn thiện bài viết và tối ưu cho từng kênh. Bản nháp sẽ sẵn sàng trong giây lát!",
    });
  }

  async function handleVoiceDirectGenerate(text: string) {
    const newChip: RawChip = {
      key: makeNoteChipKey(chips.length),
      kind: "text",
      label: text.length > 40 ? `${text.slice(0, 40)}…` : text,
      input: { kind: "text", text },
    };
    const currentChips = [...chips, newChip];
    setError(null);
    setNotice(null);

    const key = makeJobKey(currentChips);
    const result = await createJob(
      currentChips.map((c) => c.input),
      key,
    );
    if (!result.ok) {
      setError(result.message);
      setQuotaKey((k) => k + 1);
      return;
    }
    for (const chip of currentChips) forgetPreviewUrl(chip.previewUrl);
    setChips([]);
    setUploads([]);
    setNote("");
    setNoteOpen(true);

    poll.addJobId(result.data.id);
    setJobId(result.data.id);
    setQuotaKey((k) => k + 1);

    addToast({
      type: "loading",
      title: "Havi đang viết bài từ giọng nói...",
      description: "Nhân viên AI đang sáng tạo bài viết đa kênh từ lời thu âm của chị!",
    });
  }

  function handleVoiceInsertNote(text: string) {
    setNote(text);
    setNoteOpen(true);
    addToast({
      type: "success",
      icon: "🎙️",
      title: "Đã chèn giọng nói vào ô ghi chú",
      description: "Chị có thể sửa lại câu chữ hoặc bấm nút 'Để Havi viết cho chị' bên dưới.",
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
        ? "Nội dung đang được Havi gửi trực tiếp lên kênh của tiệm. Anh/chị có thể kiểm tra trực tiếp trên kênh hoặc theo dõi trong Lịch đăng bài nhé!"
        : "Bài viết đã được duyệt và xếp lịch tự động. Havi sẽ tự động xuất bản bài viết đúng giờ đã chọn.",
      isInstant: !!scheduledAt,
    });
    setNotice(
      scheduledAt
        ? "⚡ Đã phát lệnh đăng bài thành công!"
        : "📅 Đã duyệt — bài sẽ lên đúng lịch ở tab Lịch đăng.",
    );
  }

  async function onDismiss(id: string) {
    setBusyIds((prev) => [...prev, id]);
    const result = await dismissItem(id);
    setBusyIds((prev) => prev.filter((b) => b !== id));
    if (!result.ok) {
      setError(result.message);
      loadItems(true);
      return;
    }
    setItems((prev) => prev.filter((i) => i.id !== id));
    addToast({
      type: "info",
      icon: "🗑️",
      title: "Đã xoá bài nháp",
      description: "Bài viết đã được xoá vĩnh viễn khỏi hàng chờ.",
    });
  }

  async function onDismissAll() {
    const ids = items.map((i) => i.id);
    if (!ids.length) return;
    if (!confirm(`Bạn có chắc chắn muốn xoá tất cả ${ids.length} bản nháp này không?`)) {
      return;
    }
    setBusyIds(ids);
    const result = await dismissAllItems(ids);
    setBusyIds([]);
    if (!result.ok) {
      setError(result.message);
      return;
    }
    setItems([]);
    addToast({
      type: "info",
      icon: "🗑️",
      title: "Đã dọn sạch bản nháp",
      description: `Đã xoá ${result.data.length} bài nháp khỏi danh sách.`,
    });
  }

  async function onApproveAll() {
    const ids = items.map((i) => i.id);
    if (!ids.length) return;
    setBusyIds(ids);
    const result = await approveAll(ids, true);
    setBusyIds([]);
    if (!result.ok) {
      setError(result.message);
      return;
    }
    setPublishedModal({
      title: "🚀 Đã phát lệnh đăng ngay tất cả!",
      body: `Havi đang đồng loạt gửi ${result.data.approved.length} bài lên các kênh Facebook, TikTok, YouTube, Google Maps. Bạn có thể kiểm tra trực tiếp trên các kênh hoặc Lịch đăng bài nhé!`,
      isInstant: true,
    });
    loadItems();
  }

  const [generatingImageId, setGeneratingImageId] = useState<string | null>(null);
  const [renderingVideoId, setRenderingVideoId] = useState<string | null>(null);
  const [enhancedImageIds, setEnhancedImageIds] = useState<string[]>([]);

  async function handleAiRenderVideo(itemId: string) {
    const item = items.find((i) => i.id === itemId);
    if (!item) return;

    setRenderingVideoId(itemId);
    const toastId = addToast({
      type: "loading",
      title: "AI đang dựng Video 9:16...",
      description: "Đang tự động bóc tách Hook 3s, tạo hiệu ứng chuyển động và chèn phụ đề chữ vàng nhảy nhót.",
    });

    try {
      const topicImg =
        (item.media_url && !item.media_url.endsWith(".mp4") ? item.media_url : null) ||
        uploads.find((u) => u.previewUrl)?.previewUrl ||
        getTopicImage(item.media_note, item.text);

      const dynamicVideoUrl = await generateKineticShortVideo({
        text: item.text,
        channel: item.channel,
        mediaNote: item.media_note,
        imageUrl: topicImg,
        brandName: "TRUNG TÂM CÔNG NGHỆ NHẬT MINH",
        hotline: "0984 883 750",
      });

      await updateItemMedia(itemId, dynamicVideoUrl);

      setItems((prev) =>
        prev.map((i) =>
          i.id === itemId
            ? {
                ...i,
                media_url: dynamicVideoUrl,
                media_note: "🎬 Video 9:16 đã dựng hoàn tất kèm phụ đề động",
              }
            : i,
        ),
      );
      removeToast(toastId);
      addToast({
        type: "success",
        icon: "🎬",
        title: "Đã dựng xong Video 9:16!",
        description: "Clip dài 6s đã sẵn sàng để bạn xem thử và phát lệnh đăng lên kênh ngay.",
      });
    } catch {
      removeToast(toastId);
      await generateItemVideo(itemId, "9:16");
    } finally {
      setRenderingVideoId(null);
    }
  }

  async function handleAiGenerateImage(itemId: string) {
    setGeneratingImageId(itemId);
    addToast({
      type: "loading",
      title: "Gemini đang tạo ảnh AI...",
      description: "Đang tạo bức ảnh chất lượng cao 4K chuẩn studio cho bài viết của bạn.",
    });
    const res = await generateItemImage(itemId, "3d_studio");
    setGeneratingImageId(null);
    if (res.ok) {
      setItems((prev) =>
        prev.map((i) =>
          i.id === itemId
            ? { ...i, media_url: res.data.media_url, media_note: "✨ Ảnh AI tạo sinh" }
            : i,
        ),
      );
      addToast({
        type: "success",
        icon: "✨",
        title: "Đã tạo ảnh AI thành công!",
        description: "Bức ảnh mới lung linh đã được gắn trực tiếp vào bài viết.",
      });
    } else {
      setError(res.message);
    }
  }

  function handleMagicEnhance(itemId: string) {
    setEnhancedImageIds((prev) =>
      prev.includes(itemId) ? prev.filter((id) => id !== itemId) : [...prev, itemId],
    );
    addToast({
      type: "success",
      icon: "🪄",
      title: "Đã tút lại ảnh (Magic Enhance)!",
      description: "Đã nâng cao ánh sáng, tăng độ sắc nét HD và làm nổi bật chủ thể.",
    });
  }

  async function handleRemoveImage(itemId: string) {
    const res = await updateItemMedia(itemId, null);
    if (res.ok) {
      setItems((prev) =>
        prev.map((i) => (i.id === itemId ? { ...i, media_url: null } : i)),
      );
      addToast({
        type: "info",
        icon: "❌",
        title: "Đã gỡ ảnh đính kèm",
        description: "Bài viết này sẽ được đăng dưới dạng bài viết chữ (Text post).",
      });
    }
  }

  async function handleShareToPersonalProfile(text: string) {
    try {
      if (typeof navigator !== "undefined" && navigator.clipboard) {
        await navigator.clipboard.writeText(text);
      }
      addToast({
        type: "success",
        icon: "📋",
        title: "Đã copy nội dung bài viết!",
        description: "Havi đã copy sẵn bài viết, bạn chỉ việc Dán (Ctrl+V) lên Trang cá nhân để đăng nhé.",
      });
      window.open("https://www.facebook.com", "_blank");
    } catch {
      window.open("https://www.facebook.com", "_blank");
    }
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
        <p className={styles.dropTitle}>Chụp ảnh, quay video hoặc gõ vài dòng — Nhân viên AI viết bài ngay</p>
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
          <input
            ref={cameraInputRef}
            type="file"
            accept="image/*,video/*"
            capture="environment"
            hidden
            data-testid="camera-input"
            onChange={(e) => onPickFiles(e.target.files)}
          />
          <Button
            variant="primary"
            disabled={uploading}
            onClick={() => cameraInputRef.current?.click()}
          >
            📸 Chụp ảnh / Video
          </Button>
          <Button
            variant="outline"
            disabled={uploading}
            onClick={() => setVoiceModalOpen(true)}
            data-testid="btn-voice-modal"
          >
            🎙️ Ghi âm giọng nói
          </Button>
          <Button
            variant="outline"
            disabled={uploading}
            onClick={() => fileInputRef.current?.click()}
          >
            {uploading ? "Đang tải lên…" : "+ Thư viện ảnh / clip"}
          </Button>
          <Button variant="outline" onClick={() => setNoteOpen((v) => !v)}>
            ✍️ Gõ ghi chú nhanh
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

        {/* 1-Tap Fast Template Presets */}
        <div className={styles.presetSection}>
          <div className={styles.presetHeader}>
            <span>⚡</span>
            <span>Ý tưởng bài viết 1-chạm (Bấm để điền nhanh):</span>
          </div>
          <div className={styles.presetGrid}>
            {[
              {
                icon: "💆",
                title: "Spa / Chăm sóc da",
                text: "Ưu đãi chăm sóc da chuyên sâu cuối tuần: Giảm 20% + Tặng gói massage cổ vai gáy 15 phút cho khách đặt lịch trước.",
              },
              {
                icon: "☕",
                title: "F&B / Quán ăn & Cafe",
                text: "Giới thiệu món đặc biệt mới tuần này: Tặng kèm 1 đồ uống mát lạnh cho bàn từ 2 người, áp dụng từ nay đến Chủ Nhật.",
              },
              {
                icon: "🏢",
                title: "Bất động sản vị trí đẹp",
                text: "Căn hộ 2 phòng ngủ view hồ thoáng mát, đầy đủ nội thất cao cấp xách vali vào ở ngay, sổ hồng sẵn công chứng trong ngày.",
              },
              {
                icon: "💻",
                title: "Đào tạo Tech / Kỹ năng số",
                text: "Khai giảng khóa học Kỹ thuật số thực chiến 1 kèm 1: Học trên dự án thật, cam kết hỗ trợ việc làm sau khóa học.",
              },
              {
                icon: "🛍️",
                title: "Shop / Flash Sale",
                text: "Bộ sưu tập mới về ngập kệ: Flash sale tri ân khách quen giảm 10% toàn bộ sản phẩm trong 48 giờ tới.",
              },
              {
                icon: "🔧",
                title: "Dịch vụ & Bảo dưỡng",
                text: "Dịch vụ bảo dưỡng sửa chữa tận nơi nhanh chóng, bảo hành 6 tháng uy tín, gọi là có mặt sau 15 phút.",
              },
            ].map((preset) => (
              <button
                key={preset.title}
                type="button"
                className={styles.presetChip}
                onClick={() => {
                  setNote(preset.text);
                  setNoteOpen(true);
                }}
              >
                <span>{preset.icon}</span>
                <span>{preset.title}</span>
              </button>
            ))}
          </div>
        </div>
      </section>

      {uploads.length ? (
        <section className={styles.uploadList} aria-label="Ảnh và clip đang nạp">
          {uploads.map((upload) => (
            <article
              key={upload.key}
              className={`${styles.uploadItem} ${
                upload.status === "failed" ? styles.uploadItemFailed : ""
              }`}
              style={{ maxWidth: "540px", margin: "8px 0" }}
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
          className={styles.heroGenerateBtn}
          onClick={generate}
          disabled={(!chips.length && !note.trim()) || uploading || generating}
        >
          {generating ? "⏳ Havi đang viết bài (5 Kênh)…" : "⚡ Để Havi viết bài ngay (5 Kênh)"}
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
          <div>
            <h2 className={styles.draftsTitle}>
              {items.length} bản nháp trong kho
            </h2>
            {items.length > 0 ? (
              <p style={{ fontSize: "13px", color: "#64748B", marginTop: "3px" }}>
                Gồm: {items.filter((i) => i.channel === "facebook_page" || i.channel === "google_business" || i.channel === "zalo_oa").length} Bài Viết &amp; Local SEO • {items.filter((i) => i.channel === "tiktok" || i.channel === "youtube" || i.channel === "reels").length} Video Ngắn 9:16
              </p>
            ) : null}
          </div>
          <div style={{ display: "flex", gap: "10px", alignItems: "center", flexWrap: "wrap" }}>
            <Button
              type="button"
              variant="outline"
              style={{ color: "#DC2626", borderColor: "#FCA5A5", background: "#FEF2F2" }}
              onClick={onDismissAll}
              disabled={!items.length || busyIds.length > 0}
            >
              🗑️ Xoá tất cả bản nháp
            </Button>
            <Button
              type="button"
              variant="primary"
              onClick={onApproveAll}
              disabled={!items.length || busyIds.length > 0}
            >
              🚀 Duyệt &amp; Đăng ngay tất cả ({items.length === 5 ? "5 Kênh" : `${items.length} bài`})
            </Button>
          </div>
        </div>

        {loading ? (
          <LoadingState title="Đang tải bản nháp…" />
        ) : items.length === 0 ? (
          <EmptyState
            title="Chưa có bản nháp nào chờ duyệt"
            body="Nạp vài tấm ảnh hoặc gõ vài dòng, Havi sẽ viết bài cho chị."
          />
        ) : (
          <div>
            {(() => {
              const channelBadges: Record<
                string,
                { icon: string; bg: string; color: string; border: string }
              > = {
                facebook_page: {
                  icon: "📘",
                  bg: "#EFF6FF",
                  color: "#1D4ED8",
                  border: "#BFDBFE",
                },
                google_business: {
                  icon: "📍",
                  bg: "#ECFDF5",
                  color: "#047857",
                  border: "#A7F3D0",
                },
                tiktok: {
                  icon: "🎵",
                  bg: "#FDF2F8",
                  color: "#BE185D",
                  border: "#FBCFE8",
                },
                youtube: {
                  icon: "▶️",
                  bg: "#FEF2F2",
                  color: "#B91C1C",
                  border: "#FECACA",
                },
                reels: {
                  icon: "🎬",
                  bg: "#FAF5FF",
                  color: "#7E22CE",
                  border: "#E9D5FF",
                },
                zalo_oa: {
                  icon: "💬",
                  bg: "#F0F9FF",
                  color: "#0369A1",
                  border: "#BAE6FD",
                },
              };

              const postGroup = items.filter(
                (i) =>
                  i.channel === "facebook_page" ||
                  i.channel === "google_business" ||
                  i.channel === "zalo_oa",
              );
              const videoGroup = items.filter(
                (i) =>
                  i.channel === "tiktok" ||
                  i.channel === "youtube" ||
                  i.channel === "reels",
              );
              const otherGroup = items.filter(
                (i) => !postGroup.includes(i) && !videoGroup.includes(i),
              );

              const renderDraftCard = (item: ContentItem) => {
                const busy = busyIds.includes(item.id);
                const badgeInfo = channelBadges[item.channel];
                return (
                  <article key={item.id} className={styles.draftCard}>
                    <div className={styles.draftMeta}>
                      <span
                        style={{
                          display: "inline-flex",
                          alignItems: "center",
                          gap: "6px",
                          padding: "3px 10px",
                          borderRadius: "999px",
                          fontSize: "12px",
                          fontWeight: 700,
                          background: badgeInfo?.bg || "#F1F5F9",
                          color: badgeInfo?.color || "#334155",
                          border: `1px solid ${badgeInfo?.border || "#E2E8F0"}`,
                        }}
                      >
                        <span>{badgeInfo?.icon || "📄"}</span>
                        <span>
                          {channelLabels[item.channel as keyof typeof channelLabels] ??
                            item.channel}
                        </span>
                      </span>
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
                        {item.channel === "tiktok" ||
                        item.channel === "youtube" ||
                        item.channel === "reels" ? (
                          <div style={{ marginBottom: "12px" }}>
                            <div className={styles.inPlaceVideoContainer}>
                              {(() => {
                                const isCustom = Boolean(
                                  item.media_url &&
                                    (item.media_url.startsWith("blob:") ||
                                      item.media_url.endsWith(".mp4") ||
                                      item.media_url.includes("video") ||
                                      item.media_url.startsWith("/") ||
                                      item.media_url.startsWith("http")),
                                );
                                const videoSrc = isCustom ? item.media_url! : "/test_tiktok.mp4";
                                const isBlob = Boolean(item.media_url?.startsWith("blob:"));
                                return (
                                  <video
                                    key={`${item.id}-${item.media_url || "default"}`}
                                    src={videoSrc}
                                    poster={isBlob ? undefined : getTopicImage(item.media_note, item.text)}
                                    controls
                                    playsInline
                                    autoPlay={isBlob}
                                    className={styles.inPlaceVideoPlayer}
                                  >
                                    <source src={videoSrc} type="video/mp4" />
                                    <source src={videoSrc} type="video/webm" />
                                  </video>
                                );
                              })()}
                              <div className={styles.inPlaceVideoFooter}>
                                <span>🎬 Video 9:16 Sẵn Sàng (Phụ đề động &amp; Nhạc)</span>
                                <button
                                  type="button"
                                  className={styles.inPlaceVideoResetBtn}
                                  onClick={() => handleRemoveImage(item.id)}
                                >
                                  ❌ Đổi lại
                                </button>
                              </div>
                            </div>
                            <div
                              style={{
                                display: "flex",
                                gap: "6px",
                                marginTop: "8px",
                                marginBottom: "12px",
                                flexWrap: "wrap",
                              }}
                            >
                              <button
                                type="button"
                                className={styles.inPlaceRenderVideoBtn}
                                disabled={renderingVideoId === item.id}
                                onClick={() => handleAiRenderVideo(item.id)}
                              >
                                {renderingVideoId === item.id
                                  ? "⏳ Đang dựng Video 9:16…"
                                  : "🎬 AI Dựng Video 9:16 Ngay"}
                              </button>
                              <button
                                type="button"
                                style={{
                                  fontSize: "12px",
                                  padding: "4px 10px",
                                  borderRadius: "6px",
                                  border: "1px solid #93C5FD",
                                  background: "#EFF6FF",
                                  color: "#1D4ED8",
                                  cursor: "pointer",
                                  fontWeight: 600,
                                }}
                                disabled={generatingImageId === item.id}
                                onClick={() => handleAiGenerateImage(item.id)}
                              >
                                {generatingImageId === item.id
                                  ? "✨ Đang vẽ…"
                                  : "✨ AI Vẽ Lại Đẹp Hơn"}
                              </button>
                              <button
                                type="button"
                                style={{
                                  fontSize: "12px",
                                  padding: "4px 10px",
                                  borderRadius: "6px",
                                  border: "1px solid #FCD34D",
                                  background: "#FFFBEB",
                                  color: "#B45309",
                                  cursor: "pointer",
                                  fontWeight: 600,
                                }}
                                onClick={() => handleMagicEnhance(item.id)}
                              >
                                {enhancedImageIds.includes(item.id)
                                  ? "🪄 Đã tút nét HD"
                                  : "🪄 Tút Lại Ảnh Thật"}
                              </button>
                              <button
                                type="button"
                                style={{
                                  fontSize: "12px",
                                  padding: "4px 10px",
                                  borderRadius: "6px",
                                  border: "1px solid #E5E7EB",
                                  background: "#F9FAFB",
                                  color: "#4B5563",
                                  cursor: "pointer",
                                }}
                                onClick={() => handleRemoveImage(item.id)}
                                title="Xoá video này"
                              >
                                ❌ Bỏ video
                              </button>
                            </div>
                          </div>
                        ) : (
                          <div style={{ marginBottom: "12px" }}>
                            {item.media_url !== "__NONE__" ? (
                              <>
                                <div className={styles.generatedAiImageBox}>
                                  <img
                                    src={
                                      item.media_url && !item.media_url.endsWith(".mp4")
                                        ? item.media_url
                                        : uploads.find((u) => u.previewUrl)?.previewUrl ||
                                          getTopicImage(item.media_note, item.text)
                                    }
                                    alt="Ảnh đính kèm bài viết"
                                    className={styles.generatedAiImage}
                                    onError={(e) => {
                                      (e.currentTarget as HTMLImageElement).src = getTopicImage(
                                        item.media_note,
                                        item.text,
                                      );
                                    }}
                                    style={
                                      enhancedImageIds.includes(item.id)
                                        ? {
                                            filter: "contrast(1.15) brightness(1.08) saturate(1.2)",
                                            transform: "scale(1.02)",
                                            transition: "all 0.3s ease",
                                          }
                                        : undefined
                                    }
                                  />
                                  <span className={styles.aiImageBadge}>
                                    {enhancedImageIds.includes(item.id)
                                      ? "🪄 Đã tút nét & tăng sáng (Magic Enhance)"
                                      : item.media_url || uploads.some((u) => u.previewUrl)
                                      ? "📸 Ảnh bạn nạp đính kèm"
                                      : "✨ Ảnh minh hoạ AI"}
                                  </span>
                                </div>
                                <div
                                  style={{
                                    display: "flex",
                                    gap: "6px",
                                    marginTop: "8px",
                                    marginBottom: "12px",
                                    flexWrap: "wrap",
                                  }}
                                >
                                  <button
                                    type="button"
                                    style={{
                                      fontSize: "12px",
                                      padding: "4px 10px",
                                      borderRadius: "6px",
                                      border: "1px solid #FCD34D",
                                      background: "#FFFBEB",
                                      color: "#B45309",
                                      cursor: "pointer",
                                      fontWeight: 600,
                                    }}
                                    onClick={() => handleMagicEnhance(item.id)}
                                  >
                                    {enhancedImageIds.includes(item.id)
                                      ? "🪄 Đã tút nét HD"
                                      : "🪄 Tút Lại Ảnh Thật"}
                                  </button>
                                  <button
                                    type="button"
                                    style={{
                                      fontSize: "12px",
                                      padding: "4px 10px",
                                      borderRadius: "6px",
                                      border: "1px solid #93C5FD",
                                      background: "#EFF6FF",
                                      color: "#1D4ED8",
                                      cursor: "pointer",
                                      fontWeight: 600,
                                    }}
                                    disabled={generatingImageId === item.id}
                                    onClick={() => handleAiGenerateImage(item.id)}
                                  >
                                    {generatingImageId === item.id
                                      ? "✨ Đang vẽ…"
                                      : "✨ AI Vẽ Lại Đẹp Hơn"}
                                  </button>
                                  <button
                                    type="button"
                                    style={{
                                      fontSize: "12px",
                                      padding: "4px 10px",
                                      borderRadius: "6px",
                                      border: "1px solid #E5E7EB",
                                      background: "#F9FAFB",
                                      color: "#4B5563",
                                      cursor: "pointer",
                                    }}
                                    onClick={() => handleRemoveImage(item.id)}
                                    title="Xoá ảnh này để đăng bài thuần chữ"
                                  >
                                    ❌ Bỏ ảnh
                                  </button>
                                </div>
                              </>
                            ) : (
                              <div
                                style={{
                                  padding: "10px 14px",
                                  background: "#F8FAFC",
                                  borderRadius: "8px",
                                  marginBottom: "12px",
                                  display: "flex",
                                  justifyContent: "space-between",
                                  alignItems: "center",
                                  flexWrap: "wrap",
                                  gap: "8px",
                                  border: "1px dashed #CBD5E1",
                                }}
                              >
                                <span style={{ fontSize: "13px", color: "#64748B" }}>
                                  📄 Bài viết thuần văn bản (Không đính kèm ảnh)
                                </span>
                                <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
                                  <button
                                    type="button"
                                    style={{
                                      fontSize: "12px",
                                      padding: "4px 10px",
                                      borderRadius: "6px",
                                      border: "1px solid #93C5FD",
                                      background: "#EFF6FF",
                                      color: "#1D4ED8",
                                      cursor: "pointer",
                                      fontWeight: 600,
                                    }}
                                    disabled={generatingImageId === item.id}
                                    onClick={() => handleAiGenerateImage(item.id)}
                                  >
                                    {generatingImageId === item.id
                                      ? "✨ Đang vẽ…"
                                      : "✨ Tạo ảnh AI"}
                                  </button>
                                </div>
                              </div>
                            )}
                          </div>
                        )}
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
                          type="button"
                          variant="primary"
                          disabled={busy}
                          onClick={() => onApprove(item.id, new Date().toISOString())}
                        >
                          {busyIds.includes(item.id) ? "⚡ Đang đăng…" : "⚡ Đăng ngay"}
                        </Button>
                        <Button
                          type="button"
                          variant="outline"
                          disabled={busy}
                          onClick={() => onApprove(item.id)}
                        >
                          📅 Lên lịch
                        </Button>
                        <Button
                          type="button"
                          variant="outline"
                          disabled={busy}
                          onClick={() =>
                            setEditingId(editingId === item.id ? null : item.id)
                          }
                        >
                          {editingId === item.id ? "Đang sửa" : "Sửa"}
                        </Button>
                        {(item.channel === "facebook_page" || item.channel === "reels") && (
                          <Button
                            type="button"
                            variant="outline"
                            style={{ color: "#1877F2", borderColor: "#BFDBFE" }}
                            onClick={() => handleShareToPersonalProfile(item.text)}
                            title="Copy nội dung và mở Facebook để đăng nhanh lên Trang cá nhân"
                          >
                            📲 Trang cá nhân
                          </Button>
                        )}
                        <Button
                          type="button"
                          variant="outline"
                          style={{ color: "#DC2626", borderColor: "#FCA5A5" }}
                          disabled={busy}
                          onClick={() => onDismiss(item.id)}
                        >
                          🗑️ Xoá
                        </Button>
                      </div>
                    </div>
                  </article>
                );
              };

              return (
                <div>
                  {postGroup.length > 0 && (
                    <div className={styles.groupSection}>
                      <div className={styles.groupHeaderPost}>
                        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                          <span style={{ fontSize: "17px", fontWeight: 800, color: "#0F172A" }}>
                            📸 Nhóm 1: Bài Viết &amp; Local SEO ({postGroup.length} bản)
                          </span>
                          <span className={styles.groupBadgePost}>
                            Facebook Fanpage &amp; Google Maps
                          </span>
                        </div>
                        <span style={{ fontSize: "12.5px", color: "#64748B", fontWeight: 500 }}>
                          Kể chuyện cảm xúc &amp; Kéo khách ghé tiệm
                        </span>
                      </div>
                      <div className={styles.draftsGrid}>
                        {postGroup.map(renderDraftCard)}
                      </div>
                    </div>
                  )}

                  {videoGroup.length > 0 && (
                    <div className={styles.groupSection}>
                      <div className={styles.groupHeaderVideo}>
                        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                          <span style={{ fontSize: "17px", fontWeight: 800, color: "#7E22CE" }}>
                            🎬 Nhóm 2: Video Ngắn Dọc 9:16 ({videoGroup.length} bản)
                          </span>
                          <span className={styles.groupBadgeVideo}>
                            TikTok, YouTube Shorts, Facebook Reels (1-Chạm Dựng Video)
                          </span>
                        </div>
                        <span style={{ fontSize: "12.5px", color: "#9333EA", fontWeight: 500 }}>
                          Hook 3s giật tít &amp; Phụ đề nhảy nhót
                        </span>
                      </div>
                      <div className={styles.draftsGrid}>
                        {videoGroup.map(renderDraftCard)}
                      </div>
                    </div>
                  )}

                  {otherGroup.length > 0 && (
                    <div className={styles.draftsGrid}>
                      {otherGroup.map(renderDraftCard)}
                    </div>
                  )}
                </div>
              );
            })()}
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

      <VoiceRecorderModal
        isOpen={voiceModalOpen}
        onClose={() => setVoiceModalOpen(false)}
        onInsertNote={handleVoiceInsertNote}
        onDirectGenerate={handleVoiceDirectGenerate}
      />

      {/* Floating Toast Notification ở góc phải màn hình theo chuẩn MIT */}
      <ToastContainer toasts={toasts} onDismiss={removeToast} />
    </>
  );
}
