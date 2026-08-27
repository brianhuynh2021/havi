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

import { useLanguage, type Translate } from "@/lib/i18n/language-context";
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
import { DangerConfirmModal } from "@/features/settings/danger-confirm-modal";
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
// i18n-data: nhãn hiện ra, `t()` dịch ở chỗ render bên dưới
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

/**
 * Khung hình nói bằng hình dạng, không bằng số pixel.
 *
 * "khung 720:1648" không cho biết clip dọc hay ngang — chủ tiệm phải tự chia
 * trong đầu. Quy về dạng `:9` thì đọc được ngay: 20.6:9 là dọc, 16:9 là ngang.
 * Khớp với `describe_shape` ở `domain/policies/video_constraints.py`.
 */
function describeShape(
  width: number | null | undefined,
  height: number | null | undefined,
  t: Translate,
): string | null {
  if (!width || !height) return null;
  const ratio = width / height;
  if (ratio < 1) return t("khung dọc {value}:9", { value: +(((1 / ratio) * 9).toFixed(1)) });
  if (ratio === 1) return t("khung vuông 1:1");
  return t("khung ngang {value}:9", { value: +(ratio * 9).toFixed(1) });
}

function describeClip(asset: MediaAsset, t: Translate): string {
  const parts: string[] = [];
  const shape = describeShape(asset.width, asset.height, t);
  if (shape) parts.push(shape);
  if (typeof asset.duration_seconds === "number") {
    parts.push(t("{value} giây", { value: Math.round(asset.duration_seconds) }));
  }
  if (asset.has_audio === false) parts.push(t("không có tiếng"));
  return parts.join(" · ");
}

export function VideoBranch() {
  const {
    t
  } = useLanguage();

  const [posts, setPosts] = useState<VideoPost[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [draft, setDraft] = useState<ClipDraft | null>(null);
  const [caption, setCaption] = useState("");
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  /** Lý do backend từ chối clip. Rỗng = chưa hỏi, hoặc clip hợp lệ. */
  const [blockReasons, setBlockReasons] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [plan, setPlan] = useState<SchedulePlan>({ publishNow: false, postsPerDay: 1 });
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const [cancellingPost, setCancellingPost] = useState<VideoPost | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const previewUrlRef = useRef<string | null>(null);
  const uploadControllerRef = useRef<AbortController | null>(null);

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
      uploadControllerRef.current?.abort();
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
      setError(t("Chọn một file video giúp bạn nhé — mục này chỉ nhận clip."));
      return;
    }

    setError(null);
    setUploading(true);
    setUploadProgress(0);
    const controller = new AbortController();
    uploadControllerRef.current = controller;

    const previewUrl = URL.createObjectURL(file);
    previewUrlRef.current = previewUrl;

    const result = await uploadMedia(file, {
      signal: controller.signal,
      onProgress: (percent) => setUploadProgress((prev) => Math.max(prev, percent)),
    });
    if (uploadControllerRef.current === controller) uploadControllerRef.current = null;
    setUploading(false);

    if (!result.ok) {
      URL.revokeObjectURL(previewUrl);
      previewUrlRef.current = null;
      setError(controller.signal.aborted ? null : result.message);
      if (fileInputRef.current) fileInputRef.current.value = "";
      return;
    }

    setBlockReasons([]);
    setDraft({ asset: result.data, previewUrl });
  }

  function cancelClipUpload() {
    uploadControllerRef.current?.abort();
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
      // Backend trả hết lý do một lượt — hiện nguyên văn để sửa một lần, ngay
      // cạnh clip chứ không phải ở dải lỗi trên cùng màn hình.
      setBlockReasons(result.message.split(". ").filter(Boolean));
      return;
    }

    setError(null);
    setBlockReasons([]);
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

  async function onCancelRequested(post: VideoPost) {
    setCancellingPost(post);
  }

  async function onCancel() {
    if (!cancellingPost) return;
    const post = cancellingPost;
    setCancellingPost(null);
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

  return (
    <>
      {error ? <ErrorState title={t(error)} /> : null}

      <section className={styles.uploadCard} aria-labelledby="video-upload-title">
        <h2 id="video-upload-title" className={styles.sectionTitle}>{t("Tải clip lên")}</h2>

        <input
          ref={fileInputRef}
          type="file"
          accept="video/*"
          className={styles.hiddenInput}
          onChange={(event) => onPickFile(event.target.files)}
        />

        {!draft ? (
          <div className={styles.dropzone}>
            <p className={styles.dropzoneHint}>{t(
              "Clip dọc 9:16, từ 3 đến 90 giây. Havi kiểm ngay khi tải lên để bạn còn\n              kịp quay lại nếu có gì chưa hợp."
            )}</p>
            <div className={styles.uploadControls}>
              <Button
                variant="primary"
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading}
              >
                {uploading ? t("Đang tải lên {uploadProgress}%", { uploadProgress: uploadProgress }) : "Chọn clip từ máy"}
              </Button>
              {uploading ? (
                <Button variant="outline" onClick={cancelClipUpload}>
                  {t("Huỷ tải")}
                </Button>
              ) : null}
            </div>
          </div>
        ) : (
          <div className={styles.draftGrid}>
            <video
              className={styles.preview}
              src={draft.previewUrl}
              controls
              playsInline
              aria-label={t("Xem lại clip vừa tải lên")}
            />

            <div className={styles.draftForm}>
              <p className={styles.clipSpec}>{describeClip(draft.asset, t) || "Đang đọc thông số clip…"}</p>

              <ul className={styles.channelList}>
                {Object.entries(CHANNEL_LABELS).map(([channel, label]) => {
                  const fits = eligibleChannels.includes(channel as never);
                  return (
                    <li key={channel} className={fits ? styles.channelFits : styles.channelUnfit}>
                      <span aria-hidden="true">{fits ? "✓" : "✕"}</span>
                      <span>{`${label}: ${t(fits ? "đăng được" : "chưa hợp")}`}</span>
                    </li>
                  );
                })}
              </ul>

              <label className={styles.label} htmlFor="video-caption">{t("Nội dung đăng kèm")}</label>
              <Textarea
                id="video-caption"
                value={caption}
                onChange={(event) => setCaption(event.target.value)}
                placeholder={t("Viết vài dòng giới thiệu clip này…")}
                rows={4}
              />

              <div className={styles.draftActions}>
                <Button variant="primary" onClick={onSubmit} disabled={submitting}>
                  {t(submitting ? "Đang lưu…" : "Đưa vào hàng chờ duyệt")}
                </Button>
                <Button variant="outline" onClick={resetDraft} disabled={submitting}>{t("Chọn clip khác")}</Button>
              </div>

              {blockReasons.length ? (
                <div className={styles.blockReason} role="alert">
                  <strong>{t("Clip này chưa đăng được:")}</strong>
                  <ul>
                    {blockReasons.map((reason) => (
                      <li key={reason}>{reason}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </div>
          </div>
        )}
      </section>

      <section aria-labelledby="video-list-title">
        <h2 id="video-list-title" className={styles.sectionTitle}>{t("Video của bạn")}</h2>

        {loading ? (
          <LoadingState title={t("Đang tải danh sách video…")} />
        ) : posts.length === 0 ? (
          <EmptyState
            title={t("Chưa có video nào")}
            body={t("Tải một clip lên để bắt đầu.")}
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
                      {t(status.text)}
                    </span>
                    <p className={styles.postCaption}>
                      {post.caption || <em>{t("Chưa có nội dung đăng kèm")}</em>}
                    </p>
                    {post.scheduled_at ? (
                      <p className={styles.postSchedule}>{t("Sẽ đăng")}{" "}{scheduleFormatter.format(new Date(post.scheduled_at))}
                      </p>
                    ) : null}
                    {post.error_message ? (
                      <p className={styles.postError}>{post.error_message}</p>
                    ) : null}
                  </div>

                  <div className={styles.postActions}>
                    {post.status === "ready_for_review" ? (
                      <Button variant="outline" onClick={() => onCancelRequested(post)} disabled={isBusy}>{t("Bỏ clip này")}</Button>
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

      <DangerConfirmModal
        isOpen={cancellingPost !== null}
        type="custom"
        isDeleting={busyId === cancellingPost?.id}
        customKeyword="HUYVIDEO"
        customTitle={t("Xác nhận huỷ video")}
        customLostItems={["Video này sẽ bị huỷ khỏi hàng chờ duyệt và không được xuất bản."]}
        onClose={() => setCancellingPost(null)}
        onConfirm={onCancel}
      />
    </>
  );
}
