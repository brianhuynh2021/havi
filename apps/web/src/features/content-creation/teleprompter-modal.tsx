import React, { useState, useEffect, useRef } from "react";
import styles from "./teleprompter.module.css";

export interface TeleprompterModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  hookText: string;
  cameraAngle: string;
  scriptText: string;
  onUploadVideo: (file: File) => void;
}

export function TeleprompterModal({
  isOpen,
  onClose,
  title,
  hookText,
  cameraAngle,
  scriptText,
  onUploadVideo,
}: TeleprompterModalProps) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [countdown, setCountdown] = useState<number | null>(null);
  const [fontSize, setFontSize] = useState<number>(24); // px
  const [speed, setSpeed] = useState<number>(1.0); // 0.7x, 1.0x, 1.4x
  const [isMirrored, setIsMirrored] = useState(false);

  const prompterBodyRef = useRef<HTMLDivElement>(null);
  const scrollIntervalRef = useRef<number | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Screen Wake Lock API để màn hình điện thoại không bị tắt khi đọc
  useEffect(() => {
    let wakeLock: { release: () => Promise<void> } | null = null;
    const nav = navigator as Navigator & {
      wakeLock?: { request: (type: string) => Promise<{ release: () => Promise<void> }> };
    };
    if (isOpen && nav.wakeLock) {
      nav.wakeLock
        .request("screen")
        .then((lock) => {
          wakeLock = lock;
        })
        .catch(() => {});
    }
    return () => {
      if (wakeLock) {
        wakeLock.release().catch(() => {});
      }
    };
  }, [isOpen]);

  useEffect(() => {
    if (isPlaying) {
      const scrollStep = 1.2 * speed;
      scrollIntervalRef.current = window.setInterval(() => {
        if (prompterBodyRef.current) {
          prompterBodyRef.current.scrollTop += scrollStep;
          // Nếu chạm đáy thì dừng
          if (
            prompterBodyRef.current.scrollTop + prompterBodyRef.current.clientHeight >=
            prompterBodyRef.current.scrollHeight - 10
          ) {
            setIsPlaying(false);
          }
        }
      }, 30);
    } else {
      if (scrollIntervalRef.current) clearInterval(scrollIntervalRef.current);
    }
    return () => {
      if (scrollIntervalRef.current) clearInterval(scrollIntervalRef.current);
    };
  }, [isPlaying, speed]);

  function handleStartPlay() {
    if (isPlaying) {
      setIsPlaying(false);
      return;
    }
    // Bắt đầu đếm ngược 3s
    setCountdown(3);
    const interval = setInterval(() => {
      setCountdown((prev) => {
        if (prev === null || prev <= 1) {
          clearInterval(interval);
          setCountdown(null);
          setIsPlaying(true);
          return null;
        }
        return prev - 1;
      });
    }, 900);
  }

  function handleResetScroll() {
    setIsPlaying(false);
    if (prompterBodyRef.current) {
      prompterBodyRef.current.scrollTo({ top: 0, behavior: "smooth" });
    }
  }

  function handleClose() {
    setIsPlaying(false);
    setCountdown(null);
    if (scrollIntervalRef.current) clearInterval(scrollIntervalRef.current);
    onClose();
  }

  if (!isOpen) return null;

  return (
    <div
      className={styles.teleprompterOverlay}
      role="dialog"
      aria-modal="true"
      aria-label="Máy nhắc chữ quay video 30s"
    >
      {/* Top Header */}
      <header className={styles.topHeader}>
        <div className={styles.topInfo}>
          <span className={styles.prompterBadge}>Studio Teleprompter</span>
          <h2 className={styles.prompterTitle}>{title || "Lời thoại kịch bản video"}</h2>
        </div>

        <div className={styles.topControls}>
          <button
            type="button"
            className={styles.toolBtn}
            onClick={() => setFontSize((s) => Math.max(16, s - 3))}
            title="Giảm cỡ chữ"
          >
            A-
          </button>
          <button
            type="button"
            className={styles.toolBtn}
            onClick={() => setFontSize((s) => Math.min(42, s + 3))}
            title="Tăng cỡ chữ"
          >
            A+
          </button>
          <button
            type="button"
            className={styles.toolBtn}
            onClick={() => setIsMirrored((m) => !m)}
            style={{ color: isMirrored ? "#a855f7" : "#f1f5f9" }}
            title="Chế độ lật gương (khi nhìn camera trước)"
          >
            🪞 {isMirrored ? "Lật gương BẬT" : "Lật gương"}
          </button>
          <button
            type="button"
            className={styles.closeBtn}
            onClick={handleClose}
            aria-label="Đóng máy nhắc chữ"
          >
            ✕
          </button>
        </div>
      </header>

      {/* Main Prompter Body */}
      <main
        ref={prompterBodyRef}
        className={styles.prompterBody}
        style={{ transform: isMirrored ? "scaleX(-1)" : "none" }}
      >
        <div className={styles.scriptWrapper}>
          {/* Camera Cue */}
          <div className={styles.cameraCueCard}>
            <span style={{ fontSize: "20px" }}>📹</span>
            <span>
              <strong>Góc máy gợi ý:</strong> {cameraAngle || "Cầm điện thoại quay cận cảnh thao tác thực tế tại tiệm."}
            </span>
          </div>

          {/* Hook 3s Card */}
          <div className={styles.hookCard}>
            <div className={styles.hookLabel}>🎯 3 Giây Đầu • Nói To &amp; Dứt Khoát</div>
            <div className={styles.hookText} style={{ fontSize: `${fontSize * 1.25}px` }}>
              &ldquo;{hookText || "BÍ QUYẾT TỰ HỌC & LÀM CHỦ CÔNG NGHỆ THỰC CHIẾN"}&rdquo;
            </div>
          </div>

          {/* Main Dialogue Card */}
          <div className={styles.dialogueCard}>
            <div className={styles.dialogueLabel}>💬 Lời Thoại Chính (Đọc 15–20s)</div>
            <div className={styles.dialogueText} style={{ fontSize: `${fontSize}px` }}>
              {scriptText}
            </div>
          </div>
        </div>
      </main>

      {/* Countdown Overlay */}
      {countdown !== null ? (
        <div className={styles.countdownOverlay}>
          <div className={styles.countdownNumber}>{countdown}</div>
          <div className={styles.countdownHint}>Chuẩn bị nhìn vào Camera và đọc...</div>
        </div>
      ) : null}

      {/* Bottom Floating Controls */}
      <footer className={styles.bottomControlBar}>
        <div className={styles.controlLeft}>
          <button
            type="button"
            className={styles.toolBtn}
            onClick={() => setSpeed((s) => (s === 0.7 ? 1.0 : s === 1.0 ? 1.4 : 0.7))}
          >
            ⚡ Tốc độ: {speed === 0.7 ? "Chậm (0.7x)" : speed === 1.0 ? "Vừa (1.0x)" : "Nhanh (1.4x)"}
          </button>
          <button
            type="button"
            className={styles.toolBtn}
            onClick={handleResetScroll}
          >
            🔄 Cuộn Lại Đầu
          </button>
        </div>

        <div className={styles.controlCenter}>
          <button
            type="button"
            className={`${styles.playBtn} ${isPlaying ? styles.pauseBtn : ""}`}
            onClick={handleStartPlay}
          >
            {isPlaying ? "⏸️ Tạm Dừng" : "▶️ Bắt Đầu Cuộn Chữ (Đếm 3s)"}
          </button>
        </div>

        <div className={styles.controlRight}>
          <input
            ref={fileInputRef}
            type="file"
            accept="video/mp4,video/quicktime,video/webm"
            style={{ display: "none" }}
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) {
                onUploadVideo(file);
                onClose();
              }
            }}
          />
          <button
            type="button"
            className={styles.uploadFinishBtn}
            onClick={() => fileInputRef.current?.click()}
          >
            📤 Quay Xong • Tải Clip Lên
          </button>
        </div>
      </footer>
    </div>
  );
}
