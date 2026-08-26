"use client";
import { useLanguage } from "@/lib/i18n/language-context";

import { useEffect, useState } from "react";

type BeforeInstallPromptEvent = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: string }>;
};

export function PwaRegistrar() {
  const {
    t
  } = useLanguage();

  const [installPrompt, setInstallPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const [showIosPrompt, setShowIosPrompt] = useState(false);
  const [isDismissed, setIsDismissed] = useState(false);

  useEffect(() => {
    // 1. Chỉ đăng ký Service Worker trong môi trường Production, ở Local dev tự động huỷ để tránh xung đột Turbopack
    if (typeof window !== "undefined" && "serviceWorker" in navigator) {
      if (process.env.NODE_ENV === "production") {
        navigator.serviceWorker
          .register("/sw.js")
          .catch((err) => {
            console.warn("Havi PWA Service Worker registration failed:", err);
          });
      } else {
        navigator.serviceWorker.getRegistrations().then((regs) => {
          for (const reg of regs) reg.unregister();
        });
      }
    }

    // 2. Bắt sự kiện trước khi cài đặt App (Android / Chrome / Edge)
    const handleBeforeInstall = (e: Event) => {
      e.preventDefault();
      setInstallPrompt(e as BeforeInstallPromptEvent);
    };

    window.addEventListener("beforeinstallprompt", handleBeforeInstall);

    // 3. Kiểm tra thiết bị iOS Safari chưa cài Standalone
    if (typeof window !== "undefined") {
      const isIos =
        /iPad|iPhone|iPod/.test(navigator.userAgent) &&
        !("MSStream" in window);
      const isStandalone =
        window.matchMedia("(display-mode: standalone)").matches ||
        Boolean((navigator as unknown as { standalone?: boolean }).standalone);
      if (isIos && !isStandalone) {
        // Chỉ hiện sau 3 giây để không làm phiền người dùng
        const timer = setTimeout(() => setShowIosPrompt(true), 3000);
        return () => clearTimeout(timer);
      }
    }

    return () => window.removeEventListener("beforeinstallprompt", handleBeforeInstall);
  }, []);

  const handleInstall = async () => {
    if (!installPrompt) return;
    installPrompt.prompt();
    const { outcome } = await installPrompt.userChoice;
    if (outcome === "accepted") {
      setInstallPrompt(null);
    }
  };

  if (isDismissed || (!installPrompt && !showIosPrompt)) {
    return null;
  }

  return (
    <div
      style={{
        position: "fixed",
        bottom: "16px",
        left: "50%",
        transform: "translateX(-50%)",
        zIndex: 9999,
        background: "linear-gradient(135deg, #1e1b4b 0%, #0f172a 100%)",
        color: "#ffffff",
        padding: "12px 20px",
        borderRadius: "16px",
        boxShadow: "0 12px 32px rgba(0, 0, 0, 0.4), 0 0 0 1px rgba(99, 102, 241, 0.3)",
        display: "flex",
        alignItems: "center",
        gap: "14px",
        maxWidth: "92vw",
        width: "420px",
        animation: "slideUp 0.3s cubic-bezier(0.16, 1, 0.3, 1)",
      }}
    >
      <div
        style={{
          width: "40px",
          height: "40px",
          borderRadius: "10px",
          background: "#00D2FF",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: "20px",
          flexShrink: 0,
        }}
      >
        📱
      </div>
      <div style={{ flex: 1 }}>
        <div style={{ fontWeight: 700, fontSize: "0.9rem" }}>{t("Cài đặt Havi lên điện thoại")}</div>
        <div style={{ fontSize: "0.75rem", color: "#94a3b8" }}>
          {showIosPrompt && !installPrompt
            ? t("Bấm nút Chia sẻ 📤 rồi chọn 'Thêm vào MH chính'")
            : t("Mở toàn màn hình, chạy nhanh mượt mà")}
        </div>
      </div>
      {installPrompt ? (
        <button
          type="button"
          onClick={handleInstall}
          style={{
            background: "linear-gradient(135deg, #4f46e5 0%, #06b6d4 100%)",
            color: "#ffffff",
            border: "none",
            padding: "8px 14px",
            borderRadius: "8px",
            fontWeight: 700,
            fontSize: "0.8rem",
            cursor: "pointer",
            whiteSpace: "nowrap",
          }}
        >{t("Cài đặt ngay")}</button>
      ) : (
        <span
          style={{
            fontSize: "0.8rem",
            color: "#00D2FF",
            fontWeight: 700,
            whiteSpace: "nowrap",
            background: "rgba(0, 210, 255, 0.1)",
            padding: "6px 10px",
            borderRadius: "8px",
          }}
        >{t("📤 Thêm MH chính")}</span>
      )}
      <button
        type="button"
        onClick={() => setIsDismissed(true)}
        style={{
          background: "transparent",
          color: "#64748b",
          border: "none",
          fontSize: "16px",
          cursor: "pointer",
          padding: "4px",
        }}
        aria-label={t("Đóng")}
      >
        ×
      </button>
    </div>
  );
}
