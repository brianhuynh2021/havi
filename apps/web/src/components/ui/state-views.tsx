import type { ReactNode } from "react";
import styles from "./state-views.module.css";

type StateViewProps = {
  title: string;
  body?: string;
  action?: ReactNode;
};

export function EmptyState({ title, body, action }: StateViewProps) {
  return (
    <div className={styles.state} role="status">
      <p className={styles.title}>{title}</p>
      {body ? <p className={styles.body}>{body}</p> : null}
      {action}
    </div>
  );
}

export function ErrorState({ title, body, action }: StateViewProps) {
  return (
    <div className={`${styles.state} ${styles.error}`} role="alert">
      <p className={styles.title}>{title}</p>
      {body ? <p className={styles.body}>{body}</p> : null}
      {action}
    </div>
  );
}

export function LoadingState({ title = "Đang tải…" }: { title?: string }) {
  return (
    <div className={styles.state} role="status" aria-live="polite">
      <span className={styles.spinner} aria-hidden="true" />
      <p className={styles.title}>{title}</p>
    </div>
  );
}
