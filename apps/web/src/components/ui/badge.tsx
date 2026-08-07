import type { HTMLAttributes } from "react";
import styles from "./badge.module.css";

type BadgeTone = "success" | "info" | "neutral" | "warning" | "primary";

type BadgeProps = HTMLAttributes<HTMLSpanElement> & {
  tone?: BadgeTone;
};

export function Badge({ tone = "neutral", className = "", ...props }: BadgeProps) {
  return (
    <span className={`${styles.badge} ${styles[tone]} ${className}`} {...props} />
  );
}
