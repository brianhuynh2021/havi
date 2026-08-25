"use client";

/**
 * Đăng bài — **một tab, một luồng**, rẽ nhánh ở bước đầu tiên.
 *
 *     Bước 1  Đăng gì?        [ Bài viết ]  hoặc  [ Video ]
 *                                  │                  │
 *     Bước 2  Chuẩn bị      kể cho Havi nghe      tải clip lên
 *                           → Havi viết nháp      → viết nội dung
 *                                  │                  │
 *     Bước 3  Lên lịch       └──────┬───────────┘
 *                            rải nhiều ngày, hoặc đăng ngay
 *
 * Vì sao gộp: chủ tiệm không nghĩ theo "màn Bài viết" và "màn Video". Họ nghĩ
 * *"tối nay ngồi chuẩn bị nội dung cho tuần sau"* — trong đó có bài chữ và có
 * clip, xen kẽ nhau. Tách thành hai tab là bắt họ làm cùng một việc hai lần và
 * tự ghép lịch trong đầu.
 *
 * Loại nội dung chỉ đổi **cách nhập vào**. Bước lên lịch giống hệt nhau ở cả
 * hai nhánh, và đó là lý do `SchedulePicker` dùng chung.
 */

import { useCallback, useEffect, useState } from "react";
import { ErrorState, LoadingState } from "@/components/ui/state-views";
import { ToastContainer, type ToastItem } from "@/components/ui/toast";
import { pushNotification } from "@/components/notifications/notification-store";
import { VoiceRecorderModal } from "@/features/voice-note/voice-recorder-modal";
import { completeTask } from "@/features/roadmap/roadmap.api";
import { VideoBranch } from "@/features/video/video-branch";
import {
  approveAll,
  createJob,
  dismissAllItems,
  dismissItem,
  generateItemImage,
  listPendingItems,
  uploadMedia,
  type ContentItem,
  type RawInput,
} from "./content-creation.api";
import { DraftList } from "./draft-list";
import { PostBrief, type CampaignGoal, type RawChip, type UploadRow } from "./post-brief";
import { QuotaBanner } from "./quota-banner";
import { SchedulePicker, type SchedulePlan } from "./schedule-picker";
import { useJobPolling } from "./use-job-polling";
import styles from "./content-creation.module.css";

/** Bài chữ đi Facebook Page. Google Business dùng chung nội dung, thêm sau được. */
const TARGET_CHANNELS = ["facebook_page"] as const;

type ContentKind = "post" | "video";

function shortLabel(text: string): string {
  return text.length > 40 ? `${text.slice(0, 40)}…` : text;
}

function makeKey(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
}

export function ContentCreationScreen() {
  const [kind, setKind] = useState<ContentKind>("post");

  const [chips, setChips] = useState<RawChip[]>([]);
  const [uploads, setUploads] = useState<UploadRow[]>([]);
  const [note, setNote] = useState("");
  const [selectedGoal, setSelectedGoal] = useState<string | null>(null);

  const [items, setItems] = useState<ContentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const [jobId, setJobId] = useState<string | null>(null);
  const [quotaKey, setQuotaKey] = useState(0);
  const [busyIds, setBusyIds] = useState<string[]>([]);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [generatingImageId, setGeneratingImageId] = useState<string | null>(null);
  const [voiceModalOpen, setVoiceModalOpen] = useState(false);
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const [plan, setPlan] = useState<SchedulePlan>({ publishNow: false, postsPerDay: 1 });

  // Blob URL của ảnh xem trước phải được thu hồi bằng tay, nếu không mỗi lần
  // chọn ảnh lại giữ thêm một bản trong bộ nhớ trình duyệt cho tới khi tải lại
  // trang — thấy rõ trên điện thoại sau vài lượt tạo bài.
  const [previewUrls] = useState(() => new Set<string>());

  useEffect(() => {
    return () => {
      for (const url of previewUrls) URL.revokeObjectURL(url);
      previewUrls.clear();
    };
  }, [previewUrls]);

  function forgetPreview(url: string | undefined) {
    if (!url || !previewUrls.has(url)) return;
    URL.revokeObjectURL(url);
    previewUrls.delete(url);
  }

  const addToast = useCallback((toast: Omit<ToastItem, "id">) => {
    const id = makeKey("toast");
    setToasts((prev) => [...prev, { ...toast, id }]);
    if (toast.type !== "loading") {
      setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 6000);
    }
    return id;
  }, []);

  const loadItems = useCallback(async () => {
    const result = await listPendingItems();
    if (result.ok) {
      setItems(result.data);
      setError(null);
    } else {
      setError(result.message);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    loadItems();
  }, [loadItems]);

  // Lộ trình gửi chủ đề sang qua query string. Nạp vào ô ghi chú thay vì tự tạo
  // bài luôn: nhiệm vụ là gợi ý, còn nội dung cuối cùng vẫn do chủ tiệm chốt.
  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    if (params.get("kind") === "video") setKind("video");
    const topic = params.get("topic");
    if (!topic) return;
    setNote(topic);
    setNotice(`Đã nạp chủ đề từ Lộ trình: “${topic}”.`);
  }, []);

  const onJobReady = useCallback(() => {
    setToasts((prev) => prev.filter((t) => t.type !== "loading"));
    setNotice("Havi vừa viết xong bài mới. Cuộn xuống để xem và xếp lịch.");
    pushNotification({
      type: "draft_ready",
      title: "Havi vừa viết xong bài mới",
      description: "Bản nháp đã sẵn sàng để bạn duyệt.",
    });
    addToast({
      type: "success",
      title: "Havi viết xong rồi",
      description: "Bản nháp đã nằm trong danh sách bên dưới.",
    });
    loadItems();
  }, [addToast, loadItems]);

  const poll = useJobPolling(jobId, onJobReady);
  const uploading = uploads.some((upload) => upload.status === "uploading");
  const generating = poll.status === "queued" || poll.status === "processing";

  async function onPickFiles(files: FileList | null) {
    if (!files?.length) return;
    setError(null);

    const pending = Array.from(files).map((file, index) => {
      const previewUrl = URL.createObjectURL(file);
      previewUrls.add(previewUrl);
      return {
        file,
        row: {
          key: `upload-${Date.now()}-${index}-${file.name}`,
          fileName: file.name,
          previewUrl,
          progress: 0,
          status: "uploading" as const,
          controller: new AbortController(),
        },
      };
    });

    setUploads((prev) => [...prev, ...pending.map((item) => item.row)]);

    await Promise.all(
      pending.map(async ({ file, row }) => {
        const result = await uploadMedia(file, {
          signal: row.controller.signal,
          onProgress: (progress) =>
            setUploads((prev) =>
              prev.map((upload) =>
                upload.key === row.key
                  ? { ...upload, progress: Math.max(upload.progress, progress) }
                  : upload,
              ),
            ),
        });

        if (!result.ok) {
          setUploads((prev) =>
            prev.map((upload) =>
              upload.key === row.key
                ? { ...upload, status: "failed", message: result.message }
                : upload,
            ),
          );
          setError(result.message);
          return;
        }

        setUploads((prev) =>
          prev.map((upload) =>
            upload.key === row.key
              ? { ...upload, progress: 100, status: "complete", assetId: result.data.id }
              : upload,
          ),
        );
        setChips((prev) => [
          ...prev,
          {
            key: result.data.id,
            kind: "photo",
            label: file.name,
            previewUrl: row.previewUrl,
            input: {
              kind: "photo",
              media_asset_id: result.data.id,
              preview_url: row.previewUrl,
            },
          },
        ]);
      }),
    );
  }

  function addNote() {
    const text = note.trim();
    if (!text) return;
    setChips((prev) => [
      ...prev,
      { key: makeKey("note"), kind: "text", label: shortLabel(text), input: { kind: "text", text } },
    ]);
    setNote("");
  }

  function removeChip(key: string) {
    const removed = chips.find((chip) => chip.key === key);
    forgetPreview(removed?.previewUrl);
    setChips((prev) => prev.filter((chip) => chip.key !== key));
    setUploads((prev) => prev.filter((upload) => upload.assetId !== key));
  }

  function selectGoal(goal: CampaignGoal) {
    setSelectedGoal(goal.id);
    setNote(goal.text);
  }

  /** Gom chips + ghi chú đang gõ dở thành một job. Dùng chung cho nút và giọng nói. */
  async function submitJob(inputs: RawInput[], loadingTitle: string) {
    if (!inputs.length) return;
    setError(null);
    setNotice(null);

    const result = await createJob(inputs, makeKey("job"), [...TARGET_CHANNELS]);
    setQuotaKey((key) => key + 1);
    if (!result.ok) {
      setError(result.message);
      return;
    }

    for (const chip of chips) forgetPreview(chip.previewUrl);
    setChips([]);
    setUploads([]);
    setNote("");

    poll.addJobId(result.data.id);
    setJobId(result.data.id);
    addToast({
      type: "loading",
      title: loadingTitle,
      description: "Bản nháp sẽ hiện bên dưới trong giây lát.",
    });
  }

  function generate() {
    const inputs = chips.map((chip) => chip.input);
    if (note.trim()) inputs.push({ kind: "text", text: note.trim() });
    return submitJob(inputs, "Havi đang viết bài…");
  }

  function generateFromVoice(text: string) {
    const inputs = [...chips.map((chip) => chip.input), { kind: "text" as const, text }];
    return submitJob(inputs, "Havi đang viết bài từ lời bạn nói…");
  }

  /**
   * Duyệt cả loạt theo lịch đã chọn — bước cuối, và là **chỗ duy nhất** bài
   * được đưa lên Trang. Backend rải giờ; thứ tự `items` là thứ tự lên bài.
   */
  async function onApproveAll() {
    const ids = items.map((item) => item.id);
    if (!ids.length) return;
    setBusyIds(ids);
    const result = await approveAll(ids, plan.publishNow, plan.postsPerDay);
    setBusyIds([]);

    if (!result.ok) {
      setError(result.message);
      return;
    }
    markRoadmapTaskDone();
    setNotice(
      plan.publishNow
        ? `Đã duyệt ${result.data.approved.length} bài — Havi đang gửi lên Trang.`
        : `Đã xếp lịch ${result.data.approved.length} bài. Xem và đổi giờ ở mục Lịch đăng.`,
    );
    loadItems();
  }

  async function onDismiss(id: string) {
    setBusyIds((prev) => [...prev, id]);
    const result = await dismissItem(id);
    setBusyIds((prev) => prev.filter((busy) => busy !== id));
    if (!result.ok) {
      setError(result.message);
      return;
    }
    setItems((prev) => prev.filter((item) => item.id !== id));
  }

  async function onDismissAll() {
    const ids = items.map((item) => item.id);
    if (!ids.length) return;
    if (!confirm(`Xoá tất cả ${ids.length} bản nháp?`)) return;
    setBusyIds(ids);
    const result = await dismissAllItems(ids);
    setBusyIds([]);
    if (!result.ok) {
      setError(result.message);
      return;
    }
    setItems([]);
  }

  async function onGenerateImage(id: string) {
    setGeneratingImageId(id);
    const result = await generateItemImage(id, "3d_studio");
    setGeneratingImageId(null);
    if (!result.ok) {
      addToast({ type: "error", title: "Chưa tìm được ảnh", description: result.message });
      return;
    }
    setItems((prev) =>
      prev.map((item) =>
        item.id === id ? { ...item, media_url: result.data.media_url } : item,
      ),
    );
  }

  /** Duyệt bài xong thì nhiệm vụ trong Lộ trình cũng coi như xong — nếu có. */
  function markRoadmapTaskDone() {
    if (typeof window === "undefined") return;
    const taskId = new URLSearchParams(window.location.search).get("task_id");
    if (!taskId) return;
    completeTask(taskId, {
      evidence_text: "Đã duyệt và lên lịch một bài viết trên Trang",
      evidence_type: "link",
    }).catch(() => {});
  }

  return (
    <>
      <header className={styles.header}>
        <h1 className={styles.title}>Đăng bài</h1>
        <p className={styles.subtitle}>
          Chuẩn bị nội dung cho cả tuần trong một lần ngồi, rồi để Havi đăng đều
          mỗi ngày.
        </p>
      </header>

      <QuotaBanner reloadKey={quotaKey} />

      {error ? <ErrorState title={error} /> : null}
      {notice ? (
        <p className={styles.notice} role="status">
          {notice}
        </p>
      ) : null}

      {/* BƯỚC 1 — rẽ nhánh. Từ đây trở xuống, hai loại nội dung đi hai đường
          khác nhau cho tới bước xếp lịch. */}
      <section className={styles.kindSection} aria-labelledby="kind-title">
        <div className={styles.stepTitle}>
          <span className={styles.stepNumber}>1</span>
          <span id="kind-title">Bạn muốn đăng gì?</span>
        </div>
        <div className={styles.kindGrid} role="tablist" aria-label="Loại nội dung">
          <button
            type="button"
            role="tab"
            aria-selected={kind === "post"}
            className={`${styles.kindCard} ${kind === "post" ? styles.kindCardActive : ""}`}
            onClick={() => setKind("post")}
          >
            <span className={styles.kindIcon}>📝</span>
            <strong>Bài viết</strong>
            <small>Kể vài dòng hoặc nạp ảnh — Havi viết bài cho Trang.</small>
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={kind === "video"}
            className={`${styles.kindCard} ${kind === "video" ? styles.kindCardActive : ""}`}
            onClick={() => setKind("video")}
          >
            <span className={styles.kindIcon}>🎬</span>
            <strong>Video</strong>
            <small>Bạn quay và cắt sẵn, Havi đăng lên Reels và xác nhận đã lên.</small>
          </button>
        </div>
      </section>

      {kind === "video" ? (
        <VideoBranch />
      ) : (
        <>
          <PostBrief
            chips={chips}
            uploads={uploads}
            note={note}
            selectedGoal={selectedGoal}
            uploading={uploading}
            generating={generating}
            onNoteChange={setNote}
            onAddNote={addNote}
            onRemoveChip={removeChip}
            onPickFiles={onPickFiles}
            onOpenVoice={() => setVoiceModalOpen(true)}
            onSelectGoal={selectGoal}
            onGenerate={generate}
          />

          {loading ? (
            <LoadingState title="Đang tải bản nháp…" />
          ) : (
            <>
              <DraftList
                items={items}
                busyIds={busyIds}
                editingId={editingId}
                onEdit={setEditingId}
                onSaved={(saved) => {
                  setItems((prev) =>
                    prev.map((item) => (item.id === saved.id ? saved : item)),
                  );
                  setEditingId(null);
                  setNotice("Đã lưu bản sửa — bài vẫn đang chờ bạn duyệt.");
                }}
                onDismiss={onDismiss}
                onDismissAll={onDismissAll}
                onGenerateImage={onGenerateImage}
                generatingImageId={generatingImageId}
              />

              {/* BƯỚC 3 — chung với nhánh Video. */}
              {items.length ? (
                <SchedulePicker
                  noun="bài"
                  labels={items.map((item, index) =>
                    shortLabel(item.text) || `Bài ${index + 1}`,
                  )}
                  plan={plan}
                  onPlanChange={setPlan}
                  onConfirm={onApproveAll}
                  busy={busyIds.length > 0}
                />
              ) : null}
            </>
          )}
        </>
      )}

      <VoiceRecorderModal
        isOpen={voiceModalOpen}
        onClose={() => setVoiceModalOpen(false)}
        onInsertNote={(text) => {
          setNote(text);
          setVoiceModalOpen(false);
        }}
        onDirectGenerate={async (text) => {
          setVoiceModalOpen(false);
          await generateFromVoice(text);
        }}
      />

      <ToastContainer
        toasts={toasts}
        onDismiss={(id) => setToasts((prev) => prev.filter((toast) => toast.id !== id))}
      />
    </>
  );
}
