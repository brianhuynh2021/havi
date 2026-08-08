import type { ReactNode } from "react";
import styles from "./auth-shell.module.css";

type AuthShellProps = {
  children: ReactNode;
};

export function AuthShell({ children }: AuthShellProps) {
  return (
    <div className={styles.page}>
      <div className={styles.brand}>
        <div className={styles.brandMark}>Ha</div>
        <div className={styles.brandText}>Havi</div>
      </div>
      <div className={styles.card}>{children}</div>
      <p className={styles.tagline}>Havi — trợ lý marketing cho tiệm của bạn</p>
    </div>
  );
}
