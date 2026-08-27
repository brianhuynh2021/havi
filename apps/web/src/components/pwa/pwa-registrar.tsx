"use client";
import { useEffect } from "react";

export function PwaRegistrar() {
  useEffect(() => {
    // Chỉ đăng ký service worker ở production. Lời mời cài đặt là hành động chủ
    // động trong header sau khi người dùng đã vào app; registrar không tự bật
    // banner che màn hình trước khi người dùng nhận được giá trị.
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

  }, []);
  return null;
}
