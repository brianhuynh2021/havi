"use client";

/**
 * Nhánh Video của luồng Đăng bài: tải clip lên → duyệt → Havi đăng lên Reels.
 *
 * Không có nút cắt, nút ghép, nút thêm phụ đề — và đó là chủ ý sản phẩm. Chủ
 * tiệm đã có CapCut và dùng quen hơn bất cứ thứ gì Havi dựng được trong trình
 * duyệt. Thứ họ thiếu là một đường đăng đáng tin, nên nhánh này phục vụ đúng
 * một câu hỏi: *clip này lên Trang được chưa, và đã lên thật chưa.*
 *
 * Chia sẻ bước cuối với nhánh Bài viết: cùng `SchedulePicker`, cùng khái niệm
 * "rải nhiều ngày". Từ góc nhìn chủ tiệm, chuẩn bị nội dung cả tuần là một việc
 * duy nhất — loại nội dung chỉ đổi cách *nhập vào*, không đổi cách *lên lịch*.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/input";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/state-views";
import { ToastContainer, type ToastItem } from "@/components/ui/toast";
import { mediaTypeOf, uploadMedia, type MediaAsset } from "@/features/content-creation/content-creation.api";
import {
  SchedulePicker,
  previewSchedule,
  type SchedulePlan,
} from "@/features/content-creation/schedule-picker";
import {
  approveVideoPost,
  cancelVideoPost,
  createVideoPost,
  listVideoPosts,
  type VideoPost,
  type VideoPostStatus,
} from "./video-posts.api";
import styles from "./video.module.css";

/** Kênh Havi kiểm ràng buộc — khớp `VIDEO_REQUIREMENTS` ở backend. */
const CHANNEL_LABELS: Record<string, string> = {
  reels: "Facebook Reels",
  tiktok: "TikTok",
  youtube: "YouTube Shorts",
};

/**
 * Nhãn trạng thái viết theo thứ *đã xảy ra*, không theo tên kỹ thuật.
 *
 * `verifying` cố tình không nói "đã đăng": Facebook nhận video xong vẫn có thể
 * từ chối sau đó. Nói sớm một nhịp là chủ tiệm đóng máy đi làm việc khác rồi
 * hôm sau phát hiện bài chưa bao giờ lên.
 */
const STATUS_LABELS: Record<VideoPostStatus, { text: string; tone: string }> = {
  ready_for_review: { text: "Chờ bạn duyệt", tone: "wait" },
  approved: { text: "Đã duyệt — đang xếp hàng gửi", tone: "wait" },
  publishing: { text: "Đang gửi lên Facebook", tone: "wait" },
  verifying: { text: "Facebook đang xử lý — chờ xác nhận", tone: "wait" },
  published: { text: "Đã lên Trang", tone: "ok" },
  failed: { text: "Gửi không thành công — thử lại được", tone: "bad" },
  failed_permanent: { text: "Không đăng được", tone: "bad" },
  pending_reconciliation: { text: "Đã gửi nhưng chưa xác nhận được", tone: "warn" },
  cancelled: { text: "Đã huỷ", tone: "muted" },
};

const scheduleFormatter = new Intl.DateTimeFormat("vi-VN", {
  timeZone: "Asia/Ho_Chi_Minh",
  weekday: "short",
  day: "2-digit",
  month: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});

type ClipDraft = {
  asset: MediaAsset;
  previewUrl: string;
};

function describeClip(asset: MediaAsset): string {
  const parts: string[] = [];
  if (asset.aspect_ratio) parts.push(`khung ${asset.aspect_ratio}`);
  if (typeof asset.duration_seconds === "number") {
    parts.push(`${Math.round(asset.duration_seconds)} giây`);
  }
  if (asset.has_audio === false) parts.push("không có tiếng");
  return parts.join(" · ");
}

export function VideoBranch() {
  const [posts, setPosts] = useState<VideoPost[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [draft, setDraft] = useState<ClipDraft | null>(null);
  const [caption, setCaption] = useState("");
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [plan, setPlan] = useState<SchedulePlan>({ publishNow: false, postsPerDay: 1 });
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const previewUrlRef = useRef<string | null>(null);

  const addToast = useCallback((toast: Omit<ToastItem, "id">) => {
    const id = `toast-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
    setToasts((prev) => [...prev, { ...toast, id }]);
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 6000);
  }, []);

  const load = useCallback(async () => {
    const result = await listVideoPosts();
    if (result.ok) {
      setPosts(result.data);
      setError(null);
    } else {
      setError(result.message);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  // Có bài đang trên đường sang Facebook thì hỏi lại định kỳ. Dừng hẳn khi
  // không còn bài nào đang chạy — poll mãi một danh sách đứng yên chỉ tốn pin
  // điện thoại của chủ tiệm.
  useEffect(() => {
    const inFlight = posts.some((p) =>
      ["approved", "publishing", "verifying"].includes(p.status),
    );
    if (!inFlight) return;
    const timer = setInterval(load, 5000);
    return () => clearInterval(timer);
  }, [posts, load]);

  useEffect(() => {
    return () => {
      if (previewUrlRef.current) URL.revokeObjectURL(previewUrlRef.current);
    };
  }, []);

  function resetDraft() {
    if (previewUrlRef.current) {
      URL.revokeObjectURL(previewUrlRef.current);
      previewUrlRef.current = null;
    }
    setDraft(null);
    setCaption("");
    setUploadProgress(0);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  async function onPickFile(files: FileList | null) {
    const file = files?.[0];
    if (!file) return;
    if (mediaTypeOf(file) !== "video") {
      setError("Chọn một file video giúp bạn nhé — mục này chỉ nhận clip.");
      return;
    }

    setError(null);
    setUploading(true);
    setUploadProgress(0);

    const previewUrl = URL.createObjectURL(file);
    previewUrlRef.current = previewUrl;

    const result = await uploadMedia(file, {
      onProgress: (percent) => setUploadProgress((prev) => Math.max(prev, percent)),
    });
    setUploading(false);

    if (!result.ok) {
      URL.revokeObjectURL(previewUrl);
      previewUrlRef.current = null;
      setError(result.message);
      return;
    }

    setDraft({ asset: result.data, previewUrl });
  }

  async function onSubmit() {
    if (!draft) return;
    setSubmitting(true);
    const result = await createVideoPost({
      sourceMediaId: draft.asset.id,
      caption: caption.trim(),
    });
    setSubmitting(false);

    if (!result.ok) {
      // Backend trả hết lý do một lượt — hiện nguyên văn để sửa một lần.
      setError(result.message);
      return;
    }

    setError(null);
    resetDraft();
    setPosts((prev) => [result.data, ...prev]);
    addToast({
      type: "success",
      icon: "🎬",
      title: "Clip đã vào hàng chờ duyệt",
      description: "Xem lại nội dung rồi bấm Duyệt & đăng khi bạn thấy ổn.",
    });
  }

  async function onApprove(post: VideoPost, scheduledAt?: string | null) {
    setBusyId(post.id);
    const result = await approveVideoPost(post.id, scheduledAt);
    setBusyId(null);

    if (!result.ok) {
      setError(result.message);
      return;
    }

    setError(null);
    setPosts((prev) => prev.map((p) => (p.id === post.id ? result.data.post : p)));
    addToast({
      type: "success",
      icon: "🚀",
      title: scheduledAt
        ? "Đã xếp lịch"
        : result.data.queuedForPublish
          ? "Đang gửi lên Facebook"
          : "Đã duyệt — sẽ gửi ở lượt kế tiếp",
      description: scheduledAt
        ? "Havi sẽ gửi clip đúng giờ đã hẹn rồi đọc lại Trang để xác nhận."
        : "Havi sẽ đọc lại Trang để xác nhận bài đã lên thật, không chỉ dựa vào phản hồi lúc gửi.",
    });
  }

  /**
   * Duyệt cả loạt theo lịch đã chọn — bước cuối dùng chung với nhánh Bài viết.
   *
   * Gọi tuần tự chứ không `Promise.all`: mỗi clip cần đúng khung giờ của nó, và
   * gửi song song thì thứ tự tới backend không còn là thứ tự chủ tiệm đã xếp.
   */
  async function onApproveAll() {
    const slots = plan.publishNow ? [] : previewSchedule(pendingPosts.length, plan.postsPerDay);
    for (const [index, post] of pendingPosts.entries()) {
      await onApprove(post, plan.publishNow ? null : slots[index].toISOString());
    }
    load();
  }

  async function onCancel(post: VideoPost) {
    if (!confirm("Huỷ video này khỏi hàng chờ?")) return;
    setBusyId(post.id);
    const result = await cancelVideoPost(post.id);
    setBusyId(null);
    if (!result.ok) {
      setError(result.message);
      return;
    }
    load();
  }

  // Thứ tự hiện ra là thứ tự lên bài. `listVideoPosts` trả mới nhất trước, nên
  // đảo lại: clip tải lên đầu tiên là câu chuyện của ngày đầu tiên.
  const pendingPosts = posts
    .filter((post) => post.status === "ready_for_review")
    .slice()
    .reverse();

  const eligibleChannels = draft?.asset.eligible_channels ?? [];
  const canPostToReels = eligibleChannels.includes("reels" as never);

  return (
    <>
      {error ? <ErrorState title={error} /> : null}

      <section className={styles.uploadCard} aria-labelledby="video-upload-title">
        <h2 id="video-upload-title" className={styles.sectionTitle}>
          Tải clip lên
        </h2>

        <input
          ref={fileInputRef}
          type="file"
          accept="video/*"
          className={styles.hiddenInput}
          onChange={(event) => onPickFile(event.target.files)}
        />

        {!draft ? (
          <div className={styles.dropzone}>
            <p className={styles.dropzoneHint}>
              Clip dọc 9:16, từ 3 đến 90 giây. Havi kiểm ngay khi tải lên để bạn còn
              kịp quay lại nếu có gì chưa hợp.
            </p>
            <Button
              variant="primary"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
            >
              {uploading ? `Đang tải lên ${uploadProgress}%` : "Chọn clip từ máy"}
            </Button>
          </div>
        ) : (
          <div className={styles.draftGrid}>
            <video
              className={styles.preview}
              src={draft.previewUrl}
              controls
              playsInline
              aria-label="Xem lại clip vừa tải lên"
            />

            <div className={styles.draftForm}>
              <p className={styles.clipSpec}>{describeClip(draft.asset) || "Đang đọc thông số clip…"}</p>

              <ul className={styles.channelList}>
                {Object.entries(CHANNEL_LABELS).map(([channel, label]) => {
                  const fits = eligibleChannels.includes(channel as never);
                  return (
                    <li key={channel} className={fits ? styles.channelFits : styles.channelUnfit}>
                      <span aria-hidden="true">{fits ? "✓" : "✕"}</span>
                      <span>{`${label}: ${fits ? "đăng được" : "chưa hợp"}`}</span>
                    </li>
                  );
                })}
              </ul>

              <label className={styles.label} htmlFor="video-caption">
                Nội dung đăng kèm
              </label>
              <Textarea
                id="video-caption"
                value={caption}
                onChange={(event) => setCaption(event.target.value)}
                placeholder="Viết vài dòng giới thiệu clip này…"
                rows={4}
              />

              <div className={styles.draftActions}>
                <Button
                  variant="primary"
                  onClick={onSubmit}
                  disabled={submitting || !canPostToReels}
                >
                  {submitting ? "Đang lưu…" : "Đưa vào hàng chờ duyệt"}
                </Button>
                <Button variant="outline" onClick={resetDraft} disabled={submitting}>
                  Chọn clip khác
                </Button>
              </div>

              {!canPostToReels && draft.asset.aspect_ratio ? (
                <p className={styles.blockReason} role="alert">
                  Clip này chưa đăng được lên Facebook Reels. Reels cần khung dọc 9:16
                  và độ dài từ 3 đến 90 giây.
                </p>
              ) : null}
            </div>
          </div>
        )}
      </section>

      <section aria-labelledby="video-list-title">
        <h2 id="video-list-title" className={styles.sectionTitle}>
          Video của bạn
        </h2>

        {loading ? (
          <LoadingState title="Đang tải danh sách video…" />
        ) : posts.length === 0 ? (
          <EmptyState
            title="Chưa có video nào"
            body="Tải một clip lên để bắt đầu."
          />
        ) : (
          <ul className={styles.postList}>
            {posts.map((post) => {
              const status = STATUS_LABELS[post.status];
              const isBusy = busyId === post.id;
              return (
                <li key={post.id} className={styles.postRow}>
                  <div className={styles.postMain}>
                    <span className={`${styles.statusPill} ${styles[`tone_${status.tone}`]}`}>
                      {status.text}
                    </span>
                    <p className={styles.postCaption}>
                      {post.caption || <em>Chưa có nội dung đăng kèm</em>}
                    </p>
                    {post.scheduled_at ? (
                      <p className={styles.postSchedule}>
                        Sẽ đăng {scheduleFormatter.format(new Date(post.scheduled_at))}
                      </p>
                    ) : null}
                    {post.error_message ? (
                      <p className={styles.postError}>{post.error_message}</p>
                    ) : null}
                  </div>

                  <div className={styles.postActions}>
                    {post.status === "ready_for_review" ? (
                      <Button variant="outline" onClick={() => onCancel(post)} disabled={isBusy}>
                        Bỏ clip này
                      </Button>
                    ) : null}
                  </div>
                </li>
              );
            })}
          </ul>
        )}

        {pendingPosts.length ? (
          <SchedulePicker
            noun="video"
            labels={pendingPosts.map(
              (post, index) => post.caption.slice(0, 60) || `Clip ${index + 1}`,
            )}
            plan={plan}
            onPlanChange={setPlan}
            onConfirm={onApproveAll}
            busy={busyId !== null}
          />
        ) : null}
      </section>

      <ToastContainer
        toasts={toasts}
        onDismiss={(id) => setToasts((prev) => prev.filter((t) => t.id !== id))}
      />
    </>
  );
}
