"use client";

import React, { useState, useEffect, useCallback } from "react";
import Image from "next/image";
import Link from "next/link";
import styles from "./landing.module.css";

interface VideoDemoModalProps {
  isOpen: boolean;
  onClose: () => void;
  lang?: "VN" | "EN";
}

interface Chapter {
  id: number;
  timeSec: number;
  timeLabel: string;
  title: string;
  desc: string;
  channel: string;
}

const CHAPTERS: Chapter[] = [
  {
    id: 1,
    timeSec: 0,
    timeLabel: "00:00 - 00:18",
    title: "1. Chụp ảnh tiệm thật & Quét nhận diện AI",
    desc: "Chủ tiệm nạp tư liệu cơ sở thật và thông tin đã kiểm chứng để Havi dùng làm ngữ cảnh tạo bản nháp.",
    channel: "📸 HAVI VISION AI",
  },
  {
    id: 2,
    timeSec: 18,
    timeLabel: "00:18 - 00:40",
    title: "2. Sinh bản nháp Facebook & kịch bản video 9:16",
    desc: "AI tạo bản nháp để người dùng kiểm tra. Facebook Beta có thể xuất bản qua API khi đủ quyền; các kênh khác chưa được mô tả như auto-publish.",
    channel: "⚡ DRAFT ENGINE",
  },
  {
    id: 3,
    timeSec: 40,
    timeLabel: "00:40 - 01:00",
    title: "3. Theo dõi hội thoại và trạng thái xử lý",
    desc: "Havi gom hội thoại từ các kênh được hỗ trợ, cho phép chỉnh bản nháp rồi gửi hoặc bỏ qua.",
    channel: "🔔 SOCIAL OPERATIONS",
  },
];

export function VideoDemoModal({
  isOpen,
  onClose,
  lang = "VN",
}: VideoDemoModalProps) {
  const [isPlaying, setIsPlaying] = useState<boolean>(true);
  const [currentSec, setCurrentSec] = useState<number>(0);
  const [activeChapterIdx, setActiveChapterIdx] = useState<number>(0);

  const totalDurationSec = 60;

  // Handle ESC key to close
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    },
    [onClose],
  );

  useEffect(() => {
    if (isOpen) {
      window.addEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "hidden";
    }
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "";
    };
  }, [isOpen, handleKeyDown]);

  // Smooth continuous video timer (updates smoothly every 100ms)
  useEffect(() => {
    if (!isOpen || !isPlaying) return;

    const timer = setInterval(() => {
      setCurrentSec((prev) => {
        const next = prev + 0.15;
        if (next >= totalDurationSec) {
          setActiveChapterIdx(0);
          return 0;
        }
        if (next < 18) setActiveChapterIdx(0);
        else if (next < 40) setActiveChapterIdx(1);
        else setActiveChapterIdx(2);
        return next;
      });
    }, 100);

    return () => clearInterval(timer);
  }, [isOpen, isPlaying]);

  if (!isOpen) return null;

  const currentChapter = CHAPTERS[activeChapterIdx];
  const progressPercent = Math.min(100, (currentSec / totalDurationSec) * 100);

  const formatTime = (sec: number) => {
    const totalS = Math.floor(sec);
    const m = Math.floor(totalS / 60)
      .toString()
      .padStart(2, "0");
    const s = (totalS % 60).toString().padStart(2, "0");
    return `${m}:${s}`;
  };

  const jumpToChapter = (chapterIdx: number) => {
    setActiveChapterIdx(chapterIdx);
    setCurrentSec(CHAPTERS[chapterIdx].timeSec);
  };

  return (
    <div
      className={styles.modalOverlay}
      onClick={onClose}
      data-testid="video-demo-modal-backdrop"
    >
      <div
        className={styles.videoModalContent}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label="Video trình diễn thực chiến Havi 60 giây"
      >
        {/* Modal Header */}
        <div className={styles.videoModalHeader}>
          <div className={styles.videoModalTitleBox}>
            <span className={styles.videoBadge}>🎥 DEMO THỰC CHIẾN 60S</span>
            <h3 className={styles.videoModalTitle}>
              Xem Havi Quản Trị Social Media Đa Kênh
            </h3>
          </div>
          <button
            type="button"
            className={styles.videoModalCloseBtn}
            onClick={onClose}
            aria-label="Đóng video"
          >
            ✕
          </button>
        </div>

        {/* Video Player Display Container */}
        <div className={styles.playerStage}>
          {/* Main Visual Frame */}
          <div className={styles.playerScreen}>
            {/* Overlay Chapter Tag */}
            <div className={styles.playerChapterOverlay}>
              <span className={styles.playerChannelPill}>
                {currentChapter.channel}
              </span>
              <span className={styles.playerTimestampPill}>
                {formatTime(currentSec)} / {formatTime(totalDurationSec)}
              </span>
            </div>

            {/* Simulated live visual based on chapter */}
            {activeChapterIdx === 0 && (
              <div className={styles.playerVisualScene}>
                <div className={styles.scenePhotoContainer}>
                  <Image
                    src="https://images.unsplash.com/photo-1540555700478-4be289fbecef?w=1000&auto=format&fit=crop&q=80"
                    alt="Cơ sở Spa thẩm mỹ thực tế"
                    width={520}
                    height={300}
                    className={styles.scenePhotoImg}
                    unoptimized
                  />
                  <div className={styles.sceneLaserScan} />
                </div>
                <div className={styles.sceneMetaCard}>
                  <div className={styles.sceneTagGreen}>✓ Tải ảnh tiệm hoàn tất</div>
                  <h4 className={styles.sceneCardHeading}>Viện Thẩm Mỹ &amp; Spa Lan Anh</h4>
                  <p className={styles.sceneCardDesc}>
                    AI nhận diện gói dịch vụ: Trị mụn thâm &amp; gội dưỡng sinh 450k.<br />
                    Tự động lên cấu trúc kịch bản video TikTok 9:16 và bài Fanpage.
                  </p>
                </div>
              </div>
            )}

            {activeChapterIdx === 1 && (
              <div className={styles.playerVisualScene}>
                <div className={styles.sceneMultiCardList}>
                  <div className={styles.scenePostCard}>
                    <div className={styles.sceneCardHead}>📘 Fanpage Facebook</div>
                    <p className={styles.sceneCardText}>
                      &ldquo;Da căng bóng, sạch mụn chỉ sau 1 liệu trình vi kim... Tặng 30 suất soi da tuần này!&rdquo;
                    </p>
                  </div>
                  <div className={`${styles.scenePostCard} ${styles.scenePostCardTiktok}`}>
                    <div className={styles.sceneCardHead}>🎵 TikTok Hook 3s</div>
                    <p className={styles.sceneCardText}>
                      🔥 <strong>&ldquo;3 sai lầm rửa mặt khiến mụn ẩn tái lại mà 90% chị em không ngờ tới...&rdquo;</strong>
                    </p>
                  </div>
                </div>
                <div className={styles.sceneMetaCard}>
                  <div className={styles.sceneTagGreen}>✓ Sẵn sàng duyệt 1-chạm</div>
                  <h4 className={styles.sceneCardHeading}>Đã tạo xong 3 kênh trong 5s</h4>
                  <p className={styles.sceneCardDesc}>
                    Nội dung đúng bảng giá tiệm, không bao giờ tự ý đăng khi chủ tiệm chưa nhấn nút duyệt.
                  </p>
                </div>
              </div>
            )}

            {activeChapterIdx === 2 && (
              <div className={styles.playerVisualScene}>
                <div className={styles.sceneTgAlertCard}>
                  <div className={styles.sceneTgTop}>
                    <span>💬 Hộp thư chung</span>
                    <span className={styles.scenePulseLive}>Mới</span>
                  </div>
                  <div className={styles.sceneTgContent}>
                    <div>🔔 <strong>CÓ MỘT HỘI THOẠI CHƯA XỬ LÝ</strong></div>
                    <div>👤 <strong>Người gửi:</strong> Khách Facebook</div>
                    <div>💬 <strong>Nội dung:</strong> Cho mình xin thông tin liệu trình</div>
                    <div className={styles.sceneTgBtnRow}>
                      <span className={styles.sceneBtnCall}>[ MỞ HỘI THOẠI ]</span>
                      <span className={styles.sceneBtnZalo}>[ KIỂM TRA BẢN NHÁP ]</span>
                    </div>
                  </div>
                </div>
                <div className={styles.sceneMetaCard}>
                  <div className={styles.sceneTagGreen}>✓ Minh hoạ xử lý hội thoại</div>
                  <h4 className={styles.sceneCardHeading}>Theo dõi inquiry trong một hộp thư</h4>
                  <p className={styles.sceneCardDesc}>
                    Đây là kịch bản minh hoạ. Chỉ FAQ đã duyệt mới được tự phản hồi; các trường hợp khác chờ người dùng duyệt và gửi.
                  </p>
                </div>
              </div>
            )}

            {/* Play/Pause toggle button */}
            <button
              type="button"
              className={styles.playerPlayToggleBtn}
              onClick={() => setIsPlaying(!isPlaying)}
              aria-label={isPlaying ? "Tạm dừng video" : "Phát video"}
            >
              {isPlaying ? "⏸" : "▶"}
            </button>
          </div>

          {/* Timeline Progress Bar with Rocket Beam */}
          <div
            className={styles.timelineTrack}
            onClick={(e) => {
              const rect = e.currentTarget.getBoundingClientRect();
              const clickX = e.clientX - rect.left;
              const ratio = Math.max(0, Math.min(1, clickX / rect.width));
              const newSec = Math.round(ratio * totalDurationSec);
              setCurrentSec(newSec);
              if (newSec < 18) setActiveChapterIdx(0);
              else if (newSec < 40) setActiveChapterIdx(1);
              else setActiveChapterIdx(2);
            }}
          >
            <div
              className={styles.timelineFill}
              style={{ width: `${progressPercent}%` }}
            >
              <div className={styles.timelineRocketHead} />
            </div>
          </div>

          {/* Chapters Navigation Tabs */}
          <div className={styles.chaptersGrid}>
            {CHAPTERS.map((chap, idx) => (
              <button
                key={chap.id}
                type="button"
                className={`${styles.chapterTabItem} ${activeChapterIdx === idx ? styles.chapterTabActive : ""}`}
                onClick={() => jumpToChapter(idx)}
              >
                <div className={styles.chapterTabTime}>{chap.timeLabel}</div>
                <div className={styles.chapterTabTitle}>{chap.title}</div>
              </button>
            ))}
          </div>
        </div>

        {/* Modal Bottom CTA Footer */}
        <div className={styles.videoModalFooter}>
          <div className={styles.videoModalFooterLeft}>
            ⭐️ <strong>Nguyên tắc kiểm soát:</strong> Bạn là người duyệt cuối cùng trước khi đăng.
          </div>
          <div className={styles.videoModalFooterRight}>
            <Link
              href="/signup"
              className={styles.videoPrimaryCta}
              onClick={onClose}
            >
              {lang === "VN"
                ? "Bắt đầu dùng thử 7 ngày miễn phí ➔"
                : "Start 7-Day Free Trial ➔"}
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
