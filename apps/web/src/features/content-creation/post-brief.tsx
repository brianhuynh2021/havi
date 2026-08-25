"use client";

/**
 * Phần "kể cho Havi nghe" — ảnh, giọng nói, ghi chú, mục tiêu chiến dịch.
 *
 * Tách khỏi màn chính vì nó là *đầu vào*, còn danh sách bản nháp là *đầu ra*.
 * Hai nửa này thay đổi vì hai lý do khác nhau (thêm cách nhập liệu / đổi cách
 * duyệt bài), nên để chung một file là bảo đảm mỗi lần sửa đều phải đọc cả hai.
 */

import { useRef } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/input";
import type { RawInput } from "./content-creation.api";
import styles from "./content-creation.module.css";

export type RawChip = {
  key: string;
  kind: "photo" | "text";
  label: string;
  input: RawInput;
  previewUrl?: string;
};

export type UploadRow = {
  key: string;
  fileName: string;
  previewUrl: string;
  progress: number;
  status: "uploading" | "complete" | "cancelled" | "failed";
  message?: string;
  assetId?: string;
  controller: AbortController;
};

export type CampaignGoal = {
  id: string;
  icon: string;
  title: string;
  desc: string;
  /** Câu gợi ý nạp thẳng vào ô ghi chú — chủ tiệm sửa lại chứ không phải gõ từ đầu. */
  text: string;
};

/**
 * Mục tiêu chiến dịch, không phải "playbook".
 *
 * Mỗi mục chỉ nạp sẵn một câu gợi ý vào ô ghi chú. Havi không hứa kết quả nào ở
 * đây — hiệu quả thật chỉ đo được sau khi bài đã đăng, nên phần mô tả nói về
 * *nội dung sẽ viết ra*, không nói về doanh thu.
 */
export const CAMPAIGN_GOALS: CampaignGoal[] = [
  {
    id: "offer",
    icon: "🏷️",
    title: "Giới thiệu ưu đãi",
    desc: "Bài nêu rõ ưu đãi, điều kiện áp dụng và cách khách liên hệ.",
    text: "Nêu rõ ưu đãi đang áp dụng, thời hạn và điều kiện thật; cuối bài mời khách nhắn tin để nhân viên xác nhận lịch trống.",
  },
  {
    id: "local",
    icon: "📍",
    title: "Khách quanh khu vực",
    desc: "Bài nhấn vị trí, giờ mở cửa và dịch vụ chính — hợp với tìm kiếm quanh đây.",
    text: "Giới thiệu dịch vụ chính, vị trí và giờ mở cửa của cơ sở, kèm cách đặt lịch nhanh nhất.",
  },
  {
    id: "proof",
    icon: "💬",
    title: "Kể chuyện khách hàng",
    desc: "Bài dựa trên một trường hợp có thật đã làm ở cơ sở.",
    text: "Kể lại một trường hợp khách hàng có thật: vấn đề ban đầu, cơ sở đã xử lý thế nào, kết quả khách nhận được.",
  },
  {
    id: "intro",
    icon: "✨",
    title: "Giới thiệu dịch vụ mới",
    desc: "Bài mô tả dịch vụ hoặc sản phẩm vừa có, kèm mức giá nếu đã chốt.",
    text: "Giới thiệu dịch vụ hoặc sản phẩm mới: dành cho ai, làm trong bao lâu, giá tham khảo nếu đã có.",
  },
];

/**
 * Việc bài viết còn thiếu gì — dạng danh sách kiểm, **không** phải điểm số.
 *
 * Bản trước hiện "Điểm Chuyển Đổi: 87/100" tính bằng vài regex. Con số đó trông
 * như một phép đo nhưng không đo gì cả, và người đọc sẽ tin nó hơn hẳn một gạch
 * đầu dòng. Giữ đúng năm mục kiểm, bỏ con số bịa.
 */
export type BriefCheck = { id: string; label: string; pass: boolean };

export function checkBrief(text: string, hasPhoto: boolean): BriefCheck[] {
  const content = text.toLowerCase();
  return [
    {
      id: "offer",
      label: "Nêu rõ dịch vụ hoặc ưu đãi",
      pass: /(ưu đãi|giảm|tặng|miễn phí|voucher|combo|khóa học|dịch vụ|gói)/i.test(content),
    },
    { id: "proof", label: "Có ảnh thật của cơ sở", pass: hasPhoto },
    {
      id: "price",
      label: "Có mức giá hoặc khoảng giá",
      pass: /(\d+\s*(k|tr|đ|đồng|triệu|nghìn|vnđ|%)|miễn phí|0đ)/i.test(content),
    },
    {
      id: "cta",
      label: "Có cách để khách liên hệ",
      pass: /(inbox|nhắn|đặt lịch|gọi|liên hệ|hotline|sđt|đăng ký|ghé|bình luận|comment)/i.test(
        content,
      ),
    },
    {
      id: "when",
      label: "Có mốc thời gian cụ thể",
      pass: /(tuần này|hôm nay|chỉ còn|hạn|ngày|từ .* đến|cuối tuần|\d+h)/i.test(content),
    },
  ];
}

type PostBriefProps = {
  chips: RawChip[];
  uploads: UploadRow[];
  note: string;
  selectedGoal: string | null;
  uploading: boolean;
  generating: boolean;
  onNoteChange: (value: string) => void;
  onAddNote: () => void;
  onRemoveChip: (key: string) => void;
  onPickFiles: (files: FileList | null) => void;
  onOpenVoice: () => void;
  onSelectGoal: (goal: CampaignGoal) => void;
  onGenerate: () => void;
};

export function PostBrief({
  chips,
  uploads,
  note,
  selectedGoal,
  uploading,
  generating,
  onNoteChange,
  onAddNote,
  onRemoveChip,
  onPickFiles,
  onOpenVoice,
  onSelectGoal,
  onGenerate,
}: PostBriefProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);

  const briefText = [note, ...chips.map((chip) => chip.label)].join(" ");
  const hasPhoto = chips.some((chip) => chip.kind === "photo");
  const showChecks = Boolean(briefText.trim()) || hasPhoto;
  const checks = showChecks ? checkBrief(briefText, hasPhoto) : [];
  const canGenerate = (chips.length > 0 || note.trim().length > 0) && !uploading && !generating;

  return (
    <>
      <section className={styles.playbookSection} aria-labelledby="goal-title">
        <div className={styles.stepTitle}>
          <span className={styles.stepNumber}>1</span>
          <span id="goal-title">Bài này để làm gì?</span>
        </div>
        <div className={styles.playbookGrid}>
          {CAMPAIGN_GOALS.map((goal) => (
            <button
              key={goal.id}
              type="button"
              aria-pressed={selectedGoal === goal.id}
              className={`${styles.playbookCard} ${
                selectedGoal === goal.id ? styles.playbookCardActive : ""
              }`}
              onClick={() => onSelectGoal(goal)}
            >
              <span className={styles.playbookIcon}>{goal.icon}</span>
              <strong>{goal.title}</strong>
              <small>{goal.desc}</small>
            </button>
          ))}
        </div>
      </section>

      <section className={styles.rawSection} aria-labelledby="brief-title">
        <div className={styles.stepTitle}>
          <span className={styles.stepNumber}>2</span>
          <span id="brief-title">Kể cho Havi nghe</span>
        </div>

        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          multiple
          hidden
          data-testid="file-input"
          onChange={(event) => onPickFiles(event.target.files)}
        />
        <input
          ref={cameraInputRef}
          type="file"
          accept="image/*"
          capture="environment"
          hidden
          data-testid="camera-input"
          onChange={(event) => onPickFiles(event.target.files)}
        />

        <div className={styles.rawActions}>
          <Button
            variant="primary"
            disabled={uploading}
            onClick={() => cameraInputRef.current?.click()}
          >
            📸 Chụp ảnh
          </Button>
          <Button
            variant="outline"
            disabled={uploading}
            onClick={() => fileInputRef.current?.click()}
          >
            {uploading ? "Đang tải lên…" : "Chọn ảnh có sẵn"}
          </Button>
          <Button variant="outline" disabled={uploading} onClick={onOpenVoice} data-testid="btn-voice-modal">
            🎙️ Nói thay vì gõ
          </Button>
        </div>

        <div className={styles.noteBox}>
          <label className={styles.noteLabel} htmlFor="raw-note">
            Muốn Havi viết về điều gì?
          </label>
          <Textarea
            id="raw-note"
            rows={3}
            placeholder="Tuần này giảm 20% gói gội đầu thảo dược cho khách quen"
            value={note}
            onChange={(event) => onNoteChange(event.target.value)}
          />
          <Button variant="outline" onClick={onAddNote} disabled={!note.trim()}>
            Thêm ghi chú
          </Button>
        </div>

        {uploads.some((upload) => upload.status === "uploading") ? (
          <ul className={styles.uploadList}>
            {uploads
              .filter((upload) => upload.status === "uploading")
              .map((upload) => (
                <li key={upload.key} className={styles.uploadRow}>
                  <span>{upload.fileName}</span>
                  <span>{upload.progress}%</span>
                </li>
              ))}
          </ul>
        ) : null}

        {chips.length ? (
          <div className={styles.chipRow}>
            {chips.map((chip) => (
              <span key={chip.key} className={styles.chip}>
                <span aria-hidden="true">{chip.kind === "photo" ? "🖼️" : "✍️"}</span>
                {chip.label}
                <button
                  type="button"
                  className={styles.chipRemove}
                  aria-label={`Bỏ ${chip.label}`}
                  onClick={() => onRemoveChip(chip.key)}
                >
                  ×
                </button>
              </span>
            ))}
          </div>
        ) : null}

        {showChecks ? (
          <div className={styles.briefChecks} aria-label="Bài viết còn thiếu gì">
            <p className={styles.briefChecksTitle}>Havi sẽ viết tốt hơn nếu có thêm:</p>
            <ul className={styles.criteriaGrid}>
              {checks.map((check) => (
                <li
                  key={check.id}
                  className={`${styles.criterionItem} ${
                    check.pass ? styles.criterionItemPass : ""
                  }`}
                >
                  <span aria-hidden="true">{check.pass ? "✓" : "○"}</span>
                  <span>{check.label}</span>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </section>

      <div className={styles.generateRow}>
        <Button
          variant="primary"
          scale="large"
          className={styles.heroGenerateBtn}
          onClick={onGenerate}
          disabled={!canGenerate}
        >
          {generating ? "Havi đang viết…" : "Để Havi viết bài"}
        </Button>
        <p className={styles.generateHint}>
          Havi viết bản nháp. Không bài nào lên Trang khi bạn chưa duyệt.
        </p>
      </div>
    </>
  );
}
