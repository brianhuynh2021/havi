"use client";

import { ConnectionList } from "./connection-list";
import styles from "./connections-screen.module.css";

/**
 * Trang Cài đặt → Kênh đã nối.
 */
export function ConnectionsScreen() {
  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.badge}>
          <span>⚡ API Chính Thức</span>
        </div>
        <h1 className={styles.title}>Kênh truyền thông đã kết nối</h1>
        <p className={styles.subtitle}>
          Havi liên kết trực tiếp qua API chính thức của các nền tảng (Facebook,
          Zalo, TikTok, YouTube...). Khi kênh hết hạn hoặc mất quyền, chị có thể
          nối lại tại đây để hệ thống tiếp tục đăng bài và nhận tin nhắn tự động.
        </p>
      </header>
      <ConnectionList returnTo="settings" />
    </div>
  );
}
