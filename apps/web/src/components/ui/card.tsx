import type { HTMLAttributes } from "react";
import styles from "./card.module.css";

type CardProps = HTMLAttributes<HTMLDivElement> & {
  tone?: "paper" | "dark";
};

export function Card({ tone = "paper", className = "", ...props }: CardProps) {
  return (
    <div className={`${styles.card} ${styles[tone]} ${className}`} {...props} />
  );
}
