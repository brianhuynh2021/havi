"use client";

/**
 * "Tôi tự viết" — bài đã hoàn chỉnh, Havi không sửa một chữ.
 *
 * Vì sao có màn này
 * -----------------
 * Đường duy nhất tạo bài trước đây là nút "Để Havi viết bài", và nó luôn gọi LLM.
 * Người viết sẵn một bài ở nơi khác rồi dán vào thì phải nhờ Havi viết một bản
 * không ai cần, tốn quota, rồi ghi đè bài của mình lên.
 *
 * Ảnh và clip nằm ngay ở đây, không phải đi vòng
 * ----------------------------------------------
 * Bài viết sẵn gần như luôn đi kèm ảnh của chính người viết. Bắt họ sang tab khác
 * để nạp ảnh rồi quay lại là chia một việc thành hai màn hình, và màn kia là
 * "kể cho Havi nghe" — nơi ảnh được hiểu là *gợi ý cho AI*, không phải ảnh sẽ
 * đăng. Nên upload và Thư viện đều mở được tại chỗ.
 *
 * Khung xem trước cố tình hiện **xấu như thật**
 * ---------------------------------------------
 * Facebook không hiểu Markdown và cắt bài sau khoảng 800 ký tự. Một khung xem
 * trước render `**đậm**` thành chữ đậm là đang nói dối người dùng về kết quả — họ
 * duyệt một thứ và khách nhìn thấy một thứ khác. Nên ở đây chữ được hiện đúng
 * như Facebook sẽ hiện: nguyên ký hiệu, và cắt ở chỗ Facebook cắt.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { MediaPickerModal } from "@/features/media/media-picker-modal";
import type { MediaAsset as PickerAsset } from "@/features/media/media.api";
import { useLanguage } from "@/lib/i18n/language-context";
import styles from "./content-creation.module.css";
import {
  createOwnItem,
  previewContent,
  uploadMedia,
  type Channel,
  type ContentItem,
  type ContentPreview,
} from "./content-creation.api";

type OwnPostComposerProps = {
  channel: Channel;
  onCreated: (item: ContentItem) => void;
};

/** Ảnh/clip đang gắn vào bài. `url` để xem trước, `id` để gửi lên API. */
type AttachedMedia = {
  id: string;
  url: string;
  kind: "image" | "video";
  fileName: string;
};

/** Xem trước chờ người dùng ngừng gõ — mỗi ký tự một request là vô ích. */
const PREVIEW_DEBOUNCE_MS = 400;

export function OwnPostComposer({ channel, onCreated }: OwnPostComposerProps) {
  const { t } = useLanguage();
  const [text, setText] = useState("");
  const [media, setMedia] = useState<AttachedMedia | null>(null);
  const [preview, setPreview] = useState<ContentPreview | null>(null);
  const [expanded, setExpanded] = useState(false);
  const [busy, setBusy] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pickerOpen, setPickerOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!text.trim()) {
      setPreview(null);
      return;
    }
    const timer = setTimeout(async () => {
      const result = await previewContent(text, channel, media?.id);
      if (result.ok) setPreview(result.data);
    }, PREVIEW_DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [text, channel, media?.id]);

  async function onPickFile(files: FileList | null) {
    const file = files?.[0];
    if (!file) return;
    setUploading(true);
    setError(null);
    const result = await uploadMedia(file);
    setUploading(false);
    if (!result.ok) {
      setError(result.message);
      return;
    }
    setMedia({
      id: result.data.id,
      url: result.data.url,
      kind: result.data.type === "video" ? "video" : "image",
      fileName: result.data.filename,
    });
  }

  function onPickFromLibrary(asset: PickerAsset) {
    setMedia({
      id: asset.id,
      url: asset.url,
      kind: asset.type === "video" ? "video" : "image",
      fileName: asset.filename,
    });
    setPickerOpen(false);
  }

  const onSubmit = useCallback(async () => {
    setBusy(true);
    setError(null);
    const result = await createOwnItem(text, channel, media?.id);
    setBusy(false);
    if (!result.ok) {
      setError(result.message);
      return;
    }
    setText("");
    setMedia(null);
    setPreview(null);
    onCreated(result.data);
  }, [text, channel, media?.id, onCreated]);

  // Cắt đúng chỗ Facebook cắt. Phần sau vẫn giữ để nút "Xem thêm" mở ra được —
  // đó là lý do backend trả cả bài kèm `truncate_at` thay vì chuỗi đã cắt.
  const cut = preview?.truncate_at ?? null;
  const shown = cut !== null && !expanded ? preview!.text.slice(0, cut) : preview?.text ?? "";
  const hidden = cut !== null && !expanded;

  return (
    <section className={styles.ownComposer} aria-labelledby="own-post-title">
      <h3 className={styles.ownTitle} id="own-post-title">
        {t("Bài tôi tự viết")}
      </h3>
      <p className={styles.ownHint}>
        {t("Havi không sửa chữ nào. Dán bài vào, chèn ảnh hoặc clip, xem trước rồi đưa vào hàng chờ duyệt.")}
      </p>

      <label className={styles.ownLabel} htmlFor="own-post-text">
        {t("Nội dung bài")}
      </label>
      <textarea
        id="own-post-text"
        className={styles.ownTextarea}
        value={text}
        onChange={(event) => setText(event.target.value)}
        rows={10}
        placeholder={t("Dán bài đã viết sẵn vào đây…")}
      />

      <input
        ref={fileInputRef}
        type="file"
        accept="image/*,video/*"
        hidden
        data-testid="own-file-input"
        onChange={(event) => onPickFile(event.target.files)}
      />

      <div className={styles.ownMediaActions}>
        <Button
          variant="outline"
          disabled={uploading || busy}
          onClick={() => fileInputRef.current?.click()}
        >
          {uploading ? t("Đang tải lên…") : t("🖼️ Chèn ảnh / clip")}
        </Button>
        <Button
          variant="outline"
          disabled={uploading || busy}
          onClick={() => setPickerOpen(true)}
        >
          {t("📂 Lấy từ Thư viện")}
        </Button>
        {media ? (
          <button
            type="button"
            className={styles.ownRemoveMedia}
            onClick={() => setMedia(null)}
            disabled={busy}
          >
            {t("Bỏ {name}", { name: media.fileName })}
          </button>
        ) : null}
      </div>

      {preview ? (
        <>
          {(preview.warnings ?? []).length > 0 ? (
            <ul className={styles.ownWarnings} aria-label={t("Cảnh báo trước khi đăng")}>
              {(preview.warnings ?? []).map((warning) => (
                <li key={warning.code} className={styles.ownWarning}>
                  ⚠️ {warning.message}
                </li>
              ))}
            </ul>
          ) : null}

          <div className={styles.fbPreview}>
            <p className={styles.fbPreviewCaption}>
              {t("Trên Facebook sẽ hiện như thế này")}
            </p>
            <div className={styles.fbCard}>
              {media ? (
                <div className={styles.fbImageWrap}>
                  {media.kind === "video" ? (
                    <video className={styles.fbImage} src={media.url} controls />
                  ) : (
                    /* `<img>` chứ không phải `next/image`: host media đổi theo môi
                       trường (MinIO ở local, object storage khi deploy) nên không
                       khai báo trước được trong `remotePatterns`. `draft-list` đã
                       dùng cùng cách. */
                    /* eslint-disable-next-line @next/next/no-img-element */
                    <img className={styles.fbImage} src={media.url} alt="" />
                  )}
                </div>
              ) : null}
              {/* `white-space: pre-wrap` giữ đúng xuống dòng người dùng gõ, và chữ
                  đi ra nguyên văn — không render Markdown, vì Facebook cũng không. */}
              <p className={styles.fbText}>
                {shown}
                {hidden ? <span className={styles.fbEllipsis}>…</span> : null}
              </p>
              {cut !== null ? (
                <button
                  type="button"
                  className={styles.fbSeeMore}
                  onClick={() => setExpanded((prev) => !prev)}
                >
                  {expanded ? t("Thu gọn") : t("Xem thêm")}
                </button>
              ) : null}
            </div>
            <p className={styles.fbMeta}>
              {t("{count} ký tự", { count: preview.char_count })}
            </p>
          </div>
        </>
      ) : null}

      {error ? <p className={styles.ownError}>{error}</p> : null}

      <Button variant="primary" onClick={onSubmit} disabled={busy || uploading || !text.trim()}>
        {busy ? t("Đang lưu…") : t("Đưa vào hàng chờ duyệt")}
      </Button>

      <MediaPickerModal
        isOpen={pickerOpen}
        onClose={() => setPickerOpen(false)}
        onSelect={onPickFromLibrary}
      />
    </section>
  );
}
