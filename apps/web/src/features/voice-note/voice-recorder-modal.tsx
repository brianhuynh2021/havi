"use client";
import { useLanguage } from "@/lib/i18n/language-context";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { useVoiceRecorder } from "./use-voice-recorder";
import { transcribeVoice } from "./voice-note.api";
import styles from "./voice-recorder-modal.module.css";

type VoiceRecorderModalProps = {
  isOpen: boolean;
  onClose: () => void;
  onInsertNote: (text: string) => void;
  onDirectGenerate: (text: string, audioBase64?: string) => Promise<void>;
};

function formatTimer(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
}

function VoiceRecorderModalContent({
  onClose,
  onInsertNote,
  onDirectGenerate,
}: Omit<VoiceRecorderModalProps, "isOpen">) {
  const {
    t
  } = useLanguage();

  const {
    state,
    recordingTime,
    liveTranscript,
    errorMessage,
    startRecording,
    stopRecording,
    cancelRecording,
  } = useVoiceRecorder();

  const [transcribedText, setTranscribedText] = useState("");
  const [capturedBase64, setCapturedBase64] = useState<string | null>(null);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [transcribeError, setTranscribeError] = useState<string | null>(null);

  useEffect(() => {
    return () => {
      cancelRecording();
    };
  }, [cancelRecording]);

  async function handleToggleRecording() {
    if (state === "recording") {
      try {
        setIsTranscribing(true);
        const { base64, mimeType, transcript } = await stopRecording();
        setCapturedBase64(base64);

        if (transcript) {
          setTranscribedText(transcript);
        }

        // Gọi Backend Gemini Transcriber để có văn bản tiếng Việt chất lượng cao nhất
        const result = await transcribeVoice(base64, mimeType);
        if (result.ok) {
          setTranscribedText(result.data.text);
        } else if (!transcript) {
          setTranscribeError(result.message);
        }
      } catch (err: unknown) {
        const errorObj = err as { message?: string };
        setTranscribeError(errorObj?.message || t("Lỗi xử lý âm thanh"));
      } finally {
        setIsTranscribing(false);
      }
    } else {
      setTranscribedText("");
      setCapturedBase64(null);
      setTranscribeError(null);
      await startRecording();
    }
  }

  async function handleGenerateDirect() {
    const textToUse = transcribedText || liveTranscript;
    if (!textToUse.trim()) return;

    setIsGenerating(true);
    try {
      await onDirectGenerate(textToUse, capturedBase64 || undefined);
      onClose();
    } finally {
      setIsGenerating(false);
    }
  }

  function handleInsert() {
    const textToUse = transcribedText || liveTranscript;
    if (textToUse.trim()) {
      onInsertNote(textToUse.trim());
      onClose();
    }
  }

  const isRecording = state === "recording";
  const hasText = Boolean(transcribedText || liveTranscript);

  return (
    <div className={styles.overlay} onClick={onClose} role="dialog" aria-modal="true">
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <button className={styles.closeButton} onClick={onClose} aria-label={t("Đóng")}>
          ✕
        </button>

        <h2 className={styles.title}>{t("🎙️ Ghi âm ý tưởng bài viết")}</h2>
        <p className={styles.subtitle}>{t("Bạn cứ nói tự nhiên — Havi sẽ viết thành bài đăng Facebook.")}</p>

        {errorMessage || transcribeError ? (
          <div className={styles.errorBanner} role="alert">
            {errorMessage || transcribeError}
          </div>
        ) : null}

        <div className={styles.waveContainer}>
          {isRecording ? (
            <>
              <div className={styles.wavePulse} />
              <div className={styles.wavePulseDelay} />
            </>
          ) : null}
          <button
            type="button"
            className={`${styles.micButton} ${isRecording ? styles.micButtonRecording : ""}`}
            onClick={handleToggleRecording}
            disabled={isTranscribing || isGenerating}
            aria-label={t(isRecording ? "Dừng ghi âm" : "Bắt đầu ghi âm")}
            data-testid="mic-toggle-btn"
          >
            {isRecording ? "⏹️" : "🎙️"}
          </button>
        </div>

        <div className={`${styles.timer} ${isRecording ? styles.timerRecording : ""}`}>
          {isTranscribing
            ? t("⚡ Đang nhận diện giọng nói…")
            : isRecording
            ? t("🔴 Đang thu âm: {value}", { value: formatTimer(recordingTime) })
            : hasText
            ? t("✅ Đã thu âm xong")
            : t("Chạm vào Micro để bắt đầu nói")}
        </div>

        <div className={styles.transcriptBox}>
          <div className={styles.transcriptLabel}>{t("Nội dung đã nhận diện")}</div>
          {transcribedText || liveTranscript ? (
            <p className={styles.transcriptText} data-testid="transcript-text">
              {transcribedText || liveTranscript}
            </p>
          ) : (
            <p className={styles.transcriptPlaceholder}>
              {isRecording
                ? t("Đang lắng nghe…")
                : t("Chưa có nội dung. Bạn chạm nút Micro ở trên để nói nhé.")}
            </p>
          )}
        </div>

        {!hasText && !isRecording ? (
          <div className={styles.suggestions}>
            <p className={styles.suggestionTitle}>{t("💡 Câu nói mẫu gợi ý:")}</p>
            <p className={styles.suggestionItem}>{t(
              "“Hôm nay tiệm em giảm 30% uốn nhuộm phục hồi nhân dịp 2/9, tặng kèm hấp dầu collagen cho khách đặt lịch sớm.”"
            )}</p>
          </div>
        ) : null}

        {hasText && !isRecording ? (
          <div className={styles.actions}>
            <Button
              variant="primary"
              disabled={isGenerating || isTranscribing}
              onClick={handleGenerateDirect}
              data-testid="btn-voice-generate"
            >
              {t(isGenerating ? "⚡ Đang viết bài…" : "Để Havi viết bài từ lời này")}
            </Button>
            <Button
              variant="outline"
              disabled={isGenerating || isTranscribing}
              onClick={handleInsert}
              data-testid="btn-voice-insert"
            >{t("✍️ Chèn vào ô ghi chú")}</Button>
            <Button
              variant="ghost"
              disabled={isGenerating || isTranscribing}
              onClick={handleToggleRecording}
            >{t("🔄 Ghi âm lại câu khác")}</Button>
          </div>
        ) : null}
      </div>
    </div>
  );
}

export function VoiceRecorderModal({
  isOpen,
  ...props
}: VoiceRecorderModalProps) {
  // Không gọi `useLanguage` ở đây: wrapper này chỉ gác `isOpen`, mọi chữ nằm
  // trong `VoiceRecorderModalContent`.
  if (!isOpen) return null;
  return <VoiceRecorderModalContent {...props} />;
}
