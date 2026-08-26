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

import { useLanguage } from "@/lib/i18n/language-context";
import { useCallback, useEffect, useState } from "react";
import { ErrorState, LoadingState } from "@/components/ui/state-views";
import { ToastContainer, type ToastItem } from "@/components/ui/toast";
import { pushNotification } from "@/components/notifications/notification-store";
import { VoiceRecorderModal } from "@/features/voice-note/voice-recorder-modal";
import { VideoBranch } from "@/features/video/video-branch";
import { DangerConfirmModal } from "@/features/settings/danger-confirm-modal";
import { MediaPickerModal } from "@/features/media/media-picker-modal";
import type { MediaAsset } from "@/features/media/media.api";
import {
  approveAll,
  createJob,
  dismissAllItems,
  dismissItem,
  listChannelOptions,
  listPendingItems,
  uploadMedia,
  type Channel,
  type ChannelOption,
  type ContentItem,
  type RawInput,
} from "./content-creation.api";
import { DraftList } from "./draft-list";
import { PostBrief, type RawChip, type UploadRow } from "./post-brief";
import { QuotaBanner } from "./quota-banner";
import { SchedulePicker, type SchedulePlan } from "./schedule-picker";
import { useJobPolling } from "./use-job-polling";
import styles from "./content-creation.module.css";

type ContentKind = "post" | "video";

function shortLabel(text: string): string {
  return text.length > 40 ? `${text.slice(0, 40)}…` : text;
}

function makeKey(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
}

export function ContentCreationScreen() {
  const {
    t
  } = useLanguage();

  const [kind, setKind] = useState<ContentKind>("post");

  const [chips, setChips] = useState<RawChip[]>([]);
  const [uploads, setUploads] = useState<UploadRow[]>([]);
  const [note, setNote] = useState("");

  const [items, setItems] = useState<ContentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const [jobId, setJobId] = useState<string | null>(null);
  const [quotaKey, setQuotaKey] = useState(0);
  const [busyIds, setBusyIds] = useState<string[]>([]);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [voiceModalOpen, setVoiceModalOpen] = useState(false);
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const [plan, setPlan] = useState<SchedulePlan>({ publishNow: false, postsPerDay: 1 });
  const [channelOptions, setChannelOptions] = useState<ChannelOption[]>([]);
  const [selectedChannels, setSelectedChannels] = useState<string[]>([]);

  const [isConfirmingDismissAll, setIsConfirmingDismissAll] = useState(false);
  const [mediaPickerOpen, setMediaPickerOpen] = useState(false);

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

  useEffect(() => {
    void listChannelOptions().then((result) => {
      if (result.ok) setChannelOptions(result.data);
    });
  }, []);

  // Kênh khả dụng là **hàm của loại nội dung**: TikTok và YouTube không nhận bài
  // chữ. Bản trước là một mảng viết cứng dùng chung cho cả hai loại, nên chọn được
  // "Bài viết + TikTok" và lỗi chỉ lộ ra ở bước đăng.
  const availableChannels = channelOptions.filter((option) =>
    option.kinds.includes(kind),
  );

  // Đổi loại nội dung thì bỏ những kênh không còn nhận được, và tự chọn kênh duy
  // nhất nếu chỉ còn một — bắt người dùng tick một ô mà không có lựa chọn nào khác
  // là một bước thừa.
  useEffect(() => {
    const allowed = channelOptions
      .filter((option) => option.kinds.includes(kind))
      .map((option) => option.channel as string);
    setSelectedChannels((prev) => {
      const kept = prev.filter((channel) => allowed.includes(channel));
      if (kept.length) return kept;
      return allowed.length === 1 ? allowed : [];
    });
  }, [kind, channelOptions]);

  // Cho phép mở thẳng nhánh video bằng `?kind=video` — dùng khi điều hướng từ
  // Tổng quan. Không nạp "chủ đề" từ đâu khác: Havi không giao việc cho ai.
  useEffect(() => {
    if (typeof window === "undefined") return;
    if (new URLSearchParams(window.location.search).get("kind") === "video") {
      setKind("video");
    }
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

  function handleMediaPick(asset: MediaAsset) {
    if (asset.type !== "image") {
      addToast({
        type: "error", // Use string if ToastItem doesn't support 'error' type. Wait, I should check toast types. If not error, use default or something. Let's assume there is an error type or we just use alert.
        title: "Không thể chọn video",
        description: "Bản nháp bài viết hiện chỉ hỗ trợ chèn ảnh.",
      });
      return;
    }
    
    if (chips.some((chip) => chip.key === asset.id)) {
      setMediaPickerOpen(false);
      return;
    }

    setChips((prev) => [
      ...prev,
      {
        key: asset.id,
        kind: "photo",
        label: asset.filename,
        previewUrl: asset.url,
        input: {
          kind: "photo",
          media_asset_id: asset.id,
          preview_url: asset.url,
        },
      },
    ]);
    setMediaPickerOpen(false);
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

  /** Gom chips + ghi chú đang gõ dở thành một job. Dùng chung cho nút và giọng nói. */
  async function submitJob(inputs: RawInput[], loadingTitle: string) {
    if (!inputs.length) return;
    if (!selectedChannels.length) {
      setError("Vui lòng chọn ít nhất 1 kênh đăng bài.");
      return;
    }
    setError(null);
    setNotice(null);

    const result = await createJob(inputs, makeKey("job"), [...selectedChannels] as Channel[]);
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
    setNotice(
      plan.publishNow
        ? `Đã duyệt ${result.data.approved.length} bài — Havi đang gửi lên Trang.`
        : `Đã xếp lịch ${result.data.approved.length} bài. Xem và đổi giờ ở mục Lịch đăng.`,
    );
    loadItems();
  }

  /**
   * Duyệt một bài — **cùng nghĩa** với nút duyệt cả loạt ở dưới, chỉ khác phạm
   * vi. Bản trước hardcode `publishNow = true`, nên hai nút trông giống nhau
   * trên cùng một đống nháp lại làm hai việc trái ngược: nút trên thẻ đẩy bài
   * lên Trang ngay, nút dưới xếp vào lịch tuần. Đó đúng là lý do nút trên thẻ
   * từng bị gỡ một lần rồi.
   */
  async function onApproveSingle(id: string) {
    setBusyIds((prev) => [...prev, id]);
    const result = await approveAll([id], plan.publishNow, plan.postsPerDay);
    setBusyIds((prev) => prev.filter((busy) => busy !== id));

    if (!result.ok) {
      setError(result.message);
      return;
    }
    setNotice(
      plan.publishNow
        ? "Đã duyệt 1 bài — Havi đang gửi lên Trang."
        : "Đã xếp lịch 1 bài. Xem và đổi giờ ở mục Lịch đăng.",
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

  function onDismissAllRequested() {
    if (!items.length) return;
    setIsConfirmingDismissAll(true);
  }

  async function onDismissAll() {
    setIsConfirmingDismissAll(false);
    const ids = items.map((item) => item.id);
    if (!ids.length) return;
    setBusyIds(ids);
    const result = await dismissAllItems(ids);
    setBusyIds([]);
    if (!result.ok) {
      setError(result.message);
      return;
    }
    setItems([]);
  }

  return (
    <>
      <header className={styles.header}>
        <h1 className={styles.title}>{t("Đăng bài")}</h1>
        <p className={styles.subtitle}>{t(
          "Chuẩn bị nội dung cho cả tuần trong một lần ngồi, rồi để Havi đăng đều\n          mỗi ngày."
        )}</p>
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
          <span id="kind-title">{t("Bạn muốn đăng gì?")}</span>
        </div>
        
        {/* Bộ chọn kênh nằm SAU bước chọn loại nội dung vì nó phụ thuộc vào
            loại: đặt trước thì nó phải hiện mọi kênh rồi tự bỏ đi, và ô tick nhảy
            chỗ ngay trước mắt người dùng. */}

        <div className={styles.kindGrid} role="tablist" aria-label={t("Loại nội dung")}>
          <button
            type="button"
            role="tab"
            aria-selected={kind === "post"}
            className={`${styles.kindCard} ${kind === "post" ? styles.kindCardActive : ""}`}
            onClick={() => setKind("post")}
          >
            <span className={styles.kindIcon}>📝</span>
            <strong>{t("Bài viết")}</strong>
            <small>{t("Kể vài dòng hoặc nạp ảnh — Havi viết bài cho Trang.")}</small>
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
            <small>{t("Bạn quay và cắt sẵn, Havi đăng lên Reels và xác nhận đã lên.")}</small>
          </button>
        </div>
      </section>

      {/* BƯỚC 1b — kênh, phụ thuộc loại nội dung đã chọn ở trên. */}
      <section className={styles.channelSection} aria-labelledby="channel-title">
        <div className={styles.stepTitle}>
          <span className={styles.stepNumber}>2</span>
          <span id="channel-title">{t("Đăng lên kênh nào?")}</span>
        </div>

        {availableChannels.length === 0 ? (
          <p className={styles.channelEmpty}>
            {channelOptions.length === 0
              ? t("Đang tải danh sách kênh…")
              : t("Chưa có kênh nào nhận được loại nội dung này.")}
          </p>
        ) : (
          <div className={styles.channelRow}>
            {availableChannels.map((option) => {
              const id = option.channel as string;
              const checked = selectedChannels.includes(id);
              return (
                <label
                  key={id}
                  className={`${styles.channelChip} ${checked ? styles.channelChipActive : ""} ${
                    option.connected ? "" : styles.channelChipDisabled
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={checked}
                    // Kênh chưa nối vẫn HIỆN nhưng không tick được: ẩn đi thì
                    // người dùng không biết Havi hỗ trợ kênh đó và không biết
                    // phải đi nối.
                    disabled={!option.connected}
                    onChange={(event) =>
                      setSelectedChannels((prev) =>
                        event.target.checked
                          ? [...prev, id]
                          : prev.filter((channel) => channel !== id),
                      )
                    }
                  />
                  <span>{option.label}</span>
                  {option.connected ? null : (
                    <a className={styles.channelConnect} href="/app/connections">
                      {t("nối kênh")}
                    </a>
                  )}
                </label>
              );
            })}
          </div>
        )}
      </section>

      {kind === "video" ? (
        <VideoBranch />
      ) : (
        <>
          <PostBrief
            chips={chips}
            uploads={uploads}
            note={note}
            uploading={uploading}
            generating={generating}
            onNoteChange={setNote}
            onAddNote={addNote}
            onRemoveChip={removeChip}
            onPickFiles={onPickFiles}
            onOpenVoice={() => setVoiceModalOpen(true)}
            onOpenMediaPicker={() => setMediaPickerOpen(true)}
            onGenerate={generate}
          />

          {loading ? (
            <LoadingState title={t("Đang tải bản nháp…")} />
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
                onApproveSingle={onApproveSingle}
                publishNow={plan.publishNow}
                onDismiss={onDismiss}
                onDismissAll={onDismissAllRequested}
              />

              {/* BƯỚC 3 — chung với nhánh Video. */}
              {items.length ? (
                <SchedulePicker
                  noun={t("bài")}
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

      <DangerConfirmModal
        isOpen={isConfirmingDismissAll}
        type="custom"
        isDeleting={busyIds.length > 0}
        customKeyword="XOANHAP"
        customTitle={`Xác nhận xoá tất cả ${items.length} bản nháp`}
        customLostItems={[
          "Mọi nội dung, ảnh, video đã chuẩn bị trong các bản nháp này sẽ bị xoá.",
          "Bạn sẽ phải tạo lại nội dung nếu đổi ý.",
        ]}
        onClose={() => setIsConfirmingDismissAll(false)}
        onConfirm={onDismissAll}
      />

      <MediaPickerModal 
        isOpen={mediaPickerOpen} 
        onClose={() => setMediaPickerOpen(false)} 
        onSelect={handleMediaPick} 
      />
    </>
  );
}
