"use client";

import React, { useState, useEffect } from "react";
import Image from "next/image";
import { industryScenarios } from "./landing.content";
import styles from "./landing.module.css";

interface HeroCinematicShowcaseProps {
  onOpenVideoModal?: () => void;
  lang?: "VN" | "EN";
}

export function HeroCinematicShowcase({
  onOpenVideoModal,
  lang = "VN",
}: HeroCinematicShowcaseProps) {
  const [activeIndustryIdx, setActiveIndustryIdx] = useState<number>(0);
  const [activeStep, setActiveStep] = useState<number>(0);
  const [isHovered, setIsHovered] = useState<boolean>(false);

  // Auto-advance step every 3.8 seconds unless user is interacting/hovering
  useEffect(() => {
    if (isHovered) return;
    const interval = setInterval(() => {
      setActiveStep((prev) => (prev + 1) % 3);
    }, 3800);
    return () => clearInterval(interval);
  }, [isHovered]);

  const currentScenario =
    industryScenarios[activeIndustryIdx] || industryScenarios[0];

  return (
    <div
      className={styles.cinematicWrapper}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      data-testid="hero-cinematic-showcase"
    >
      {/* Ambient background glow */}
      <div className={styles.cinematicGlow} />

      {/* Main 3D Floating Stage */}
      <div className={styles.cinematicCard3D}>
        {/* Top Control Bar with 3-step timeline pills */}
        <div className={styles.showcaseTopBar}>
          <div className={styles.showcaseMacDots}>
            <span className={styles.macDotRed} />
            <span className={styles.macDotYellow} />
            <span className={styles.macDotGreen} />
            <span className={styles.showcaseLiveBadge}>
              <span className={styles.showcasePulseDot} />
              {lang === "VN" ? "LIVE AI PIPELINE" : "LIVE AI PIPELINE"}
            </span>
          </div>

          {/* Stepper Tabs */}
          <div className={styles.showcaseStepper}>
            <button
              type="button"
              className={`${styles.stepPill} ${activeStep === 0 ? styles.stepPillActive : ""}`}
              onClick={() => setActiveStep(0)}
              aria-label="Bước 1: Chụp ảnh tiệm"
            >
              <span className={styles.stepNum}>1</span>
              <span>{lang === "VN" ? "Chụp Ảnh Tiệm" : "Snap Photo"}</span>
            </button>
            <button
              type="button"
              className={`${styles.stepPill} ${activeStep === 1 ? styles.stepPillActive : ""}`}
              onClick={() => setActiveStep(1)}
              aria-label="Bước 2: AI Sinh Đa Kênh"
            >
              <span className={styles.stepNum}>2</span>
              <span>{lang === "VN" ? "AI Sinh Đa Kênh" : "Multi-channel AI"}</span>
            </button>
            <button
              type="button"
              className={`${styles.stepPill} ${activeStep === 2 ? styles.stepPillActive : ""}`}
              onClick={() => setActiveStep(2)}
              aria-label="Bước 3: Bắn Lead Telegram"
            >
              <span className={styles.stepNum}>3</span>
              <span>{lang === "VN" ? "Bắn Lead Telegram" : "Instant Telegram Lead"}</span>
            </button>
          </div>

          {/* Play Video CTA Button */}
          {onOpenVideoModal && (
            <button
              type="button"
              className={styles.watchVideoBtn}
              onClick={onOpenVideoModal}
            >
              <span className={styles.watchPlayIcon}>▶</span>
              <span>{lang === "VN" ? "Xem Video 60s" : "Watch 60s Tour"}</span>
            </button>
          )}
        </div>

        {/* Industry Selector Pills Bar */}
        <div className={styles.showcaseIndustryBar}>
          <span className={styles.industryBarLabel}>
            {lang === "VN" ? "Chọn mô hình tiệm:" : "Select your business:"}
          </span>
          <div className={styles.industryPillsList}>
            {industryScenarios.map((sc, idx) => (
              <button
                key={sc.name}
                type="button"
                className={`${styles.industryPillBtn} ${activeIndustryIdx === idx ? styles.industryPillBtnActive : ""}`}
                onClick={() => setActiveIndustryIdx(idx)}
              >
                <span className={styles.industryTag}>{sc.badge}</span>
                <span className={styles.industryName}>{sc.name}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Dynamic Display Screen */}
        <div className={styles.showcaseScreen}>
          {/* STEP 1: Photo Upload & Holographic Scanner */}
          {activeStep === 0 && (
            <div className={styles.stepContentSlide} data-testid="step-content-0">
              <div className={styles.scanStageGrid}>
                {/* Left: Photo with laser scan beam */}
                <div className={styles.scanPhotoBox}>
                  <Image
                    src={currentScenario.image}
                    alt={currentScenario.name}
                    width={400}
                    height={260}
                    className={styles.scanPhotoImg}
                    unoptimized
                  />
                  <div className={styles.laserBeam} />
                  <div className={styles.scanOverlayBadge}>
                    <span>📷 Ảnh Chụp Tiệm Thật</span>
                  </div>
                </div>

                {/* Right: AI OCR & Feature Extraction */}
                <div className={styles.scanAnalysisBox}>
                  <div className={styles.scanAnalysisHeader}>
                    <span className={styles.aiTagBadge}>✨ HAVI VISION AI 2.0</span>
                    <span className={styles.scanSpeed}>0.34 giây</span>
                  </div>
                  <h4 className={styles.scanAnalysisTitle}>
                    Đã nhận diện bối cảnh &amp; dịch vụ tiệm
                  </h4>
                  <ul className={styles.scanTagsList}>
                    <li className={styles.scanTagItem}>
                      <span className={styles.scanCheckIcon}>✓</span>
                      <span>Mô hình: <strong>{currentScenario.name}</strong></span>
                    </li>
                    <li className={styles.scanTagItem}>
                      <span className={styles.scanCheckIcon}>✓</span>
                      <span>Bối cảnh: <strong>{currentScenario.rawInput}</strong></span>
                    </li>
                    <li className={styles.scanTagItem}>
                      <span className={styles.scanCheckIcon}>✓</span>
                      <span>Kênh xuất: <strong>Facebook, TikTok 9:16 Hook 3s, Google Maps, Trực Inbox</strong></span>
                    </li>
                    <li className={styles.scanTagItem}>
                      <span className={styles.scanCheckIcon}>✓</span>
                      <span>Giọng văn: <strong>Thuần Việt, thân thiện, chốt lịch hẹn tư vấn</strong></span>
                    </li>
                  </ul>
                  <div className={styles.scanNextHint}>
                    Tự động chuyển dữ liệu sang bộ sinh nội dung đa kênh...
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* STEP 2: Multi-Channel Output (Facebook + TikTok Hook + Google Maps) */}
          {activeStep === 1 && (
            <div className={styles.stepContentSlide} data-testid="step-content-1">
              <div className={styles.multiChannelGrid}>
                {/* Channel 1: Facebook */}
                <div className={styles.channelPreviewCard}>
                  <div className={styles.channelHeaderFb}>
                    <span>📘 Facebook Fanpage</span>
                    <span className={styles.channelBadgeGreen}>Sẵn sàng</span>
                  </div>
                  <div className={styles.channelCardBody}>
                    <p className={styles.channelSnippet}>
                      {currentScenario.tabs.facebook.content}
                    </p>
                    <div className={styles.channelMeta}>
                      <span>⏰ Giờ vàng: 19:30</span>
                      <span>🏷 #HaviAI #Duyet1Cham</span>
                    </div>
                  </div>
                </div>

                {/* Channel 2: TikTok 9:16 Hook 3s */}
                <div className={`${styles.channelPreviewCard} ${styles.channelCardTiktok}`}>
                  <div className={styles.channelHeaderTiktok}>
                    <span>🎵 TikTok Video 9:16</span>
                    <span className={styles.channelBadgeHook}>🔥 Hook 3s</span>
                  </div>
                  <div className={styles.channelCardBody}>
                    <div className={styles.hookCalloutBox}>
                      ⚡ <strong>&ldquo;{currentScenario.tabs.video.hook}&rdquo;</strong>
                    </div>
                    <p className={styles.channelSnippetTiktok}>
                      {currentScenario.tabs.video.script}
                    </p>
                  </div>
                </div>

                {/* Channel 3: Google Maps SEO */}
                <div className={styles.channelPreviewCard}>
                  <div className={styles.channelHeaderMaps}>
                    <span>📍 Google Business SEO</span>
                    <span className={styles.channelBadgeGreen}>Top Local</span>
                  </div>
                  <div className={styles.channelCardBody}>
                    <p className={styles.channelSnippet}>
                      {currentScenario.tabs.maps.content}
                    </p>
                    <div className={styles.channelMeta}>
                      <span>⭐ 4.9/5 Đánh giá</span>
                      <span>📞 Nút gọi trực tiếp</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* STEP 3: Telegram Hot Lead Radar Alert (< 3s) */}
          {activeStep === 2 && (
            <div className={styles.stepContentSlide} data-testid="step-content-2">
              <div className={styles.telegramRadarStage}>
                <div className={styles.telegramCardBox}>
                  {/* Telegram header */}
                  <div className={styles.tgHeader}>
                    <div className={styles.tgHeaderLeft}>
                      <span className={styles.tgIcon}>✈️</span>
                      <div>
                        <div className={styles.tgBotName}>Havi Hot Lead Radar Bot</div>
                        <div className={styles.tgSub}>Thông báo tức thì • Vừa xong</div>
                      </div>
                    </div>
                    <span className={styles.tgTimeBadge}>3s trước</span>
                  </div>

                  {/* Telegram Message Body */}
                  <div className={styles.tgBody}>
                    <div className={styles.tgAlertHeader}>
                      🔔 <strong>[HAVI HOT LEAD] CÓ KHÁCH CẦN TƯ VẤN GẤP!</strong>
                    </div>
                    <div className={styles.tgLeadDetail}>
                      <div>👤 <strong>Khách hàng:</strong> {currentScenario.tabs.inbox.badge || "Chị Khách Hàng"}</div>
                      <div>📱 <strong>Số điện thoại:</strong> <span className={styles.tgPhoneHighlight}>{currentScenario.tabs.inbox.capturedPhone}</span></div>
                      <div>💬 <strong>Nhu cầu:</strong> &ldquo;{currentScenario.tabs.inbox.customerMsg}&rdquo;</div>
                      <div>📍 <strong>Kênh đến:</strong> Facebook Fanpage ({currentScenario.name})</div>
                      <div>⚡ <strong>Trạng thái:</strong> AI đã trả lời &amp; bắt số điện thoại thành công</div>
                    </div>

                    {/* Action buttons */}
                    <div className={styles.tgActionsGrid}>
                      <a
                        href="tel:0912345678"
                        className={styles.tgCallBtn}
                        onClick={(e) => e.preventDefault()}
                      >
                        📞 BẤM GỌI ĐIỆN NGAY
                      </a>
                      <a
                        href="https://zalo.me"
                        target="_blank"
                        rel="noreferrer"
                        className={styles.tgZaloBtn}
                        onClick={(e) => e.preventDefault()}
                      >
                        💬 BẤM MỞ CHAT ZALO
                      </a>
                    </div>
                  </div>
                </div>

                {/* Radar explanation side */}
                <div className={styles.radarSideCallout}>
                  <div className={styles.radarIconRing}>
                    <span className={styles.radarWave} />
                    <span className={styles.radarCenterIcon}>📡</span>
                  </div>
                  <h4 className={styles.radarTitle}>Chuông Báo Rung <span className={styles.highlightText}>Dưới 3 Giây</span></h4>
                  <p className={styles.radarDesc}>
                    Khách nhắn tin ban đêm hay rạng sáng, AI tự động trực chat theo bảng giá tiệm, khéo léo lấy SĐT và bắn chuông ngay về máy chủ tiệm để không bao giờ bị rơi mất đơn.
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
