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
  uploadRenderedVideoBlob,
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
import { TeleprompterModal } from "./teleprompter-modal";
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

/** "Clip này đăng được Reels nhưng không đăng được Shorts" — ngay lúc upload. */
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
  const [quotaKey, setQuotaKey] = useState(0);
  const [notice, setNotice] = useState<string | null>(null);
  const [busyIds, setBusyIds] = useState<string[]>([]);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [voiceModalOpen, setVoiceModalOpen] = useState(false);
  const [leadConversionEnabled, setLeadConversionEnabled] = useState(true);
  const [activeTab, setActiveTab] = useState<"all" | "video" | "posts">("all");
  const [selectedPlaybook, setSelectedPlaybook] = useState<string | null>(null);

  const [publishedModal, setPublishedModal] = useState<{
    title: string;
    body: string;
    isInstant: boolean;
  } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);
  const previewUrlsRef = useRef(new Set<string>());

  const CAMPAIGN_PLAYBOOKS = [
    {
      id: "flash_sale",
      icon: "🚀",
      tag: "Doanh Thu Đột Phá",
      title: "Flash Sale & Kéo Khách Gấp",
      desc: "Ưu đãi giờ vàng, tặng voucher trải nghiệm cho 20 khách đầu tiên nhắn tin/đặt lịch hôm nay.",
      text: "Ưu đãi giờ vàng đặc biệt cuối tuần: Tặng Voucher 20% hoặc quà tặng trải nghiệm cho 20 khách hàng đầu tiên nhắn tin/đặt lịch hôm nay.",
    },
    {
      id: "viral_trend",
      icon: "🔥",
      tag: "Hút Triệu View TikTok",
      title: "Bắt Trend Video Viral",
      desc: "Kịch bản so sánh thực tế bắt trend drama/công nghệ, giữ chân người xem 3s đầu cực đỉnh.",
      text: "Bắt trend câu chuyện đời thực: Trong khi người ta còn loay hoay thì học viên/khách hàng tại cơ sở đã đạt kết quả vượt bậc chỉ sau 3 bước đơn giản.",
    },
    {
      id: "local_seo",
      icon: "📍",
      tag: "Kéo Khách Quanh 5km",
      title: "Thống Trị Google Maps SEO",
      desc: "Bài viết chuẩn SEO địa phương, tối ưu từ khóa ngành nghề để kéo khách vãng lai quanh tiệm.",
      text: "Dịch vụ chuyên nghiệp top đầu khu vực: Uy tín tận tâm, đội ngũ tay nghề cao, nhận tư vấn và báo giá minh bạch ngay trong 15 phút.",
    },
    {
      id: "social_proof",
      icon: "💎",
      tag: "Tăng Tỷ Lệ Chốt Đơn",
      title: "Khoe Kết Quả & Uy Tín",
      desc: "Câu chuyện khách hàng thật, ca cứu máy/dịch vụ xuất sắc tạo niềm tin tuyệt đối khi chốt sale.",
      text: "Cảm nhận thực tế của khách hàng/học viên sau khi trải nghiệm: Giải quyết triệt để vấn đề, an tâm tuyệt đối với chế độ bảo hành và đồng hành lâu dài.",
    },
  ];

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
      description: "Đã nạp vào danh sách bên dưới — cuộn xuống để duyệt bài ngay.",
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
    const chip = chips.find((c) => c.key === upload?.assetId);
    if (chip) removeChip(chip.key);
  }

  const uploading = uploads.some((upload) => upload.status === "uploading");
  const generating = poll.status === "queued" || poll.status === "processing";

  async function generate() {
    let currentChips = [...chips];
    if (note.trim()) {
      const extraChip: RawChip = {
        key: makeNoteChipKey(currentChips.length),
        kind: "text",
        label: note.trim().length > 40 ? `${note.trim().slice(0, 40)}…` : note.trim(),
        input: { kind: "text", text: note.trim() },
      };
      currentChips = [...currentChips, extraChip];
    }
    if (!currentChips.length) return;

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

  async function onApprovePostsGroup(instant: boolean) {
    const ids = postGroup.map((i) => i.id);
    if (!ids.length) return;
    setBusyIds(ids);
    const result = await approveAll(ids, instant);
    setBusyIds([]);
    if (!result.ok) {
      setError(result.message);
      return;
    }
    setPublishedModal({
      title: instant
        ? "🚀 Đã phát lệnh đăng Bài Viết (Facebook & Google Maps)!"
        : "📅 Đã lên lịch đăng Bài Viết lúc 11:30 trưa!",
      body: `Havi đã ${instant ? "phát lệnh đăng ngay" : "lên lịch tự động"} ${result.data.approved.length} bài viết chuẩn SEO lên Facebook Page & Google Business. Nhóm Video vẫn được lưu an toàn để chị quay clip xong đăng sau nhé!`,
      isInstant: instant,
    });
    loadItems();
  }

  async function onApproveVideosGroup(instant: boolean) {
    const readyVideos = videoGroup.filter(
      (i) => i.media_url && (i.media_url.startsWith("blob:") || i.media_url.endsWith(".mp4") || i.media_url.endsWith(".mov") || i.media_url.includes("video")),
    );
    if (!readyVideos.length) {
      addToast({
        type: "warning",
        title: "Chưa có clip quay thật",
        description: "Chị vui lòng bấm 'Tải Video Vừa Quay Lên' ở bên dưới trước khi duyệt đăng nhóm Video nhé!",
      });
      return;
    }
    const ids = readyVideos.map((i) => i.id);
    setBusyIds(ids);
    const result = await approveAll(ids, instant);
    setBusyIds([]);
    if (!result.ok) {
      setError(result.message);
      return;
    }
    setPublishedModal({
      title: instant
        ? "🎬 Đã phát lệnh xuất bản Video lên TikTok & Reels!"
        : "📅 Đã lên lịch xuất bản Video lúc 20:00 tối!",
      body: `Havi đã ${instant ? "phát lệnh xuất bản ngay" : "lên lịch khung giờ vàng"} ${result.data.approved.length} video ngắn thật lên TikTok, YouTube Shorts, Reels.`,
      isInstant: instant,
    });
    loadItems();
  }

  async function onApproveSmartReady(instant: boolean) {
    const readyItems = items.filter((i) => {
      const isVideo = i.channel === "tiktok" || i.channel === "youtube" || i.channel === "reels";
      if (!isVideo) return true;
      return Boolean(i.media_url && (i.media_url.startsWith("blob:") || i.media_url.endsWith(".mp4") || i.media_url.endsWith(".mov") || i.media_url.includes("video")));
    });
    if (!readyItems.length) return;
    const ids = readyItems.map((i) => i.id);
    setBusyIds(ids);
    const result = await approveAll(ids, instant);
    setBusyIds([]);
    if (!result.ok) {
      setError(result.message);
      return;
    }
    const pendingVideosCount = videoGroup.length - readyItems.filter((i) => i.channel === "tiktok" || i.channel === "youtube" || i.channel === "reels").length;
    setPublishedModal({
      title: instant
        ? `🚀 Đã phát lệnh đăng ${result.data.approved.length} kênh đã sẵn sàng!`
        : `📅 Đã lên lịch Khung Giờ Vàng cho ${result.data.approved.length} kênh đã sẵn sàng!`,
      body: pendingVideosCount > 0
        ? `Đã xử lý ${result.data.approved.length} bài viết (Facebook & Google Maps). Còn ${pendingVideosCount} kịch bản Video ngắn được giữ lại an toàn ở mục nháp để chị quay clip xong bấm đăng sau nhé!`
        : `Toàn bộ ${result.data.approved.length} kênh đã được ${instant ? "phát lệnh đăng ngay" : "xếp vào Lịch đăng tự động (11:30 trưa & 20:00 tối)"}.`,
      isInstant: instant,
    });
    loadItems();
  }

  async function onApproveAll() {
    return onApproveSmartReady(true);
  }

  async function onSmartScheduleAll() {
    return onApproveSmartReady(false);
  }

  const [generatingImageId, setGeneratingImageId] = useState<string | null>(null);
  const [enhancedImageIds, setEnhancedImageIds] = useState<string[]>([]);
  const [teleprompterItem, setTeleprompterItem] = useState<ContentItem | null>(null);
  const [shootingModes, setShootingModes] = useState<Record<string, "talking" | "broll">>({});
  const [generatingVideoId, setGeneratingVideoId] = useState<string | null>(null);

  async function handleGenerateAiCapCutVideo(itemId: string) {
    const item = items.find((i) => i.id === itemId);
    if (!item) return;

    setGeneratingVideoId(itemId);
    const toastId = addToast({
      type: "loading",
      title: "Đang tạo Video CapCut 9:16...",
      description: "Havi đang lồng chữ nổi 3D, chuyển động ảnh và beat nhạc nền synth...",
    });

    try {
      const generatedUrl = await generateKineticShortVideo({
        text: item.text,
        channel: item.channel,
        mediaNote: item.media_note,
        imageUrl: item.media_url && !item.media_url.endsWith(".mp4") ? item.media_url : undefined,
      });

      const isVideoItem = videoGroup.some((v) => v.id === itemId);
      const targetIds = isVideoItem ? videoGroup.map((v) => v.id) : [itemId];

      setItems((prev) =>
        prev.map((i) =>
          targetIds.includes(i.id)
            ? {
                ...i,
                media_url: generatedUrl,
                media_note: `🎬 Video CapCut 9:16 tự động lồng chữ & nhạc`,
              }
            : i,
        ),
      );

      removeToast(toastId);
      addToast({
        type: "success",
        icon: "✨",
        title: "Tạo Video CapCut 9:16 thành công!",
        description:
          isVideoItem && videoGroup.length > 1
            ? `Đã tạo và đồng bộ video cho toàn bộ ${videoGroup.length} kênh video ngắn!`
            : "Video ngắn dọc 9:16 đã sẵn sàng để phát hành.",
      });
    } catch {
      removeToast(toastId);
      addToast({
        type: "error",
        title: "Lỗi tạo video",
        description: "Không thể tạo video tự động, vui lòng thử lại.",
      });
    } finally {
      setGeneratingVideoId(null);
    }
  }

  async function handleUploadRealVideoForItem(itemId: string, file: File) {
    const toastId = addToast({
      type: "loading",
      title: "Đang gắn video thật...",
      description: `Đang tải clip "${file.name}" lên hệ thống Havi.`,
    });

    try {
      const uploadRes = await uploadRenderedVideoBlob(itemId, file);
      removeToast(toastId);
      if (uploadRes.ok) {
        const previewUrl = URL.createObjectURL(file);
        const isVideoItem = videoGroup.some((v) => v.id === itemId);
        const targetIds = isVideoItem ? videoGroup.map((v) => v.id) : [itemId];

        setItems((prev) =>
          prev.map((i) =>
            targetIds.includes(i.id)
              ? {
                  ...i,
                  media_url: previewUrl,
                  media_note: `🎬 Video thật của tiệm (${file.name})`,
                }
              : i,
          ),
        );

        if (isVideoItem) {
          const otherVideoIds = videoGroup.map((v) => v.id).filter((id) => id !== itemId);
          for (const otherId of otherVideoIds) {
            uploadRenderedVideoBlob(otherId, file).catch(() => {});
          }
        }

        addToast({
          type: "success",
          icon: "🎬",
          title: "Đã gắn & đồng bộ video thật!",
          description: isVideoItem && videoGroup.length > 1
            ? `Video thật đã được tự động gắn cho toàn bộ ${videoGroup.length} kênh video ngắn (TikTok, Reels, Shorts)!`
            : "Video thật của bạn đã sẵn sàng để phát hành lên kênh.",
        });
      } else {
        addToast({
          type: "error",
          title: "Không thể tải video",
          description: uploadRes.message || "Vui lòng thử lại với file video khác.",
        });
      }
    } catch {
      removeToast(toastId);
      addToast({
        type: "error",
        title: "Lỗi tải video",
        description: "Có lỗi khi tải video lên máy chủ, vui lòng thử lại.",
      });
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
      title: "🪄 Đã tút nét HD!",
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

  const readyVideosCount = videoGroup.filter(
    (i) =>
      i.media_url &&
      (i.media_url.startsWith("blob:") ||
        i.media_url.endsWith(".mp4") ||
        i.media_url.endsWith(".mov") ||
        i.media_url.endsWith(".webm") ||
        i.media_url.includes("video")),
  ).length;

  const totalReadyCount = postGroup.length + readyVideosCount;
  const pendingVideosCount = videoGroup.length - readyVideosCount;

  const renderDraftCard = (item: ContentItem) => {
    const busy = busyIds.includes(item.id);
    const badgeInfo = channelBadges[item.channel];
    const isVideoChannel =
      item.channel === "tiktok" ||
      item.channel === "youtube" ||
      item.channel === "reels";

    // Extract hook 3s if available
    let hookSnippet = "";
    if (isVideoChannel) {
      const match = item.text.match(/["“]([^"”\n]{6,80})["”]/) || item.text.match(/Hook[^:]*:\s*([^\n]+)/i);
      if (match && match[1]) {
        hookSnippet = match[1].trim();
      } else {
        const firstLine = item.text.split("\n")[0];
        if (firstLine.length <= 80) hookSnippet = firstLine;
      }
    }

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
              {channelLabels[item.channel as keyof typeof channelLabels] ?? item.channel}
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
            {isVideoChannel ? (
              <div style={{ marginBottom: "12px" }}>
                {(() => {
                  const hasRealVideo = Boolean(
                    item.media_url &&
                      (item.media_url.startsWith("blob:") ||
                        item.media_url.endsWith(".mp4") ||
                        item.media_url.endsWith(".mov") ||
                        item.media_url.endsWith(".webm") ||
                        item.media_url.includes("video")),
                  );

                  if (hasRealVideo) {
                    return (
                      <div className={styles.realVideoContainer}>
                        <div className={styles.realVideoBadge}>
                          <span>🟢 Clip Thật Đã Sẵn Sàng</span>
                        </div>
                        <video
                          key={`${item.id}-${item.media_url}`}
                          src={item.media_url!}
                          controls
                          playsInline
                          className={styles.inPlaceVideoPlayer}
                        />
                        <div className={styles.realVideoFooter}>
                          <span>🎬 Video quay thực tế của tiệm</span>
                          <button
                            type="button"
                            className={styles.inPlaceVideoResetBtn}
                            onClick={() => handleRemoveImage(item.id)}
                          >
                            ❌ Đổi clip khác
                          </button>
                        </div>
                      </div>
                    );
                  }

                  const firstSentence = item.text.split(/[.\n!?]/)[0]?.replace(/^[•*"-]\s*/, "").trim() || "";
                  const hookDisplay = hookSnippet || (firstSentence.length > 5 ? firstSentence.toUpperCase() : "BÍ QUYẾT TỰ HỌC & LÀM CHỦ CÔNG NGHỆ THỰC CHIẾN");

                  const currentMode = shootingModes[item.id] || "talking";

                  return (
                    <div className={styles.scriptCard}>
                      <div className={styles.scriptBadge}>
                        <span>🎬 Kịch Bản Video 9:16 • 2 Cách Làm Siêu Dễ</span>
                      </div>

                      {/* Bộ chuyển đổi 2 Chế Độ Quay */}
                      <div className={styles.shootingModeTabs}>
                        <button
                          type="button"
                          className={`${styles.shootingModeTab} ${currentMode === "talking" ? styles.shootingModeTabActive : ""}`}
                          onClick={() => setShootingModes((prev) => ({ ...prev, [item.id]: "talking" }))}
                        >
                          🗣️ Cách 1: Đọc Kịch Bản
                        </button>
                        <button
                          type="button"
                          className={`${styles.shootingModeTab} ${currentMode === "broll" ? styles.shootingModeTabActive : ""}`}
                          onClick={() => setShootingModes((prev) => ({ ...prev, [item.id]: "broll" }))}
                        >
                          📹 Cách 2: Quay Thao Tác 10s (Không Lộ Mặt)
                        </button>
                      </div>

                      {currentMode === "talking" ? (
                        <>
                          <div className={styles.scriptSection}>
                            <div className={styles.scriptSectionTitle}>
                              🎯 Câu Mở Đầu 3 Giây Giữ Chân (Hook)
                            </div>
                            <div className={`${styles.scriptSectionContent} ${styles.scriptHookHighlight}`}>
                              "{hookDisplay}"
                            </div>
                          </div>

                          <div className={styles.scriptSection}>
                            <div className={styles.scriptSectionTitle}>
                              💬 Lời Thoại Gợi Ý (Đọc ngắn gọn 20s)
                            </div>
                            <div className={styles.scriptSectionContent}>
                              "{item.text.length > 180 ? item.text.slice(0, 175) + "..." : item.text}"
                            </div>
                          </div>
                        </>
                      ) : (
                        <div className={styles.brollGuideBox}>
                          <div className={styles.brollGuideTitle}>
                            <span>📹 Hướng Dẫn Quay 10s Không Cần Lộ Mặt</span>
                          </div>
                          <p className={styles.brollGuideDesc}>
                            💡 {item.media_note || "Cầm điện thoại quay cận cảnh thao tác tay nghề thực tế tại tiệm trong 10-15s."}
                            <br />
                            <span style={{ color: "#059669", fontWeight: 700 }}>
                              ✨ Bạn không cần nói một lời nào — Havi sẽ tự động lồng nhạc nền và chữ nổi 3D thu hút!
                            </span>
                          </p>
                        </div>
                      )}

                      <div className={styles.scriptActions}>
                        {currentMode === "talking" ? (
                          <button
                            type="button"
                            className={styles.openTeleprompterBtn}
                            onClick={() => setTeleprompterItem(item)}
                          >
                            📱 Bật Máy Nhắc Chữ (30s)
                          </button>
                        ) : null}

                        <input
                          type="file"
                          id={`upload-real-video-${item.id}`}
                          accept="video/mp4,video/quicktime,video/webm"
                          style={{ display: "none" }}
                          onChange={(e) => {
                            const f = e.target.files?.[0];
                            if (f) handleUploadRealVideoForItem(item.id, f);
                          }}
                        />
                        <label
                          htmlFor={`upload-real-video-${item.id}`}
                          className={styles.uploadRealVideoBtn}
                        >
                          📤 {currentMode === "broll" ? "Tải Clip 10s Vừa Quay Lên" : "Tải Video Vừa Quay Lên"}
                        </label>

                        <button
                          type="button"
                          className={styles.aiCapcutBtn}
                          disabled={generatingVideoId === item.id}
                          onClick={() => handleGenerateAiCapCutVideo(item.id)}
                          title="Tự động lồng chữ nổi 3D CapCut, hiệu ứng chuyển cảnh và nhạc nền"
                        >
                          {generatingVideoId === item.id ? "⏳ Đang tạo video..." : "🪄 Tạo Video CapCut (9:16)"}
                        </button>
                      </div>
                    </div>
                  );
                })()}
              </div>
            ) : null}

            {/* Bài viết Facebook/Google Maps */}
            {!isVideoChannel ? (
              <div style={{ marginBottom: "12px" }}>
                {item.media_url && !item.media_url.endsWith(".mp4") ? (
                  <div className={styles.generatedAiImageBox}>
                    <img
                      src={item.media_url}
                      alt="Ảnh bài viết"
                      className={styles.generatedAiImage}
                      style={{
                        filter: enhancedImageIds.includes(item.id)
                          ? "contrast(1.15) saturate(1.2) brightness(1.05)"
                          : "none",
                      }}
                    />
                    <div className={styles.aiImageBadge}>
                      {enhancedImageIds.includes(item.id)
                        ? "🪄 Đã tối ưu chất lượng HD"
                        : "✨ Ảnh bài viết"}
                    </div>
                  </div>
                ) : null}

                <div
                  style={{
                    display: "flex",
                    gap: "6px",
                    marginTop: "8px",
                    marginBottom: "12px",
                    flexWrap: "wrap",
                  }}
                >
                  <Button
                    type="button"
                    variant="outline"
                    disabled={generatingImageId === item.id}
                    onClick={() => handleAiGenerateImage(item.id)}
                    style={{ fontSize: "11px", padding: "4px 8px" }}
                  >
                    {generatingImageId === item.id ? "⏳ Đang vẽ…" : "✨ AI Vẽ lại đẹp hơn"}
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => handleMagicEnhance(item.id)}
                    style={{ fontSize: "11px", padding: "4px 8px" }}
                  >
                    🪄 Tút lại ảnh thật
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => handleRemoveImage(item.id)}
                    style={{
                      fontSize: "11px",
                      padding: "4px 8px",
                      color: "#DC2626",
                    }}
                  >
                    ❌ Bỏ ảnh
                  </Button>
                </div>
              </div>
            ) : null}

            <p className={styles.draftBody}>{item.text}</p>

            {item.media_note ? (
              <div className={styles.mediaNoteBox}>
                <p className={styles.mediaNoteText}>
                  💡 <strong>Gợi ý hình ảnh/góc quay:</strong> {item.media_note}
                </p>
              </div>
            ) : null}

            <div className={styles.draftFooter}>
              <div className={styles.draftActions}>
                <Button
                  variant="primary"
                  disabled={busy}
                  onClick={() => onApprove(item.id, new Date().toISOString())}
                  style={{ flex: 1 }}
                >
                  {busy ? "Đang gửi…" : "⚡ Đăng ngay"}
                </Button>
                <Button
                  variant="outline"
                  disabled={busy}
                  onClick={() => onApprove(item.id)}
                >
                  Lên lịch
                </Button>
                <Button
                  variant="outline"
                  disabled={busy}
                  onClick={() => setEditingId(item.id)}
                >
                  Sửa
                </Button>
                <Button
                  variant="outline"
                  disabled={busy}
                  onClick={() => onDismiss(item.id)}
                  aria-label={`Bỏ bài ${item.channel}`}
                >
                  Bỏ qua
                </Button>
              </div>

              {item.channel === "facebook_page" || item.channel === "reels" ? (
                <div style={{ marginTop: "10px" }}>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => handleShareToPersonalProfile(item.text)}
                    style={{
                      width: "100%",
                      fontSize: "12px",
                      color: "#1877F2",
                      borderColor: "#BAE6FD",
                      background: "#F0F9FF",
                    }}
                  >
                    📋 Copy &amp; Đăng Trang Cá Nhân Facebook
                  </Button>
                </div>
              ) : null}
            </div>
          </>
        )}
      </article>
    );
  };

  return (
    <>
      <header className={styles.header}>
        <h1 className={styles.title}>
          <span>🎯 Trung Tâm Chiến Dịch Tăng Trưởng</span>
        </h1>
        <p className={styles.subtitle}>
          Sáng tạo đa kênh chuẩn thuật toán 2026: Video 9:16 Kinetic Subtitles, SEO Google Maps &amp; Tự động chốt Lead qua Inbox.
        </p>
        <div className={styles.roiBadgeContainer}>
          <span className={styles.roiBadge}>
            💰 Tiết kiệm 15.000.000đ/tháng chi phí Marketing Agency
          </span>
          <span className={`${styles.roiBadge} ${styles.roiBadgePurple}`}>
            ⚡ Tự động tối ưu Hook 3s &amp; SEO địa phương
          </span>
        </div>
      </header>

      <QuotaBanner reloadKey={quotaKey} />

      {/* BƯỚC 1: CHỌN CHIẾN DỊCH TĂNG TRƯỞNG */}
      <section className={styles.playbookSection} aria-label="Chọn chiến dịch">
        <div className={styles.stepTitle}>
          <span className={styles.stepNumber}>1</span>
          <span>Chọn Mục Tiêu Chiến Dịch Tăng Trưởng</span>
        </div>
        <div className={styles.playbookGrid}>
          {CAMPAIGN_PLAYBOOKS.map((playbook) => {
            const isActive = selectedPlaybook === playbook.id;
            return (
              <button
                key={playbook.id}
                type="button"
                className={`${styles.playbookCard} ${isActive ? styles.playbookCardActive : ""}`}
                onClick={() => {
                  setSelectedPlaybook(playbook.id);
                  setNote(playbook.text);
                  setNoteOpen(true);
                  addToast({
                    type: "info",
                    title: `Đã chọn: ${playbook.title}`,
                    description: "Đã nạp sẵn kịch bản chiến lược — bạn có thể bấm tạo bài ngay!",
                  });
                }}
              >
                <div className={styles.playbookIconHeader}>
                  <span className={styles.playbookIcon}>{playbook.icon}</span>
                  <span className={styles.playbookTag}>{playbook.tag}</span>
                </div>
                <h3 className={styles.playbookCardTitle}>{playbook.title}</h3>
                <p className={styles.playbookCardDesc}>{playbook.desc}</p>
              </button>
            );
          })}
        </div>
      </section>

      {/* BƯỚC 2: NẠP Ý TƯỞNG NHANH */}
      <section className={styles.dropZone} aria-label="Nạp liệu mới">
        <div className={styles.stepTitle} style={{ justifyContent: "center", marginBottom: "16px" }}>
          <span className={styles.stepNumber}>2</span>
          <span>Nạp Ý Tưởng 1-Chạm (Voice, Ảnh Thật Hoặc Vài Dòng)</span>
        </div>

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

        {/* Preset chips */}
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

        {/* Lead Conversion Booster Box */}
        <div className={styles.conversionBooster}>
          <div className={styles.conversionBoosterLeft}>
            <span className={styles.conversionBoosterIcon}>🤖</span>
            <div>
              <div className={styles.conversionBoosterTitle}>
                Tự Động Chốt Lead &amp; Trả Lời Tin Nhắn 24/7 (AI Lead Agent)
              </div>
              <div className={styles.conversionBoosterDesc}>
                Tự động gắn mã ưu đãi và kích hoạt AI tiếp đón khách khi có người bình luận hoặc nhắn tin.
              </div>
            </div>
          </div>
          <label style={{ display: "flex", alignItems: "center", gap: "6px", cursor: "pointer", fontSize: "13px", fontWeight: 700, color: "#15803D" }}>
            <input
              type="checkbox"
              checked={leadConversionEnabled}
              onChange={(e) => setLeadConversionEnabled(e.target.checked)}
              style={{ width: "16px", height: "16px", accentColor: "#16A34A" }}
            />
            <span>Đang kích hoạt</span>
          </label>
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
          {generating ? "⏳ Havi đang sáng tạo nội dung…" : "⚡ Tạo Ngay Bài Viết Đa Kênh & Kịch Bản Video 30s"}
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

      {/* BƯỚC 3: VISUAL MULTI-CHANNEL COMMAND CENTER */}
      <section className={styles.draftsSection} aria-label="Bản nháp đã sẵn sàng">
        <div className={styles.draftsHeader}>
          <div>
            <div className={styles.stepTitle} style={{ marginBottom: "4px" }}>
              <span className={styles.stepNumber}>3</span>
              <span>Visual Multi-Channel Command Center</span>
            </div>
            <h2 className={styles.draftsTitle}>
              {items.length} bản nháp trong kho
            </h2>
            {items.length > 0 ? (
              <p style={{ fontSize: "13px", color: "#64748B", marginTop: "3px" }}>
                🟢 {postGroup.length} Bài Viết &amp; Local SEO (Sẵn sàng) • 🎬 {videoGroup.length} Video Ngắn 9:16 {pendingVideosCount > 0 ? `(${pendingVideosCount} kịch bản chờ clip)` : "(Đã có clip)"}
              </p>
            ) : null}
          </div>
          <div style={{ display: "flex", gap: "8px", alignItems: "center", flexWrap: "wrap" }}>
            <Button
              type="button"
              variant="outline"
              style={{ color: "#DC2626", borderColor: "#FCA5A5", background: "#FEF2F2" }}
              onClick={onDismissAll}
              disabled={!items.length || busyIds.length > 0}
            >
              🗑️ Xoá tất cả
            </Button>
            <Button
              type="button"
              variant="outline"
              style={{ color: "#4F46E5", borderColor: "#C7D2FE", background: "#EEF2FF" }}
              onClick={onSmartScheduleAll}
              disabled={!items.length || busyIds.length > 0}
            >
              📅 Hẹn Giờ Vàng (11h30 &amp; 20h00)
            </Button>
            <Button
              type="button"
              variant="primary"
              onClick={onApproveAll}
              disabled={!items.length || busyIds.length > 0}
            >
              🚀 Duyệt &amp; Đăng Ngay {totalReadyCount < items.length ? `(${totalReadyCount} Kênh Sẵn Sàng)` : "Tất Cả"}
            </Button>
          </div>
        </div>

        {/* Segmented Channel Tabs */}
        {items.length > 0 ? (
          <div className={styles.channelTabs} role="tablist">
            <button
              type="button"
              role="tab"
              aria-selected={activeTab === "all"}
              className={`${styles.channelTabBtn} ${activeTab === "all" ? styles.channelTabBtnActive : ""}`}
              onClick={() => setActiveTab("all")}
            >
              <span>🌐 Tất Cả Kênh</span>
              <span className={styles.channelTabCount}>{items.length}</span>
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={activeTab === "video"}
              className={`${styles.channelTabBtn} ${activeTab === "video" ? styles.channelTabBtnActive : ""}`}
              onClick={() => setActiveTab("video")}
            >
              <span>📱 Video Ngắn Dọc 9:16</span>
              <span className={styles.channelTabCount}>{videoGroup.length}</span>
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={activeTab === "posts"}
              className={`${styles.channelTabBtn} ${activeTab === "posts" ? styles.channelTabBtnActive : ""}`}
              onClick={() => setActiveTab("posts")}
            >
              <span>📰 Bài Viết &amp; Local SEO</span>
              <span className={styles.channelTabCount}>{postGroup.length}</span>
            </button>
          </div>
        ) : null}

        {loading ? (
          <LoadingState title="Đang tải bản nháp…" />
        ) : items.length === 0 ? (
          <EmptyState
            title="Chưa có bản nháp nào chờ duyệt"
            body="Nạp vài tấm ảnh hoặc gõ vài dòng, Havi sẽ viết bài cho chị."
          />
        ) : (
          <div>
            {/* 1. Nhóm Bài Viết Mạng Xã Hội & Local SEO */}
            {(activeTab === "all" || activeTab === "posts") && postGroup.length > 0 ? (
              <div className={styles.groupSection}>
                <div className={styles.groupHeaderPost}>
                  <div className={styles.groupHeaderTitleBox}>
                    <span style={{ fontSize: "20px" }}>📰</span>
                    <span style={{ fontSize: "16px", fontWeight: 800, color: "#1E293B" }}>
                      Nhóm 1: Bài Viết &amp; Local SEO (Facebook Page, Google Maps)
                    </span>
                    <span className={styles.statusPillReady}>🟢 Sẵn Sàng 100%</span>
                    <span className={styles.groupBadgePost}>
                      {postGroup.length} Bài Viết
                    </span>
                  </div>
                  <div className={styles.groupHeaderActions}>
                    <button
                      type="button"
                      className={styles.btnGroupScheduleSubtle}
                      onClick={() => onApprovePostsGroup(false)}
                      disabled={busyIds.length > 0}
                    >
                      📅 Hẹn Giờ Trưa (11:30)
                    </button>
                    <button
                      type="button"
                      className={styles.btnGroupPublishPosts}
                      onClick={() => onApprovePostsGroup(true)}
                      disabled={busyIds.length > 0}
                    >
                      📢 Duyệt Đăng Bài Viết (1 Chạm)
                    </button>
                  </div>
                </div>
                <div className={styles.draftsGrid}>
                  {postGroup.map(renderDraftCard)}
                </div>
              </div>
            ) : null}

            {/* 2. Nhóm Video Ngắn Dọc 9:16 */}
            {(activeTab === "all" || activeTab === "video") && videoGroup.length > 0 ? (
              <div className={styles.groupSection} style={{ background: "#FAF5FF", borderColor: "#E9D5FF" }}>
                <div className={styles.groupHeaderVideo}>
                  <div className={styles.groupHeaderTitleBox}>
                    <span style={{ fontSize: "20px" }}>🎬</span>
                    <span style={{ fontSize: "16px", fontWeight: 800, color: "#581C87" }}>
                      Nhóm 2: Video Ngắn Dọc 9:16 (TikTok, YouTube Shorts, Reels)
                    </span>
                    {readyVideosCount > 0 ? (
                      <span className={styles.statusPillReady}>🟢 {readyVideosCount}/{videoGroup.length} Clip Sẵn Sàng</span>
                    ) : (
                      <span className={styles.statusPillPending}>🎬 Kịch Bản 30s Chờ Quay</span>
                    )}
                    <span className={styles.groupBadgeVideo}>
                      {videoGroup.length} Kênh Video
                    </span>
                  </div>
                  <div className={styles.groupHeaderActions}>
                    {readyVideosCount > 0 ? (
                      <>
                        <button
                          type="button"
                          className={styles.btnGroupScheduleSubtle}
                          onClick={() => onApproveVideosGroup(false)}
                          disabled={busyIds.length > 0}
                        >
                          📅 Hẹn Giờ Tối (20:00)
                        </button>
                        <button
                          type="button"
                          className={styles.btnGroupPublishVideos}
                          onClick={() => onApproveVideosGroup(true)}
                          disabled={busyIds.length > 0}
                        >
                          🎬 Xuất Bản Video ({readyVideosCount} clip)
                        </button>
                      </>
                    ) : (
                      <span style={{ fontSize: "12px", color: "#7E22CE", fontWeight: 600 }}>
                        💡 Nhìn kịch bản quay 15-30s bên dưới rồi tải clip lên nhé
                      </span>
                    )}
                  </div>
                </div>
                <div className={styles.draftsGrid}>
                  {videoGroup.map(renderDraftCard)}
                </div>
              </div>
            ) : null}

            {/* 3. Các kênh khác nếu có */}
            {otherGroup.length > 0 && activeTab === "all" ? (
              <div className={styles.groupSection}>
                <div className={styles.draftsGrid}>
                  {otherGroup.map(renderDraftCard)}
                </div>
              </div>
            ) : null}
          </div>
        )}
      </section>

      {/* Voice Recorder Modal */}
      <VoiceRecorderModal
        isOpen={voiceModalOpen}
        onClose={() => setVoiceModalOpen(false)}
        onInsertNote={handleVoiceInsertNote}
        onDirectGenerate={handleVoiceDirectGenerate}
      />

      {/* Máy Nhắc Chữ 30s Teleprompter Modal */}
      {teleprompterItem ? (
        <TeleprompterModal
          isOpen={Boolean(teleprompterItem)}
          onClose={() => setTeleprompterItem(null)}
          title={`Kịch bản ${channelLabels[teleprompterItem.channel as keyof typeof channelLabels] || teleprompterItem.channel}`}
          hookText={
            teleprompterItem.text.match(/["“]([^"”\n]{6,80})["”]/)?.[1] ||
            teleprompterItem.text.split(/[.\n!?]/)[0]?.replace(/^[•*"-]\s*/, "").trim() ||
            "BÍ QUYẾT TỰ HỌC & LÀM CHỦ CÔNG NGHỆ THỰC CHIẾN"
          }
          cameraAngle={teleprompterItem.media_note || "Cầm điện thoại quay cận cảnh thao tác thực tế tại tiệm."}
          scriptText={teleprompterItem.text}
          onUploadVideo={(file) => handleUploadRealVideoForItem(teleprompterItem.id, file)}
        />
      ) : null}

      {/* Modal thông báo sau khi phát lệnh đăng hoặc lên lịch */}
      {publishedModal ? (
        <div className={styles.modalOverlay} role="dialog" aria-modal="true">
          <div className={styles.publishModalCard}>
            <div className={styles.publishModalHeader}>
              <span className={styles.publishModalIcon}>
                {publishedModal.isInstant ? "🚀" : "📅"}
              </span>
              <h3 className={styles.publishModalTitle}>{publishedModal.title}</h3>
            </div>
            <p className={styles.publishModalBody}>{publishedModal.body}</p>
            <div className={styles.publishModalActions}>
              <Button
                variant="outline"
                onClick={() => setPublishedModal(null)}
              >
                Đóng
              </Button>
              <Button
                variant="primary"
                onClick={() => {
                  setPublishedModal(null);
                  window.location.href = "/app/calendar";
                }}
              >
                Xem Lịch đăng bài 📅
              </Button>
            </div>
          </div>
        </div>
      ) : null}

      <ToastContainer toasts={toasts} onDismiss={removeToast} />
    </>
  );
}
