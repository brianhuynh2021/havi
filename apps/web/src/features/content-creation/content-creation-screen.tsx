"use client";

/* eslint-disable @next/next/no-img-element */

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
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
  listPendingItems,
  mediaTypeOf,
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
import { TeleprompterModal } from "./teleprompter-modal";
import {
  generateKineticShortVideo,
  type VideoStylePreset,
  type VideoVoiceChoice,
} from "./kinetic-video-generator";
import { completeTask } from "@/features/roadmap/roadmap.api";
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

type ContentTrack = "posts" | "video";
type VideoIdeaSource = "own" | "upload";

type VideoPreviewDraft = {
  url: string;
  itemId: string;
  batchIds: string[];
};

const CONTENT_TARGET_CHANNELS: Record<ContentTrack, Channel[]> = {
  posts: ["facebook_page", "google_business"],
  video: ["tiktok", "youtube", "reels"],
};

function isPublishableVideoUrl(url: string | null | undefined): boolean {
  if (!url || url.startsWith("blob:") || url === "/test_tiktok.mp4") return false;
  const normalized = url.toLowerCase().split("?")[0];
  return (
    normalized.endsWith(".mp4") ||
    normalized.endsWith(".mov") ||
    normalized.endsWith(".webm") ||
    normalized.includes("/video")
  );
}

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

function makeNoteChipKey(chipCount: number): string {
  return `note-${chipCount}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
}

function makeJobKey(chips: RawChip[]): string {
  return `job-${Date.now()}-${chips.map((c) => c.key).join("|")}`;
}

export function ContentCreationScreen() {
  const [contentTrack, setContentTrack] = useState<ContentTrack>("posts");
  const [videoIdeaSource, setVideoIdeaSource] = useState<VideoIdeaSource>("own");
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
  const [activeTab, setActiveTab] = useState<"all" | "video" | "posts">("posts");
  const [selectedPlaybook, setSelectedPlaybook] = useState<string | null>(null);
  const [videoPreview, setVideoPreview] = useState<VideoPreviewDraft | null>(null);

  const [publishedModal, setPublishedModal] = useState<{
    title: string;
    body: string;
    isInstant: boolean;
    showTikTokLink?: boolean;
  } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);
  const previewUrlsRef = useRef(new Set<string>());
  const autoGenerateVideoRef = useRef(false);

  const CAMPAIGN_PLAYBOOKS = [
    {
      id: "flash_sale",
      tracks: ["posts", "video"] as ContentTrack[],
      icon: "🚀",
      tag: "Doanh Thu Đột Phá",
      title: "Flash Sale & Kéo Khách Gấp",
      desc: "Thêm CTA hoặc ưu đãi chỉ khi cơ sở đã xác nhận giá trị, thời hạn và số lượng thật.",
      text: "CTA cuối bài: mời khách nhắn tin để nhân viên xác nhận thông tin, lịch trống và ưu đãi thực tế đang áp dụng.",
    },
    {
      id: "viral_trend",
      tracks: ["video"] as ContentTrack[],
      icon: "🔥",
      tag: "Hút Triệu View TikTok",
      title: "Bắt Trend Video Viral",
      desc: "Kịch bản so sánh thực tế bắt trend drama/công nghệ, giữ chân người xem 3s đầu cực đỉnh.",
      text: "Bắt trend câu chuyện đời thực: Trong khi người ta còn loay hoay thì học viên/khách hàng tại cơ sở đã đạt kết quả vượt bậc chỉ sau 3 bước đơn giản.",
    },
    {
      id: "local_seo",
      tracks: ["posts"] as ContentTrack[],
      icon: "📍",
      tag: "Kéo Khách Quanh 5km",
      title: "Thống Trị Google Maps SEO",
      desc: "Bài viết chuẩn SEO địa phương, tối ưu từ khóa ngành nghề để kéo khách vãng lai quanh tiệm.",
      text: "Dịch vụ chuyên nghiệp top đầu khu vực: Uy tín tận tâm, đội ngũ tay nghề cao, nhận tư vấn và báo giá minh bạch ngay trong 15 phút.",
    },
    {
      id: "social_proof",
      tracks: ["posts", "video"] as ContentTrack[],
      icon: "💎",
      tag: "Tăng Tỷ Lệ Chốt Đơn",
      title: "Khoe Kết Quả & Uy Tín",
      desc: "Câu chuyện khách hàng thật, ca cứu máy/dịch vụ xuất sắc tạo niềm tin tuyệt đối khi chốt sale.",
      text: "Cảm nhận thực tế của khách hàng/học viên sau khi trải nghiệm: Giải quyết triệt để vấn đề, an tâm tuyệt đối với chế độ bảo hành và đồng hành lâu dài.",
    },
  ];

  function selectContentTrack(track: ContentTrack) {
    setContentTrack(track);
    setActiveTab(track);
    setSelectedPlaybook(null);
  }

  const loadItems = useCallback(async (keepError = false): Promise<ContentItem[]> => {
    const result = await listPendingItems();
    if (result.ok) {
      setItems(result.data);
      if (!keepError) setError(null);
      setLoading(false);
      return result.data;
    } else {
      setError(result.message);
    }
    setLoading(false);
    return [];
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
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    const topicParam = params.get("topic");
    const trackParam = params.get("track");

    if (trackParam === "video") {
      setContentTrack("video");
      setActiveTab("video");
    } else if (trackParam === "posts") {
      setContentTrack("posts");
      setActiveTab("posts");
    }

    if (topicParam) {
      setNote(topicParam);
      setNoteOpen(true);
      setNotice(`🎯 Đã nạp nhiệm vụ từ Lộ trình: "${topicParam}". Bấm "Để Havi viết cho chị" để tạo nội dung ngay!`);
    }
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
    const isVideo = contentTrack === "video";
    setNotice(
      isVideo
        ? "🎬 Kịch bản đã xong — Havi đang tự dựng bản xem thử 9:16."
        : "⚡ Havi vừa viết xong bài mới! Đã nạp vào danh sách chờ duyệt bên dưới.",
    );
    pushNotification({
      type: "draft_ready",
      title: isVideo
        ? "Havi vừa tạo kịch bản video ngắn đa kênh"
        : "Havi vừa tạo bài viết Fanpage Facebook",
      description: isVideo
        ? "Havi đang dựng một video master để chị xem thử trước khi gửi lên ba kênh."
        : "Bản nháp Fanpage Facebook đã sẵn sàng cho chị duyệt.",
    });
    setToasts((prev) => prev.filter((t) => t.type !== "loading"));
    addToast({
      type: "success",
      title: isVideo ? "Kịch bản xong — đang dựng video AI" : "Havi đã sáng tạo xong bài mới!",
      description: isVideo
        ? "Bản xem thử 1080 × 1920 sẽ tự mở khi dựng xong."
        : "Đã nạp vào danh sách bên dưới — cuộn xuống để duyệt bài ngay.",
    });
    loadItems();
  }, [addToast, contentTrack, loadItems]);

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
      CONTENT_TARGET_CHANNELS[contentTrack],
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
    autoGenerateVideoRef.current = contentTrack === "video";

    addToast({
      type: "loading",
      title: contentTrack === "video" ? "Havi đang viết kịch bản video..." : "Havi đang viết bài cho tiệm...",
      description:
        contentTrack === "video"
          ? "Đang tạo hook 3 giây, lời thoại và góc quay cho TikTok, Reels, Shorts."
          : "Đang hoàn thiện bài viết cho Fanpage Facebook. Bản nháp sẽ sẵn sàng trong giây lát!",
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
      CONTENT_TARGET_CHANNELS[contentTrack],
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
    autoGenerateVideoRef.current = contentTrack === "video";

    addToast({
      type: "loading",
      title: contentTrack === "video" ? "Havi đang viết kịch bản video từ giọng nói..." : "Havi đang viết bài từ giọng nói...",
      description:
        contentTrack === "video"
          ? "Havi đang biến lời thu âm thành hook và kịch bản video ngắn."
          : "Nhân viên AI đang sáng tạo bài viết Fanpage Facebook từ lời thu âm của chị!",
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
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      const taskId = params.get("task_id");
      if (taskId) {
        completeTask(taskId, {
          evidence_text: `[Xác minh hệ thống] Đã duyệt và lên lịch bài viết trên Fanpage / Havi Studio`,
          evidence_type: "link",
        }).catch(() => {});
      }
    }
    setPublishedModal({
      title: scheduledAt
        ? "🚀 Đã phát lệnh đăng bài thành công!"
        : "📅 Đã xếp bài vào Lịch đăng!",
      body: scheduledAt
        ? "Nội dung đang được Havi gửi trực tiếp lên kênh của tiệm. Nhiệm vụ trong Lộ trình hôm nay cũng đã được tự động xác minh hoàn thành!"
        : "Bài viết đã được duyệt và xếp lịch tự động. Nhiệm vụ trong Lộ trình hôm nay đã được tự động xác minh hoàn thành!",
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
    const ids = items
      .filter((item) =>
        contentTrack === "video"
          ? item.channel === "tiktok" || item.channel === "youtube" || item.channel === "reels"
          : item.channel === "facebook_page" || item.channel === "google_business" || item.channel === "zalo_oa",
      )
      .map((item) => item.id);
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
        ? "🚀 Đã phát lệnh đăng Bài Viết lên Fanpage Facebook!"
        : "📅 Đã lên lịch đăng Bài Viết lúc 11:30 trưa!",
      body: `Havi đã ${instant ? "phát lệnh đăng ngay" : "lên lịch tự động"} ${result.data.approved.length} bài viết lên Fanpage Facebook. Nhóm Video vẫn được lưu an toàn để chị quay clip xong đăng sau nhé!`,
      isInstant: instant,
    });
    loadItems();
  }

  async function onApproveVideosGroup(
    instant: boolean,
    videoBatch: ContentItem[] = videoGroup,
  ) {
    const readyVideos = videoBatch.filter((item) => isPublishableVideoUrl(item.media_url));
    if (!readyVideos.length) {
      addToast({
        type: "info",
        title: "Video chưa sẵn sàng để gửi",
        description: "Hãy tạo video AI hoặc tải clip riêng rồi xem lại trước khi duyệt.",
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
        ? "🎬 Video đã được gửi tới ba kênh"
        : "📅 Video đã được xếp lịch lúc 20:00",
      body: instant
        ? "Reels và YouTube Shorts đã nhận lệnh xuất bản. TikTok đã nhận video vào Hộp thư — mở TikTok, kiểm tra lần cuối và bấm Đăng để lên sóng."
        : "Havi sẽ gửi Reels và Shorts theo lịch. Với TikTok, video sẽ vào Hộp thư TikTok để chị mở app và bấm Đăng.",
      isInstant: instant,
      showTikTokLink: true,
    });
    loadItems();
  }

  async function onApproveAll() {
    return contentTrack === "video"
      ? onApproveVideosGroup(true)
      : onApprovePostsGroup(true);
  }

  async function onSmartScheduleAll() {
    return contentTrack === "video"
      ? onApproveVideosGroup(false)
      : onApprovePostsGroup(false);
  }

  const [generatingImageId, setGeneratingImageId] = useState<string | null>(null);
  const [enhancedImageIds, setEnhancedImageIds] = useState<string[]>([]);
  const [lastUploadedPhoto, setLastUploadedPhoto] = useState<string | null>(null);
  const [teleprompterItem, setTeleprompterItem] = useState<ContentItem | null>(null);
  const [shootingModes, setShootingModes] = useState<Record<string, "talking" | "broll">>({});
  const [videoStyles, setVideoStyles] = useState<Record<string, VideoStylePreset>>({});
  const [videoVoices, setVideoVoices] = useState<Record<string, VideoVoiceChoice>>({});
  const [generatingVideoId, setGeneratingVideoId] = useState<string | null>(null);

  async function handleGenerateAiCapCutVideo(
    itemId: string,
    voiceOverride?: VideoVoiceChoice,
  ) {
    const item = items.find((i) => i.id === itemId);
    if (!item) return;
    const batch = videoGroup.filter((video) => video.job_id === item.job_id);

    setGeneratingVideoId(itemId);
    const toastId = addToast({
      type: "loading",
      title: "Đang tạo Video CapCut 9:16...",
      description: "Havi đang lồng chữ nổi 3D, giọng đọc AI và beat nhạc nền synth...",
    });

    try {
      const selectedStyle = videoStyles[itemId] || "capcut_pop";
      const selectedVoice = voiceOverride || videoVoices[itemId] || "vi-VN-HoaiMyNeural";
      const photoChip = chips.find((c) => c.kind === "photo" && c.previewUrl)?.previewUrl;
      const anyImageInBatch = items.find((i) => i.media_url && !i.media_url.endsWith(".mp4") && !i.media_url.startsWith("blob:http") && !i.media_url.includes("video"))?.media_url;
      const effectiveImg: string | undefined = (item.media_url && !item.media_url.endsWith(".mp4") && !item.media_url.includes("video")) ? item.media_url : lastUploadedPhoto || photoChip || anyImageInBatch || undefined;

      const generatedPreviewUrl = await generateKineticShortVideo({
        text: item.text,
        channel: item.channel,
        mediaNote: item.media_note,
        imageUrl: effectiveImg,
        brandName: "Trung Tâm Công Nghệ Nhật Minh",
        hotline: "0984 883 750",
        stylePreset: selectedStyle,
        voiceChoice: selectedVoice,
      });
      if (generatedPreviewUrl === "/test_tiktok.mp4") {
        throw new Error("Trình duyệt không hỗ trợ render video trực tiếp");
      }
      rememberPreviewUrl(generatedPreviewUrl);
      setVideoPreview({
        url: generatedPreviewUrl,
        itemId,
        batchIds: batch.length ? batch.map((video) => video.id) : [itemId],
      });

      removeToast(toastId);
      addToast({
        type: "success",
        icon: "▶️",
        title: "Bản xem thử 1080 × 1920 đã sẵn sàng",
        description: "Xem và nghe thử trước; Havi chỉ lưu vào ba kênh khi chị đồng ý.",
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

  function discardVideoPreview() {
    if (!videoPreview) return;
    forgetPreviewUrl(videoPreview.url);
    setVideoPreview(null);
  }

  async function persistVideoPreview() {
    if (!videoPreview) return;
    setBusyIds(videoPreview.batchIds);
    try {
      const generatedResponse = await fetch(videoPreview.url);
      if (!generatedResponse.ok) throw new Error("Không đọc được video vừa render");
      const generatedBlob = await generatedResponse.blob();
      const generatedType = generatedBlob.type || "video/webm";
      const generatedFile = new File(
        [generatedBlob],
        `havi-video-master-${videoPreview.itemId}.${generatedType.includes("mp4") ? "mp4" : "webm"}`,
        { type: generatedType },
      );
      const persisted = await uploadMedia(generatedFile);
      if (!persisted.ok) throw new Error(persisted.message);
      const updateResults = await Promise.all(
        videoPreview.batchIds.map((targetId) => updateItemMedia(targetId, persisted.data.url)),
      );
      if (updateResults.some((result) => !result.ok)) {
        throw new Error("Video đã lưu nhưng chưa đồng bộ được vào bản nháp");
      }
      setItems((prev) =>
        prev.map((item) =>
          videoPreview.batchIds.includes(item.id)
            ? {
                ...item,
                media_url: persisted.data.url,
                media_note: "🎬 Video master 9:16 do Havi dựng — đã được chị duyệt",
              }
            : item,
        ),
      );
      discardVideoPreview();
      addToast({
        type: "success",
        icon: "✨",
        title: "Đã dùng video này cho ba kênh",
        description: "Một video master đã được gắn cho TikTok, Reels và YouTube Shorts.",
      });
    } catch (error) {
      addToast({
        type: "error",
        title: "Chưa lưu được video",
        description: error instanceof Error ? error.message : "Vui lòng thử lại.",
      });
    } finally {
      setBusyIds([]);
    }
  }

  async function regenerateVideoWithOtherVoice() {
    if (!videoPreview) return;
    const itemId = videoPreview.itemId;
    const nextVoice: VideoVoiceChoice =
      (videoVoices[itemId] || "vi-VN-HoaiMyNeural") === "vi-VN-HoaiMyNeural"
        ? "vi-VN-NamMinhNeural"
        : "vi-VN-HoaiMyNeural";
    setVideoVoices((prev) => ({ ...prev, [itemId]: nextVoice }));
    discardVideoPreview();
    await handleGenerateAiCapCutVideo(itemId, nextVoice);
  }

  async function handleUploadRealVideoForItem(itemId: string, file: File) {
    const toastId = addToast({
      type: "loading",
      title: "Đang gắn video thật...",
      description: `Đang tải clip "${file.name}" lên hệ thống Havi.`,
    });

    try {
      const uploadRes = await uploadMedia(file);
      removeToast(toastId);
      if (uploadRes.ok) {
        const sourceItem = videoGroup.find((video) => video.id === itemId);
        const targetIds = sourceItem
          ? videoGroup.filter((video) => video.job_id === sourceItem.job_id).map((video) => video.id)
          : [itemId];
        const updateResults = await Promise.all(
          targetIds.map((targetId) => updateItemMedia(targetId, uploadRes.data.url)),
        );
        if (updateResults.some((result) => !result.ok)) {
          throw new Error("Clip đã tải lên nhưng chưa đồng bộ được vào bản nháp");
        }

        setItems((prev) =>
          prev.map((i) =>
            targetIds.includes(i.id)
              ? {
                  ...i,
                  media_url: uploadRes.data.url,
                  media_note: `🎬 Video thật của tiệm (${file.name}) · ${describeClip(uploadRes.data)}`,
                }
              : i,
          ),
        );

        addToast({
          type: "success",
          icon: "🎬",
          title: "Đã gắn & đồng bộ video thật!",
          description: sourceItem && targetIds.length > 1
            ? `Video thật đã được dùng làm một video master cho ${targetIds.length} kênh.`
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

  async function handleUploadMediaForItem(itemId: string, file: File) {
    if (file.type.startsWith("image/")) {
      const uploadRes = await uploadMedia(file);
      if (!uploadRes.ok) {
        addToast({ type: "error", title: "Không thể tải ảnh", description: uploadRes.message });
        return;
      }

      const sourceItem = videoGroup.find((video) => video.id === itemId);
      const targetIds = sourceItem
        ? videoGroup.filter((video) => video.job_id === sourceItem.job_id).map((video) => video.id)
        : [itemId];
      const updateResults = await Promise.all(
        targetIds.map((targetId) => updateItemMedia(targetId, uploadRes.data.url)),
      );
      if (updateResults.some((result) => !result.ok)) {
        addToast({
          type: "error",
          title: "Ảnh đã tải nhưng chưa đồng bộ",
          description: "Vui lòng thử lại.",
        });
        return;
      }

      setLastUploadedPhoto(uploadRes.data.url);
      setItems((prev) => prev.map((i) =>
        targetIds.includes(i.id)
          ? {
              ...i,
              media_url: uploadRes.data.url,
              media_note: `📸 Ảnh chụp tiệm thật (${file.name})`,
            }
          : i,
      ));

      addToast({
        type: "success",
        icon: "🖼️",
        title: "Đã lưu ảnh thật của tiệm!",
        description: "Bấm nút '🪄 Tạo Video CapCut (9:16)' để dựng video từ chính ảnh này.",
      });
      return;
    }

    return handleUploadRealVideoForItem(itemId, file);
  }

  async function handleAiGenerateImage(itemId: string) {
    setGeneratingImageId(itemId);
    addToast({
      type: "loading",
      title: "Đang tìm ảnh minh họa phù hợp...",
      description: "Hệ thống đang lựa chọn hình ảnh minh họa chất lượng cao phù hợp với nội dung bài viết.",
    });
    const res = await generateItemImage(itemId, "3d_studio");
    setGeneratingImageId(null);
    if (res.ok) {
      setItems((prev) =>
        prev.map((i) =>
          i.id === itemId
            ? { ...i, media_url: res.data.media_url, media_note: "🖼️ Ảnh minh họa gợi ý" }
            : i,
        ),
      );
      addToast({
        type: "success",
        icon: "🖼️",
        title: "Đã chọn ảnh minh họa thành công!",
        description: "Ảnh minh họa gợi ý đã được gắn trực tiếp vào bài viết.",
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

  const videoBatches = Object.values(
    videoGroup.reduce<Record<string, ContentItem[]>>((groups, item) => {
      const key = item.job_id || item.id;
      groups[key] = [...(groups[key] || []), item];
      return groups;
    }, {}),
  );

  const readyVideosCount = videoBatches.filter((batch) =>
    batch.some((item) => isPublishableVideoUrl(item.media_url)),
  ).length;

  const pendingVideosCount = videoBatches.length - readyVideosCount;
  const scopedItemCount = contentTrack === "video" ? videoGroup.length : postGroup.length;
  const activeItemsCount =
    activeTab === "all"
      ? items.length
      : activeTab === "video"
        ? videoGroup.length
        : postGroup.length;

  useEffect(() => {
    if (
      !autoGenerateVideoRef.current ||
      contentTrack !== "video" ||
      !videoBatches.length ||
      generatingVideoId ||
      videoPreview
    ) {
      return;
    }
    const batch = videoBatches.find(
      (candidate) => !candidate.some((item) => isPublishableVideoUrl(item.media_url)),
    );
    if (!batch?.[0]) return;
    autoGenerateVideoRef.current = false;
    const timer = window.setTimeout(() => {
      void handleGenerateAiCapCutVideo(batch[0].id);
    }, 0);
    // Handler intentionally runs only for the freshly-created job signalled by
    // autoGenerateVideoRef; existing drafts never render automatically on load.
    return () => window.clearTimeout(timer);
    // `items` is the source of truth for videoBatches; the handler is gated by
    // autoGenerateVideoRef so existing drafts never render on page load.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [contentTrack, items, generatingVideoId, videoPreview]);

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
                  const hasRealVideo = isPublishableVideoUrl(item.media_url);

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
                              &quot;{hookDisplay}&quot;
                            </div>
                          </div>

                          <div className={styles.scriptSection}>
                            <div className={styles.scriptSectionTitle}>
                              💬 Lời Thoại Gợi Ý (Đọc ngắn gọn 20s)
                            </div>
                            <div className={styles.scriptSectionContent}>
                              &quot;{item.text.length > 180 ? item.text.slice(0, 175) + "..." : item.text}&quot;
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

                      {/* Tùy chọn Phong cách Video & Giọng đọc AI */}
                      <div className={styles.stylePresetSection}>
                        <div className={styles.stylePresetLabel}>
                          <span>🎨 Phong Cách Chữ Nổi &amp; Nhạc Nền:</span>
                        </div>
                        <div className={styles.presetChipsList}>
                          <button
                            type="button"
                            className={`${styles.presetChip} ${(videoStyles[item.id] || "capcut_pop") === "capcut_pop" ? styles.presetChipActive : ""}`}
                            onClick={() => setVideoStyles((prev) => ({ ...prev, [item.id]: "capcut_pop" }))}
                          >
                            🌟 CapCut Kinetic (Chữ Vàng 3D)
                          </button>
                          <button
                            type="button"
                            className={`${styles.presetChip} ${videoStyles[item.id] === "authentic_story" ? styles.presetChipActive : ""}`}
                            onClick={() => setVideoStyles((prev) => ({ ...prev, [item.id]: "authentic_story" }))}
                          >
                            🎬 Tâm Sự Chân Thật (Chữ Trắng)
                          </button>
                          <button
                            type="button"
                            className={`${styles.presetChip} ${videoStyles[item.id] === "flash_sale" ? styles.presetChipActive : ""}`}
                            onClick={() => setVideoStyles((prev) => ({ ...prev, [item.id]: "flash_sale" }))}
                          >
                            🔥 Ưu Đãi Giờ Vàng (Chữ Đỏ/Cam)
                          </button>
                        </div>

                        <div className={styles.stylePresetLabel}>
                          <span>🎙️ Giọng Đọc AI Tiếng Việt (0 VNĐ):</span>
                        </div>
                        <div className={styles.voiceChipsList}>
                          <button
                            type="button"
                            className={`${styles.voiceChip} ${(videoVoices[item.id] || "vi-VN-HoaiMyNeural") === "vi-VN-HoaiMyNeural" ? styles.voiceChipActive : ""}`}
                            onClick={() => setVideoVoices((prev) => ({ ...prev, [item.id]: "vi-VN-HoaiMyNeural" }))}
                          >
                            👩 Hoài My (Nữ - Truyền Cảm)
                          </button>
                          <button
                            type="button"
                            className={`${styles.voiceChip} ${videoVoices[item.id] === "vi-VN-NamMinhNeural" ? styles.voiceChipActive : ""}`}
                            onClick={() => setVideoVoices((prev) => ({ ...prev, [item.id]: "vi-VN-NamMinhNeural" }))}
                          >
                            👨 Nam Minh (Nam - Ấm Áp/Chững Chạc)
                          </button>
                        </div>
                      </div>

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
                          accept="image/*,video/mp4,video/quicktime,video/webm"
                          style={{ display: "none" }}
                          onChange={(e) => {
                            const f = e.target.files?.[0];
                            if (f) handleUploadMediaForItem(item.id, f);
                          }}
                        />
                        <label
                          htmlFor={`upload-real-video-${item.id}`}
                          className={styles.uploadRealVideoBtn}
                        >
                          📤 {currentMode === "broll" ? "Tải Ảnh / Clip 10s Tiệm Lên" : "Tải Ảnh / Clip Tiệm Lên"}
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

  const renderVideoMasterCard = (batch: ContentItem[]) => {
    const primary = batch.find((item) => item.channel === "tiktok") || batch[0];
    if (!primary) return null;
    const readyItem = batch.find((item) => isPublishableVideoUrl(item.media_url));
    const readyUrl = readyItem?.media_url;
    const busy = batch.some((item) => busyIds.includes(item.id));
    const selectedStyle = videoStyles[primary.id] || "capcut_pop";
    const selectedVoice = videoVoices[primary.id] || "vi-VN-HoaiMyNeural";

    return (
      <article key={primary.job_id || primary.id} className={styles.videoMasterCard}>
        <div className={styles.videoMasterHeader}>
          <div>
            <span className={styles.videoMasterEyebrow}>MỘT VIDEO MASTER · 9:16</span>
            <h3>Video ngắn sẵn sàng cho ba kênh</h3>
            <p>Một lần dựng, một lần duyệt — Havi tự chuẩn bị phiên bản phân phối phù hợp.</p>
          </div>
          <div className={styles.videoDestinationBadges} aria-label="Kênh nhận video">
            <span>🎵 TikTok</span>
            <span>🎬 Reels</span>
            <span>▶️ Shorts</span>
          </div>
        </div>

        <div className={styles.videoMasterBody}>
          <div className={styles.videoMasterPreview}>
            {readyUrl ? (
              <>
                <span className={styles.videoReadyBadge}>✓ Video đã sẵn sàng — xem thử</span>
                <video src={readyUrl} controls playsInline aria-label="Xem thử video master 9:16" />
              </>
            ) : (
              <div className={styles.videoPendingPreview}>
                <span>✨</span>
                <strong>Havi sẽ tự dựng video cho chị</strong>
                <p>Ảnh, hook, giọng đọc, subtitle và nhạc nền sẽ được ghép thành một bản xem thử 1080 × 1920.</p>
              </div>
            )}
          </div>

          <div className={styles.videoMasterControls}>
            <div className={styles.videoMasterStatus}>
              <strong>{readyUrl ? "Video hoàn chỉnh đã sẵn sàng" : "Kịch bản đã sẵn sàng để AI dựng"}</strong>
              <p>{primary.text}</p>
            </div>

            <div className={styles.stylePresetLabel}>Phong cách video</div>
            <div className={styles.presetChipsList}>
              {([
                ["capcut_pop", "🌟 CapCut Kinetic"],
                ["authentic_story", "🎬 Chân thật"],
                ["flash_sale", "🔥 Flash Sale"],
              ] as const).map(([value, label]) => (
                <button
                  key={value}
                  type="button"
                  className={`${styles.presetChip} ${selectedStyle === value ? styles.presetChipActive : ""}`}
                  onClick={() => setVideoStyles((prev) => ({ ...prev, [primary.id]: value }))}
                >
                  {label}
                </button>
              ))}
            </div>

            <div className={styles.stylePresetLabel}>Giọng đọc AI</div>
            <div className={styles.voiceChipsList}>
              <button
                type="button"
                className={`${styles.voiceChip} ${selectedVoice === "vi-VN-HoaiMyNeural" ? styles.voiceChipActive : ""}`}
                onClick={() => setVideoVoices((prev) => ({ ...prev, [primary.id]: "vi-VN-HoaiMyNeural" }))}
              >
                👩 Hoài My
              </button>
              <button
                type="button"
                className={`${styles.voiceChip} ${selectedVoice === "vi-VN-NamMinhNeural" ? styles.voiceChipActive : ""}`}
                onClick={() => setVideoVoices((prev) => ({ ...prev, [primary.id]: "vi-VN-NamMinhNeural" }))}
              >
                👨 Nam Minh
              </button>
            </div>

            <button
              type="button"
              className={styles.videoPrimaryAction}
              disabled={generatingVideoId === primary.id}
              onClick={() => handleGenerateAiCapCutVideo(primary.id)}
            >
              {generatingVideoId === primary.id
                ? "⏳ Havi đang dựng bản xem thử…"
                : readyUrl
                  ? "🪄 Làm lại video AI"
                  : "🪄 Tạo video AI — xem thử trước"}
            </button>

            <input
              type="file"
              id={`upload-video-master-${primary.id}`}
              accept="video/mp4,video/quicktime,video/webm"
              hidden
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) handleUploadRealVideoForItem(primary.id, file);
              }}
            />
            <label htmlFor={`upload-video-master-${primary.id}`} className={styles.videoOwnClipLink}>
              Muốn dùng clip tự quay? Tải clip của chị lên
            </label>

            <details className={styles.channelCaptions}>
              <summary>Xem nội dung riêng cho từng kênh</summary>
              {batch.map((item) => (
                <div key={item.id}>
                  <strong>{channelLabels[item.channel as keyof typeof channelLabels] ?? item.channel}</strong>
                  <p>{item.text}</p>
                </div>
              ))}
            </details>
          </div>
        </div>

        <div className={styles.videoDeliveryTruth}>
          <span>🎵 TikTok: gửi vào Hộp thư TikTok, chị mở app và bấm Đăng.</span>
          <span>🎬 Reels · ▶️ Shorts: Havi xuất bản trực tiếp khi kênh đã kết nối.</span>
        </div>

        <div className={styles.videoMasterActions}>
          {!readyUrl ? (
            <p>Video chưa có file hoàn chỉnh nên Havi chưa cho phép duyệt hoặc đăng.</p>
          ) : (
            <>
              <Button variant="outline" disabled={busy} onClick={() => onApproveVideosGroup(false, batch)}>
                📅 Hẹn giờ 20:00
              </Button>
              <Button variant="primary" disabled={busy} onClick={() => onApproveVideosGroup(true, batch)}>
                Gửi video tới 3 kênh
              </Button>
            </>
          )}
        </div>
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

      {/* BƯỚC 1: CHỌN RÕ LOẠI NỘI DUNG */}
      <section className={styles.contentTrackSection} aria-labelledby="content-track-title">
        <div className={styles.stepTitle}>
          <span className={styles.stepNumber}>1</span>
          <span id="content-track-title">Chị muốn tạo gì hôm nay?</span>
        </div>
        <div className={styles.contentTrackGrid} role="tablist" aria-label="Loại nội dung muốn tạo">
          <button
            type="button"
            role="tab"
            aria-selected={contentTrack === "posts"}
            className={`${styles.contentTrackCard} ${contentTrack === "posts" ? styles.contentTrackCardActive : ""}`}
            onClick={() => selectContentTrack("posts")}
          >
            <span className={styles.contentTrackIcon}>📰</span>
            <span>
              <strong>Bài viết Fanpage Facebook</strong>
              <small>AI viết bài Facebook chuẩn thu hút, chị duyệt rồi đăng hoặc hẹn giờ.</small>
            </span>
            <span className={styles.contentTrackCheck}>{contentTrack === "posts" ? "✓ Đang chọn" : "Chọn"}</span>
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={contentTrack === "video"}
            className={`${styles.contentTrackCard} ${contentTrack === "video" ? styles.contentTrackCardActive : ""}`}
            onClick={() => selectContentTrack("video")}
          >
            <span className={styles.contentTrackIcon}>🎬</span>
            <span>
              <strong>Video ngắn TikTok, Reels, Shorts</strong>
              <small>AI tự tạo một video 9:16 hoàn chỉnh; chị xem thử, duyệt rồi gửi lên ba kênh.</small>
            </span>
            <span className={styles.contentTrackCheck}>{contentTrack === "video" ? "✓ Đang chọn" : "Chọn"}</span>
          </button>
        </div>

        {contentTrack === "video" ? (
          <div className={styles.videoSourcePanel} aria-label="Nguồn ý tưởng video">
            <div className={styles.videoSourceHeader}>
              <strong>Ý tưởng video đến từ đâu?</strong>
              <span>Chọn một cách để Havi dẫn đúng flow, không cần quyết định mọi thứ cùng lúc.</span>
            </div>
            <div className={styles.videoSourceGrid}>
              <Link className={`${styles.videoSourceCard} ${styles.videoSourceTrend}`} href="/app/video-studio">
                <span>🔥</span>
                <strong>AI Studio quét trend</strong>
                <small>Tìm chủ đề đang nóng và lấy hook phù hợp với tiệm.</small>
                <b>Mở AI Trend Studio →</b>
              </Link>
              <button
                type="button"
                className={`${styles.videoSourceCard} ${videoIdeaSource === "own" ? styles.videoSourceCardActive : ""}`}
                onClick={() => setVideoIdeaSource("own")}
              >
                <span>✍️</span>
                <strong>Ý tưởng của tôi</strong>
                <small>Nói hoặc gõ vài dòng, Havi biến thành kịch bản video.</small>
                <b>{videoIdeaSource === "own" ? "✓ Đang chọn" : "Chọn cách này"}</b>
              </button>
              <button
                type="button"
                className={`${styles.videoSourceCard} ${videoIdeaSource === "upload" ? styles.videoSourceCardActive : ""}`}
                onClick={() => {
                  setVideoIdeaSource("upload");
                  fileInputRef.current?.click();
                }}
              >
                <span>📹</span>
                <strong>Tôi đã có clip</strong>
                <small>Tải clip lên để Havi viết hook và chuẩn bị bản đăng đa kênh.</small>
                <b>{videoIdeaSource === "upload" ? "✓ Đang chọn" : "Chọn clip"}</b>
              </button>
            </div>
          </div>
        ) : null}
      </section>

      {/* BƯỚC 2: CHỌN CHIẾN DỊCH TĂNG TRƯỞNG */}
      <section className={styles.playbookSection} aria-label="Chọn chiến dịch">
        <div className={styles.stepTitle}>
          <span className={styles.stepNumber}>2</span>
          <span>Chọn Mục Tiêu {contentTrack === "video" ? "Video" : "Bài Viết"}</span>
        </div>
        <div className={styles.playbookGrid}>
          {CAMPAIGN_PLAYBOOKS.filter((playbook) => playbook.tracks.includes(contentTrack)).map((playbook) => {
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

      {/* BƯỚC 3: NẠP Ý TƯỞNG NHANH */}
      <section className={styles.dropZone} aria-label="Nạp liệu mới">
        <div className={styles.stepTitle} style={{ justifyContent: "center", marginBottom: "16px" }}>
          <span className={styles.stepNumber}>3</span>
          <span>{contentTrack === "video" ? "Đưa Liệu Cho Video" : "Nạp Ý Tưởng 1-Chạm"}</span>
        </div>

        <p className={styles.dropTitle}>
          {contentTrack === "video"
            ? "Thêm ảnh, ghi âm hoặc gõ ý tưởng — Havi tự dựng video hoàn chỉnh cho TikTok, Reels và Shorts"
            : "Chụp ảnh hoặc gõ vài dòng — Havi sẽ viết bài đăng Fanpage Facebook"}
        </p>
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
            {contentTrack === "video" ? "📹 Quay clip / Chụp ảnh" : "📸 Chụp ảnh thật"}
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
            {uploading
              ? "Đang tải lên…"
              : contentTrack === "video"
                ? "+ Tải clip / ảnh có sẵn"
                : "+ Chọn ảnh từ thư viện"}
          </Button>
          <Button variant="outline" onClick={() => setNoteOpen((v) => !v)}>
            ✍️ Gõ ghi chú nhanh
          </Button>
        </div>

        {noteOpen ? (
          <div className={styles.noteBox}>
            <label className={styles.noteLabel} htmlFor="raw-note">
              {contentTrack === "video" ? "Video này muốn nói điều gì?" : "Chị muốn Havi kể chuyện gì?"}
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

        {/* Offer Sellability Diagnostic (Bộ Chẩn Đoán Khả Năng Bán & Cảnh Báo Chuyển Đổi) */}
        {(() => {
          const combinedText = [note, ...chips.map((c) => c.label)].join(" ");
          const hasMedia = chips.some((c) => c.kind === "photo") || uploads.some((u) => u.status === "complete");
          if (!combinedText.trim() && !hasMedia) return null;

          const content = combinedText.toLowerCase();
          const hasOffer = /(ưu đãi|giảm|tặng|học thử|miễn phí|voucher|khóa học|combo|quà|suất|chỉ còn|%|đóng học phí|bảo dưỡng|sửa chữa)/i.test(content);
          const hasUrgency = /(tuần này|hôm nay|chỉ còn|duy nhất|hạn chót|ngày|suất|sớm nhất|hạn|48h|24h)/i.test(content);
          const hasPrice = /(\d+\s*(k|tr|đ|đồng|triệu|nghìn|vnđ|%)|miễn phí|0đ)/i.test(content);
          const hasCta = /(inbox|nhắn|nhắn tin|đặt lịch|gọi|liên hệ|hotline|sđt|đăng ký|ghé|bình luận|comment)/i.test(content);
          const hasProof = hasMedia;

          let score = 0;
          if (hasOffer) score += 25;
          if (hasProof) score += 25;
          if (hasUrgency) score += 20;
          if (hasPrice) score += 15;
          if (hasCta) score += 15;

          const scoreClass = score >= 80 ? styles.scoreHigh : score >= 50 ? styles.scoreMedium : styles.scoreLow;
          const adviceClass = score >= 80 ? styles.sellabilityAdvicePass : styles.sellabilityAdvice;
          const adviceText = score >= 80
            ? "✨ Bản nháp có đủ các thành phần CTA đang được kiểm tra; điểm này không dự đoán số khách hay doanh thu."
            : score >= 50
              ? "💡 Có thể bổ sung bằng chứng thật hoặc CTA rõ hơn. Chỉ dùng giới hạn số suất nếu đó là thông tin có thật."
              : "⚠️ Bản nháp đang thiếu đề nghị hoặc lời kêu gọi hành động rõ ràng; hãy kiểm tra lại trước khi duyệt.";

          const criteria = [
            { id: "offer", label: "🎯 Đề nghị / Ưu đãi rõ ràng", pass: hasOffer },
            { id: "proof", label: "📸 Bằng chứng ảnh/clip thật", pass: hasProof },
            { id: "urgency", label: "⏱️ Tính cấp bách / Giới hạn", pass: hasUrgency },
            { id: "price", label: "💰 Định khung giá / Giá trị", pass: hasPrice },
            { id: "cta", label: "🚀 Lời kêu gọi chốt lịch (CTA)", pass: hasCta },
          ];

          return (
            <div className={styles.sellabilityCard} aria-label="Chẩn đoán khả năng bán">
              <div className={styles.sellabilityHeader}>
                <div className={styles.sellabilityTitleWrapper}>
                  <span>🔍</span>
                  <h3 className={styles.sellabilityTitle}>Chẩn Đoán Khả Năng Bán Của Chiến Dịch</h3>
                </div>
                <div className={`${styles.sellabilityScoreBadge} ${scoreClass}`}>
                  ⚡ Điểm Chuyển Đổi: {score}/100
                </div>
              </div>

              <div className={styles.criteriaGrid}>
                {criteria.map((c) => (
                  <div
                    key={c.id}
                    className={`${styles.criterionItem} ${c.pass ? styles.criterionItemPass : ""}`}
                  >
                    <span>{c.pass ? "✓" : "○"}</span>
                    <span>{c.label}</span>
                  </div>
                ))}
              </div>

              <p className={adviceClass}>
                {adviceText}
              </p>
            </div>
          );
        })()}

        {/* Preset chips */}
        <div className={styles.presetSection}>
          <div className={styles.presetHeader}>
            <span>⚡</span>
            <span>{contentTrack === "video" ? "Gợi ý chủ đề video 1-chạm:" : "Ý tưởng bài viết 1-chạm:"}</span>
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
                text: "Khai giảng khóa học Kỹ thuật số thực hành: mô tả rõ nội dung, thời lượng và hình thức hỗ trợ sau khóa học theo chính sách thật của cơ sở.",
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

        {/* Lead conversion belongs to the post flow; showing it while scripting a
            video adds an unrelated decision before the user has even made a clip. */}
        {contentTrack === "posts" ? (
          <div className={styles.conversionBooster}>
            <div className={styles.conversionBoosterLeft}>
              <span className={styles.conversionBoosterIcon}>🤖</span>
              <div>
                <div className={styles.conversionBoosterTitle}>
                  Gợi Ý Chăm Sóc Lead &amp; Trả Lời FAQ Đã Duyệt (AI Lead Agent Beta)
                </div>
                <div className={styles.conversionBoosterDesc}>
                  Gợi ý CTA và phản hồi theo FAQ đã được chủ cơ sở phê duyệt trước.
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

      {contentTrack === "posts" ? (
        <section className={styles.modeToggle} aria-label="Chế độ đăng bài">
          <div className={styles.modeButtons} role="group">
            <button
              type="button"
              className={`${styles.modeButton} ${publishMode === "review_first" ? styles.modeButtonActive : ""}`}
              aria-pressed={publishMode === "review_first"}
              onClick={() => setPublishMode("review_first")}
            >
              Duyệt trước khi đăng
            </button>
            <button
              type="button"
              className={`${styles.modeButton} ${publishMode === "full_auto" ? styles.modeButtonActive : ""}`}
              aria-pressed={publishMode === "full_auto"}
              onClick={() => setPublishMode("full_auto")}
            >
              Tự động đăng
            </button>
          </div>
          {publishMode === "full_auto" ? (
            <p className={styles.modeWarning}>
              Chế độ này đang khoá trong bản pilot — mọi bài vẫn sẽ chờ chị duyệt trước khi lên mạng.
            </p>
          ) : (
            <p className={styles.modeHint}>
              Mặc định của Havi — không có bài nào lên mạng khi chị chưa duyệt.
            </p>
          )}
        </section>
      ) : (
        <section className={styles.videoReviewPromise} aria-label="Quy trình duyệt video">
          <span>🛡️</span>
          <div>
            <strong>Video luôn chờ chị xem lại trước khi đăng</strong>
            <p>Havi tự dựng một video 1080 × 1920 để chị xem và nghe thử. Chỉ khi chị chọn dùng bản đó, video mới được lưu và mở nút gửi lên ba kênh.</p>
          </div>
        </section>
      )}

      <div className={styles.generateRow}>
        <Button
          variant="primary"
          className={styles.heroGenerateBtn}
          onClick={generate}
          disabled={(!chips.length && !note.trim()) || uploading || generating}
        >
          {generating
            ? "⏳ Havi đang sáng tạo nội dung…"
            : contentTrack === "video"
              ? "🪄 AI Tạo Video 9:16 Cho Tôi"
              : "⚡ Tạo Bài Viết Facebook Fanpage"}
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

      {/* BƯỚC 4: DUYỆT ĐẦU RA ĐÚNG LOẠI NỘI DUNG ĐÃ CHỌN */}
      <section className={styles.draftsSection} aria-label="Bản nháp đã sẵn sàng">
        <div className={styles.draftsHeader}>
          <div>
            <div className={styles.stepTitle} style={{ marginBottom: "4px" }}>
              <span className={styles.stepNumber}>4</span>
              <span>Hoàn thiện &amp; duyệt nội dung</span>
            </div>
            <h2 className={styles.draftsTitle}>
              {contentTrack === "video"
                ? `${videoBatches.length} video master đang hoàn thiện`
                : `${postGroup.length} bản nháp bài viết`}
            </h2>
            {scopedItemCount > 0 ? (
              <p style={{ fontSize: "13px", color: "#64748B", marginTop: "3px" }}>
                {contentTrack === "video"
                  ? readyVideosCount > 0
                    ? `🟢 ${readyVideosCount} video AI đã dựng sẵn — xem thử và duyệt`
                    : `✨ ${pendingVideosCount} kịch bản sẵn sàng — Havi sẽ tự dựng video`
                  : `🟢 ${postGroup.length} bài viết Facebook & Local SEO sẵn sàng`}
              </p>
            ) : null}
          </div>
          <div style={{ display: "flex", gap: "8px", alignItems: "center", flexWrap: "wrap" }}>
            <Button
              type="button"
              variant="outline"
              style={{ color: "#DC2626", borderColor: "#FCA5A5", background: "#FEF2F2" }}
              onClick={onDismissAll}
              disabled={scopedItemCount === 0 || busyIds.length > 0}
            >
              🗑️ Xoá tất cả
            </Button>
            <Button
              type="button"
              variant="outline"
              style={{ color: "#4F46E5", borderColor: "#C7D2FE", background: "#EEF2FF" }}
              onClick={onSmartScheduleAll}
              disabled={(contentTrack === "video" ? readyVideosCount === 0 : postGroup.length === 0) || busyIds.length > 0}
            >
              {contentTrack === "video" ? "📅 Hẹn video lúc 20:00" : "📅 Hẹn bài lúc 11:30"}
            </Button>
            <Button
              type="button"
              variant="primary"
              onClick={onApproveAll}
              disabled={(contentTrack === "video" ? readyVideosCount === 0 : postGroup.length === 0) || busyIds.length > 0}
            >
              {contentTrack === "video"
                ? `🎬 Gửi ${readyVideosCount} video sẵn sàng tới 3 kênh`
                : `🚀 Đăng ${postGroup.length} bài viết sẵn sàng`}
            </Button>
          </div>
        </div>

        {/* Segmented Channel Tabs */}
        {items.length > 0 ? (
          <div className={styles.channelTabs} role="tablist" aria-label="Lọc bản nháp theo loại nội dung">
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
        ) : activeItemsCount === 0 ? (
          <EmptyState
            title={
              contentTrack === "video"
                ? "Chưa có kịch bản video nào chờ chị hoàn thiện"
                : "Chưa có bản nháp nào chờ duyệt"
            }
            body={
              contentTrack === "video"
                ? "Chọn trend hoặc gõ một ý tưởng; Havi sẽ tạo hook, dựng video AI và mở bản xem thử trước khi gửi lên ba kênh."
                : "Nạp vài tấm ảnh hoặc gõ vài dòng, Havi sẽ viết bài cho chị."
            }
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
                      Nhóm 1: Bài Viết Fanpage Facebook
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
                      Video Ngắn 9:16 → TikTok, Reels và YouTube Shorts
                    </span>
                    {readyVideosCount > 0 ? (
                      <span className={styles.statusPillReady}>🟢 {readyVideosCount}/{videoBatches.length} Video Sẵn Sàng</span>
                    ) : (
                      <span className={styles.statusPillPending}>✨ AI Sẵn Sàng Dựng Video</span>
                    )}
                    <span className={styles.groupBadgeVideo}>
                      {videoBatches.length} Video Master
                    </span>
                  </div>
                  <span style={{ fontSize: "12px", color: "#7E22CE", fontWeight: 600 }}>
                    💡 Havi dựng mặc định; clip tự quay là lựa chọn phụ
                  </span>
                </div>
                <div className={styles.videoMasterList}>
                  {videoBatches.map(renderVideoMasterCard)}
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

      {videoPreview ? (
        <div className={styles.modalOverlay} role="dialog" aria-modal="true" aria-label="Xem thử video AI">
          <div className={styles.videoPreviewModalCard}>
            <div className={styles.videoPreviewModalHeader}>
              <div>
                <span>BẢN XEM THỬ · 1080 × 1920</span>
                <h3>Xem và nghe trước khi dùng video này</h3>
              </div>
              <button type="button" onClick={discardVideoPreview} aria-label="Đóng bản xem thử">×</button>
            </div>
            <video src={videoPreview.url} controls autoPlay playsInline aria-label="Video AI đang xem thử" />
            <p>Video chưa được lưu hoặc gửi đi. Chị có thể đổi giọng, làm lại hoặc dùng bản này cho cả ba kênh.</p>
            <div className={styles.videoPreviewModalActions}>
              <Button variant="outline" onClick={discardVideoPreview}>Bỏ bản này</Button>
              <Button variant="outline" onClick={regenerateVideoWithOtherVoice}>
                🎙️ Làm lại giọng khác
              </Button>
              <Button variant="primary" onClick={persistVideoPreview} disabled={busyIds.length > 0}>
                {busyIds.length > 0 ? "Đang lưu…" : "✓ Dùng video này cho 3 kênh"}
              </Button>
            </div>
          </div>
        </div>
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
              {publishedModal.showTikTokLink ? (
                <Button
                  variant="outline"
                  onClick={() => window.open("https://www.tiktok.com/", "_blank", "noopener,noreferrer")}
                >
                  Mở TikTok để bấm Đăng ↗
                </Button>
              ) : null}
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
