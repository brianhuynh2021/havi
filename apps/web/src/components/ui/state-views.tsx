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

// `title` không có mặc định là chủ ý: một mặc định `"Đang tải…"` ở đây là chuỗi
// cấp module, bọc `t()` tại đó sẽ đóng băng ngôn ngữ lúc import. Bắt chỗ gọi
// truyền vào thì câu luôn dịch đúng, và chỗ gọi nào cũng đã có `t` trong tay.
export function LoadingState({ title }: { title: string }) {
  return (
    <div className={styles.state} role="status" aria-live="polite">
      <span className={styles.spinner} aria-hidden="true" />
      <p className={styles.title}>{title}</p>
    </div>
  );
}
