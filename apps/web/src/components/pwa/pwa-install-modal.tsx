"use client";

import { useEffect, useState, useSyncExternalStore } from "react";
import { createPortal } from "react-dom";
import { Logo } from "@/components/ui/logo";
import { useLanguage } from "@/lib/i18n/language-context";
import styles from "./pwa-install-modal.module.css";

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

function subscribeStandalone(callback: () => void) {
  if (typeof window === "undefined") return () => {};
  const mql = window.matchMedia("(display-mode: standalone)");
  mql.addEventListener("change", callback);
  return () => mql.removeEventListener("change", callback);
}

function getStandaloneSnapshot() {
  if (typeof window === "undefined") return false;
  return (
    window.matchMedia("(display-mode: standalone)").matches ||
    (window.navigator as unknown as { standalone?: boolean }).standalone === true
  );
}

function getServerSnapshot() {
  return false;
}

function subscribeMount() {
  return () => {};
}
function getMountSnapshot() {
  return true;
}
function getServerMountSnapshot() {
  return false;
}

function subscribePlatform() {
  return () => {};
}
function getPlatformSnapshot(): "ios" | "android" | "desktop" {
  if (typeof window === "undefined") return "desktop";
  const ua = window.navigator.userAgent.toLowerCase();
  if (/iphone|ipad|ipod/.test(ua)) return "ios";
  if (/android/.test(ua)) return "android";
  return "desktop";
}
function getServerPlatformSnapshot(): "ios" | "android" | "desktop" {
  return "desktop";
}

export function PwaInstallModal() {
const { lang, t } = useLanguage();
  const mounted = useSyncExternalStore(subscribeMount, getMountSnapshot, getServerMountSnapshot);
  const detectedPlatform = useSyncExternalStore(subscribePlatform, getPlatformSnapshot, getServerPlatformSnapshot);

  const [isOpen, setIsOpen] = useState(false);
  const [selectedTab, setSelectedTab] = useState<"ios" | "android" | "desktop" | null>(null);
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);

  const activeTab = selectedTab ?? detectedPlatform;

  const isStandalone = useSyncExternalStore(
    subscribeStandalone,
    getStandaloneSnapshot,
    getServerSnapshot,
  );

  useEffect(() => {
    const handlePrompt = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e as BeforeInstallPromptEvent);
    };

    window.addEventListener("beforeinstallprompt", handlePrompt);
    return () => window.removeEventListener("beforeinstallprompt", handlePrompt);
  }, []);

  // Nếu đã mở trong chế độ PWA Standalone thì không hiện bất kỳ lời nhắc nào nữa
  if (isStandalone) return null;

  const handleOpenModal = () => {
    setIsOpen(true);
  };

  const handleNativeInstall = async () => {
    if (deferredPrompt) {
      await deferredPrompt.prompt();
      const choice = await deferredPrompt.userChoice;
      if (choice.outcome === "accepted") {
        setDeferredPrompt(null);
        setIsOpen(false);
      }
    } else {
      setIsOpen(true);
    }
  };

  const currentUrl = typeof window !== "undefined" ? window.location.origin : "https://havi.vn";
  const qrUrl = `https://api.qrserver.com/v1/create-qr-code/?size=240x240&data=${encodeURIComponent(
    currentUrl
  )}&bgcolor=ffffff&color=090d16&margin=6`;

  const modalContent = isOpen ? (
    <div className={styles.modalOverlay} onClick={() => setIsOpen(false)}>
      <div
        className={styles.modalBox}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="pwa-modal-title"
      >
        {/* Header */}
        <div className={styles.modalHeader}>
          <div className={styles.modalTitleWrap}>
            <div className={styles.appIconBadge}>
              <Logo size={32} />
            </div>
            <div>
              <h3 id="pwa-modal-title" className={styles.modalTitle}>
                {t("Cài Đặt Havi Lên Điện Thoại")}
              </h3>
              <p className={styles.modalSubtitle}>
                {t("Dùng mượt mà 1-chạm, tiện lợi như app tải về máy")}
              </p>
            </div>
          </div>
          <button
            type="button"
            className={styles.closeBtn}
            onClick={() => setIsOpen(false)}
            aria-label={t("Đóng")}
          >
            ✕
          </button>
        </div>

        {/* Benefits Grid */}
        <div className={styles.benefitsRow}>
          <div className={styles.benefitItem}>
            <span>⚡</span>
            <span>{t("Mở tức thì không chờ tải")}</span>
          </div>
          <div className={styles.benefitItem}>
            <span>🔔</span>
            <span>{t("Mở hộp thư nhanh hơn")}</span>
          </div>
          <div className={styles.benefitItem}>
            <span>📱</span>
            <span>{t("Toàn màn hình tiện lợi")}</span>
          </div>
        </div>

        {/* Platform Tabs */}
        <div className={styles.platformTabs}>
          <button
            type="button"
            className={`${styles.tabBtn} ${activeTab === "ios" ? styles.tabBtnActive : ""}`}
            onClick={() => setSelectedTab("ios")}
          >
            <span>🍎</span>
            <span>iPhone / iPad</span>
          </button>
          <button
            type="button"
            className={`${styles.tabBtn} ${activeTab === "android" ? styles.tabBtnActive : ""}`}
            onClick={() => setSelectedTab("android")}
          >
            <span>🤖</span>
            <span>Android</span>
          </button>
          <button
            type="button"
            className={`${styles.tabBtn} ${activeTab === "desktop" ? styles.tabBtnActive : ""}`}
            onClick={() => setSelectedTab("desktop")}
          >
            <span>💻</span>
            <span>{t("Quét Mã QR")}</span>
          </button>
        </div>

        {/* Tab Content: iOS Safari */}
        {activeTab === "ios" && (
          <div className={styles.tabBody}>
            <div className={styles.stepsList}>
              <div className={styles.stepItem}>
                <div className={styles.stepNumber}>1</div>
                <div className={styles.stepText}>
                  {lang === "VN" ? (
                    <>{t("Mở Havi trên trình duyệt")}<strong>Safari</strong>{t(", bấm vào nút")}{" "}{" "}
                      <strong>{t("Chia sẻ (Share ⎋)")}</strong>{t("ở thanh công cụ dưới cùng.")}</>
                  ) : (
                    <>
                      Open in <strong>Safari</strong>, tap the <strong>Share (⎋)</strong> button on the bottom bar.
                    </>
                  )}
                </div>
              </div>
              <div className={styles.stepItem}>
                <div className={styles.stepNumber}>2</div>
                <div className={styles.stepText}>
                  {lang === "VN" ? (
                    <>{t("Cuộn xuống danh sách menu và chọn")}{" "}{" "}
                      <strong>{t("“Thêm vào Màn hình chính” (Add to Home Screen ➕)")}</strong>.
                    </>
                  ) : (
                    <>
                      Scroll down and tap <strong>&ldquo;Add to Home Screen&rdquo; (➕)</strong>.
                    </>
                  )}
                </div>
              </div>
              <div className={styles.stepItem}>
                <div className={styles.stepNumber}>3</div>
                <div className={styles.stepText}>
                  {lang === "VN" ? (
                    <>{t("Bấm nút")}<strong>{t("“Thêm” (Add)")}</strong>{t("ở góc trên bên phải. Icon Havi đã sẵn sàng trên màn hình chính rồi!")}</>
                  ) : (
                    <>
                      Tap <strong>&ldquo;Add&rdquo;</strong> at the top right. Havi icon is now on your home screen!
                    </>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tab Content: Android */}
        {activeTab === "android" && (
          <div className={styles.tabBody}>
            {deferredPrompt ? (
              <div className={styles.androidDirectBox}>
                <p className={styles.androidDirectText}>
                  {t("Trình duyệt của bạn đã sẵn sàng cài đặt ứng dụng Havi trực tiếp chỉ với 1 cú chạm:")}
                </p>
                <button
                  type="button"
                  className={styles.primaryActionBtn}
                  onClick={handleNativeInstall}
                >
                  📲 {t("Bấm Để Cài Đặt Ngay")}
                </button>
              </div>
            ) : (
              <div className={styles.stepsList}>
                <div className={styles.stepItem}>
                  <div className={styles.stepNumber}>1</div>
                  <div className={styles.stepText}>
                    {lang === "VN" ? (
                      <>{t("Bấm vào biểu tượng")}<strong>{t("Menu 3 chấm (⋮)")}</strong>{t("ở góc trên bên phải trình duyệt Chrome.")}</>
                    ) : (
                      <>
                        Tap the <strong>3 dots Menu (⋮)</strong> on the top right of Chrome.
                      </>
                    )}
                  </div>
                </div>
                <div className={styles.stepItem}>
                  <div className={styles.stepNumber}>2</div>
                  <div className={styles.stepText}>
                    {lang === "VN" ? (
                      <>{t("Chọn")}<strong>{t("“Cài đặt ứng dụng”")}</strong>{t("hoặc")}<strong>{t("“Thêm vào Màn hình chính”")}</strong>.
                      </>
                    ) : (
                      <>
                        Select <strong>&ldquo;Install app&rdquo;</strong> or <strong>&ldquo;Add to Home screen&rdquo;</strong>.
                      </>
                    )}
                  </div>
                </div>
                <div className={styles.stepItem}>
                  <div className={styles.stepNumber}>3</div>
                  <div className={styles.stepText}>
                    {lang === "VN" ? (
                      <>{t("Xác nhận")}<strong>{t("Cài đặt")}</strong>{t(". Ứng dụng Havi sẽ xuất hiện trong danh sách App của điện thoại.")}</>
                    ) : (
                      <>
                        Confirm <strong>Install</strong>. Havi will be added to your app drawer.
                      </>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab Content: Desktop QR Code */}
        {activeTab === "desktop" && (
          <div className={styles.tabBody}>
            <div className={styles.qrContainer}>
              <div className={styles.qrBox}>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={qrUrl}
                  alt={t("QR Cài Havi lên điện thoại")}
                  className={styles.qrImage}
                />
              </div>
              <div className={styles.qrGuide}>
                <p className={styles.qrTitle}>
                  📸 {t("Quét mã bằng Camera điện thoại")}
                </p>
                <p className={styles.qrSubtitle}>
                  {t("Mở camera iPhone hoặc Android quét mã để mở Havi trên điện thoại và cài ra màn hình chính trong 3 giây.")}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Modal Footer */}
        <div className={styles.modalFooter}>
          <button
            type="button"
            className={styles.dismissBtn}
            onClick={() => setIsOpen(false)}
          >
            {t("Đã hiểu, đóng hướng dẫn")}
          </button>
        </div>
      </div>
    </div>
  ) : null;

  return (
    <>
      {/* Nút Cài App ở Header */}
      <button
        type="button"
        className={styles.headerInstallBtn}
        onClick={handleOpenModal}
        title={t("Cài Havi ra màn hình chính điện thoại")}
      >
        <span className={styles.pulseDot} />
        <span className={styles.btnIcon}>📲</span>
        <span className={styles.btnText}>{t("Cài App Điện Thoại")}</span>
      </button>

      {/* Render Modal ra Document.Body bằng Portal để không bao giờ bị che khuất */}
      {mounted && typeof document !== "undefined" && document.body
        ? createPortal(modalContent, document.body)
        : null}
    </>
  );
}
