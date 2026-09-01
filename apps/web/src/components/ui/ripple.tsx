"use client";

import { useState, useCallback, useEffect, type MouseEvent, type PointerEvent, type KeyboardEvent } from "react";
import styles from "./ripple.module.css";

export interface RippleItem {
  id: number;
  x: number;
  y: number;
  size: number;
}

export function useRipple() {
  const [ripples, setRipples] = useState<RippleItem[]>([]);

  const removeRipple = useCallback((id: number) => {
    setRipples((prev) => prev.filter((ripple) => ripple.id !== id));
  }, []);

  const addRipple = useCallback((event: MouseEvent<HTMLElement> | PointerEvent<HTMLElement> | KeyboardEvent<HTMLElement>) => {
    // Nếu người dùng bật chế độ giảm chuyển động, không tạo ripple (tránh rò rỉ bộ nhớ do animation không chạy).
    // Kiểm tra sự tồn tại của matchMedia vì jsdom không cài sẵn API này.
    if (typeof window !== "undefined" && typeof window.matchMedia === "function") {
      if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
        return;
      }
    }

    const target = event.currentTarget;
    const rect = target.getBoundingClientRect();

    let x = 0;
    let y = 0;

    // Nếu là click chuột hoặc chạm ngón tay (pointerdown / mousedown / touch)
    if ("clientX" in event && (event.clientX !== 0 || event.clientY !== 0)) {
      x = event.clientX - rect.left;
      y = event.clientY - rect.top;
    } else {
      // Nếu kích hoạt bằng bàn phím (Enter / Space), ripple xuất phát từ tâm
      x = rect.width / 2;
      y = rect.height / 2;
    }

    // Tính bán kính bao phủ tới góc xa nhất
    const radiusX = Math.max(x, rect.width - x);
    const radiusY = Math.max(y, rect.height - y);
    const radius = Math.sqrt(radiusX * radiusX + radiusY * radiusY);
    const size = radius * 2;

    const rippleId = Date.now() + Math.random();
    const newRipple: RippleItem = {
      id: rippleId,
      x,
      y,
      size,
    };

    setRipples((prev) => [...prev, newRipple]);

    // Fallback dọn dẹp sau 600ms phòng trường hợp onAnimationEnd bị bỏ lỡ
    setTimeout(() => {
      removeRipple(rippleId);
    }, 600);
  }, [removeRipple]);

  return { ripples, addRipple, removeRipple };
}

export function Ripple({
  ripples,
  onClear,
}: {
  ripples: RippleItem[];
  onClear: (id: number) => void;
}) {
  if (!ripples || ripples.length === 0) return null;

  return (
    <span className={styles.container} aria-hidden="true">
      {ripples.map((ripple) => (
        <span
          key={ripple.id}
          className={styles.ripple}
          style={{
            left: `${ripple.x}px`,
            top: `${ripple.y}px`,
            width: `${ripple.size}px`,
            height: `${ripple.size}px`,
          }}
          onAnimationEnd={() => onClear(ripple.id)}
        />
      ))}
    </span>
  );
}
