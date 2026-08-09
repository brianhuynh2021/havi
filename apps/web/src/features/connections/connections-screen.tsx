"use client";

import { ConnectionList } from "./connection-list";
import styles from "./connections-screen.module.css";

/**
 * Trang Cài đặt → Kênh đã nối.
 *
 * Onboarding bước 2 cũng nối kênh, nhưng nó chỉ chạy đúng một lần. Token
 * Facebook thì hết hạn sau đó hàng tuần, và mất quyền có thể xảy ra bất cứ lúc
 * nào ai đó đổi vai trò trên Page — nên phải có một chỗ thường trực để nối lại,
 * không thì chủ tiệm chỉ còn cách đăng ký lại tài khoản.
 */
export function ConnectionsScreen() {
  return (
    <div className={styles.page}>
      <h1 className={styles.title}>Kênh đã nối</h1>
      <p className={styles.subtitle}>
        Havi chỉ đăng bài qua API chính thức của nền tảng. Kênh nào hết hạn hoặc
        mất quyền, chị nối lại ở đây để lịch đăng chạy tiếp.
      </p>
      <ConnectionList />
    </div>
  );
}
