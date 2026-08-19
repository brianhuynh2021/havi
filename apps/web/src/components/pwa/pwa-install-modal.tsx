"use client";

import { useEffect, useState, useSyncExternalStore } from "react";
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

export function PwaInstallModal() {
  const { lang, t } = useLanguage();
  const [isOpen, setIsOpen] = useState(false);
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);
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

  // Nếu đã chạy trong app PWA standalone thì không hiện nút nữa
  if (isStandalone) return null;

  const handleClick = async () => {
    if (deferredPrompt) {
      await deferredPrompt.prompt();
      const choice = await deferredPrompt.userChoice;
      if (choice.outcome === "accepted") {
        setDeferredPrompt(null);
      }
    } else {
      setIsOpen(true);
    }
  };

  return (
    <>
      <button
        type="button"
        className={styles.installBtn}
        onClick={handleClick}
        title={t({
          vi: "Cài Havi ra màn hình chính điện thoại",
          en: "Add Havi to Home Screen",
        })}
      >
        <span>📲</span>
        <span>{lang === "VN" ? "Cài App" : "Install App"}</span>
      </button>

      {isOpen ? (
        <div className={styles.modalOverlay} onClick={() => setIsOpen(false)}>
          <div className={styles.modalBox} onClick={(e) => e.stopPropagation()}>
            <div className={styles.modalHeader}>
              <h3 className={styles.modalTitle}>
                <span>📲</span>
                <span>
                  {t({
                    vi: "Cài Đặt Havi Ra Màn Hình Chính",
                    en: "Add Havi to Home Screen",
                  })}
                </span>
              </h3>
              <button
                type="button"
                className={styles.closeBtn}
                onClick={() => setIsOpen(false)}
                aria-label="Đóng"
              >
                ✕
              </button>
            </div>

            <p className={styles.modalDesc}>
              {t({
                vi: "Dùng Havi mượt mà như app tải từ App Store/CH Play, truy cập tức thì 1-chạm không cần mở lại trình duyệt.",
                en: "Use Havi seamlessly like an app from App Store, 1-tap instant access without re-opening browser.",
              })}
            </p>

            <div className={styles.stepsList}>
              <div className={styles.stepItem}>
                <div className={styles.stepNumber}>1</div>
                <div className={styles.stepText}>
                  {lang === "VN" ? (
                    <>
                      Bấm vào biểu tượng <strong>Chia sẻ (Share ⎋)</strong> ở thanh công cụ dưới cùng (trên Safari iPhone) hoặc góc phải trên (trên Android).
                    </>
                  ) : (
                    <>
                      Tap the <strong>Share (⎋)</strong> button on Safari bottom bar or top menu on Android.
                    </>
                  )}
                </div>
              </div>

              <div className={styles.stepItem}>
                <div className={styles.stepNumber}>2</div>
                <div className={styles.stepText}>
                  {lang === "VN" ? (
                    <>
                      Cuộn xuống danh sách tùy chọn và chọn <strong>&ldquo;Thêm vào Màn hình chính&rdquo; (Add to Home Screen ➕)</strong>.
                    </>
                  ) : (
                    <>
                      Scroll down and select <strong>&ldquo;Add to Home Screen&rdquo; (➕)</strong>.
                    </>
                  )}
                </div>
              </div>

              <div className={styles.stepItem}>
                <div className={styles.stepNumber}>3</div>
                <div className={styles.stepText}>
                  {lang === "VN" ? (
                    <>
                      Bấm <strong>&ldquo;Thêm&rdquo; (Add)</strong> ở góc trên bên phải. Biểu tượng Havi sẽ xuất hiện trên màn hình điện thoại của bạn!
                    </>
                  ) : (
                    <>
                      Tap <strong>&ldquo;Add&rdquo;</strong> at the top right. The Havi icon is now on your home screen!
                    </>
                  )}
                </div>
              </div>
            </div>

            <button
              type="button"
              className={styles.actionBtn}
              onClick={() => setIsOpen(false)}
            >
              {lang === "VN" ? "Đã hiểu, đóng hướng dẫn" : "Got it, close"}
            </button>
          </div>
        </div>
      ) : null}
    </>
  );
}
