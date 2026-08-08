import type { ButtonHTMLAttributes } from "react";
import styles from "./button.module.css";

type ButtonVariant = "primary" | "ghost" | "outline";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  /** `large` cho màn auth — full-width, cao 17px, chữ 18px. Cùng lý do đặt tên
   * `scale` như ở Input: `size` đụng thuộc tính sẵn có của phần tử HTML. */
  scale?: "default" | "large";
};

export function Button({
  variant = "primary",
  scale = "default",
  className = "",
  type = "button",
  ...props
}: ButtonProps) {
  const scaleClass = scale === "large" ? styles.large : "";
  return (
    <button
      type={type}
      className={`${styles.button} ${styles[variant]} ${scaleClass} ${className}`}
      {...props}
    />
  );
}
