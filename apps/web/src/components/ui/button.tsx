"use client";

import type { ButtonHTMLAttributes, PointerEvent, KeyboardEvent } from "react";
import { useRipple, Ripple } from "./ripple";
import styles from "./button.module.css";

type ButtonVariant = "primary" | "ghost" | "outline";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  /** `large` cho màn auth — full-width, chuẩn touch target 48px, chữ 15px theo Material 3.
   * Cùng lý do đặt tên `scale` như ở Input: `size` đụng thuộc tính sẵn có của phần tử HTML. */
  scale?: "default" | "large";
};

export function Button({
  variant = "primary",
  scale = "default",
  className = "",
  type = "button",
  onClick,
  onPointerDown,
  onKeyDown,
  children,
  disabled,
  ...props
}: ButtonProps) {
  const { ripples, addRipple, removeRipple } = useRipple();
  const scaleClass = scale === "large" ? styles.large : "";

  const handlePointerDown = (e: PointerEvent<HTMLButtonElement>) => {
    if (!disabled) {
      addRipple(e);
    }
    onPointerDown?.(e);
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLButtonElement>) => {
    if (!disabled && (e.key === "Enter" || e.key === " ")) {
      addRipple(e);
    }
    onKeyDown?.(e);
  };

  return (
    <button
      type={type}
      disabled={disabled}
      className={`${styles.button} ${styles[variant]} ${scaleClass} ${className}`}
      onPointerDown={handlePointerDown}
      onKeyDown={handleKeyDown}
      onClick={onClick}
      {...props}
    >
      <Ripple ripples={ripples} onClear={removeRipple} />
      {children}
    </button>
  );
}
