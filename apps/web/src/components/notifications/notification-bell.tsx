"use client";

import { useEffect, useRef, useState } from "react";
import styles from "./notification-bell.module.css";
import { useNotifications } from "./notification-store";

export function NotificationBell() {
  const [open, setOpen] = useState(false);
  const { notifications, unreadCount, markAllAsRead, markAsRead } = useNotifications();
  const wrapperRef = useRef<HTMLDivElement>(null);

  // Đóng popover khi click ra ngoài
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div ref={wrapperRef} className={styles.wrapper}>
      <button
        type="button"
        className={styles.bellButton}
        aria-label={`Thông báo (${unreadCount} chưa đọc)`}
        aria-expanded={open}
        onClick={() => setOpen((prev) => !prev)}
      >
        🔔
        {unreadCount > 0 ? (
          <span className={styles.badge}>{unreadCount > 9 ? "9+" : unreadCount}</span>
        ) : null}
      </button>

      {open ? (
        <div className={styles.popover} role="dialog" aria-label="Trung tâm thông báo">
          <div className={styles.popoverHeader}>
            <h3 className={styles.popoverTitle}>🔔 Thông báo Havi</h3>
            {unreadCount > 0 ? (
              <button
                type="button"
                className={styles.markAllRead}
                onClick={markAllAsRead}
              >
                Đánh dấu đã đọc
              </button>
            ) : null}
          </div>

          <div className={styles.notifList}>
            {notifications.length ? (
              notifications.map((item) => (
                <div
                  key={item.id}
                  className={`${styles.notifItem} ${!item.read ? styles.unreadItem : ""}`}
                  onClick={() => markAsRead(item.id)}
                >
                  <span className={styles.notifIcon}>
                    {item.type === "draft_ready"
                      ? "⚡"
                      : item.type === "publish_success"
                        ? "🚀"
                        : "ℹ️"}
                  </span>
                  <div className={styles.notifBody}>
                    <div className={styles.notifTitleRow}>
                      <span className={styles.notifItemTitle}>{item.title}</span>
                      <span className={styles.notifTime}>{item.timestamp}</span>
                    </div>
                    <p className={styles.notifDesc}>{item.description}</p>
                  </div>
                  {!item.read ? <span className={styles.unreadDot} /> : null}
                </div>
              ))
            ) : (
              <div className={styles.emptyState}>Chưa có thông báo mới nào</div>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
