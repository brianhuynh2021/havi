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
        <h1 className={styles.title}>Kênh kết nối</h1>
        <p className={styles.subtitle}>
          Kết nối Facebook Fanpage và Reels qua Meta Graph API chính thức.
          Sau khi nối, Havi đăng được bài và clip lên kênh, và nhận tin nhắn khách về hộp thư chung.
        </p>
      </header>
      <ConnectionList returnTo="settings" />
    </div>
  );
}
