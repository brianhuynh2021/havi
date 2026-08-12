"use client";

import styles from "./toast.module.css";

export type ToastItem = {
  id: string;
  type: "loading" | "success" | "info" | "error";
  title: string;
  description?: string;
};

type ToastContainerProps = {
  toasts: ToastItem[];
  onDismiss: (id: string) => void;
};

export function ToastContainer({ toasts, onDismiss }: ToastContainerProps) {
  if (!toasts.length) return null;

  return (
    <div className={styles.toastContainer} aria-live="polite" aria-atomic="true">
      {toasts.map((toast) => (
        <div key={toast.id} className={styles.toast} role="status">
          {toast.type === "loading" ? (
            <span className={styles.spinner} aria-hidden="true" />
          ) : (
            <span className={styles.toastIcon}>
              {toast.type === "success" ? "🎉" : toast.type === "error" ? "⚠️" : "⚡"}
            </span>
          )}

          <div className={styles.toastBody}>
            <p className={styles.toastTitle}>{toast.title}</p>
            {toast.description ? (
              <p className={styles.toastMeta}>{toast.description}</p>
            ) : null}
          </div>

          <button
            type="button"
            className={styles.closeButton}
            aria-label="Đóng thông báo"
            onClick={() => onDismiss(toast.id)}
          >
            ×
          </button>
        </div>
      ))}
    </div>
  );
}
