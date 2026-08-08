import type { InputHTMLAttributes, TextareaHTMLAttributes } from "react";
import styles from "./input.module.css";

/** Không đặt tên prop là `size`: `<input>` đã có thuộc tính `size` kiểu number,
 * giao hai kiểu lại thành `never` và mọi giá trị truyền vào đều báo lỗi type. */
type InputProps = InputHTMLAttributes<HTMLInputElement> & {
  /** `large` cho màn auth — ô to, viền dày, bo góc nhiều hơn ô trong app. */
  scale?: "default" | "large";
};

export function Input({
  className = "",
  scale = "default",
  ...props
}: InputProps) {
  const sizeClass = scale === "large" ? styles.large : "";
  return <input className={`${styles.field} ${sizeClass} ${className}`} {...props} />;
}

type TextareaProps = TextareaHTMLAttributes<HTMLTextAreaElement>;

export function Textarea({ className = "", ...props }: TextareaProps) {
  return <textarea className={`${styles.field} ${styles.textarea} ${className}`} {...props} />;
}
