"use client";
import { useLanguage } from "@/lib/i18n/language-context";

import React, { useState, useEffect } from "react";
import styles from "./danger-confirm-modal.module.css";

export type DangerActionType = "workspace" | "account" | "custom";

interface DangerConfirmModalProps {
  isOpen: boolean;
  type: DangerActionType;
  targetName?: string;
  isDeleting: boolean;
  customKeyword?: string;
  customTitle?: string;
  customLostItems?: string[];
  onClose: () => void;
  onConfirm: () => void;
}

export function DangerConfirmModal({
  isOpen,
  type,
  targetName = "tiệm này",
  isDeleting,
  customKeyword = "XOA",
  customTitle = "Xác nhận xoá",
  customLostItems = [],
  onClose,
  onConfirm,
}: DangerConfirmModalProps) {
  const {
    t
  } = useLanguage();

  const [confirmInput, setConfirmInput] = useState("");

  const requiredKeyword = type === "workspace" ? "XOATIEM" : type === "account" ? "XOATAIKHOAN" : customKeyword;
  const isMatch = confirmInput.trim().toUpperCase() === requiredKeyword;

  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !isDeleting) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, isDeleting, onClose]);

  if (!isOpen) return null;

  return (
    <div className={styles.overlay} onClick={isDeleting ? undefined : onClose} role="dialog" aria-modal="true">
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        {/* Modal Header */}
        <div className={styles.modalHeader}>
          <div className={styles.warningIconBox}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
              <line x1="12" y1="9" x2="12" y2="13" />
              <line x1="12" y1="17" x2="12.01" y2="17" />
            </svg>
          </div>
          <div className={styles.headerText}>
            <h3 className={styles.modalTitle}>
              {type === "workspace" 
                ? `Xác nhận xoá tiệm "${targetName}"` 
                : type === "account" 
                  ? "Xác nhận xoá tài khoản Havi"
                  : customTitle}
            </h3>
            <p className={styles.modalSubtitle}>{t("⚠️ Hành động này mang tính vĩnh viễn và KHÔNG THỂ HOÀN TÁC")}</p>
          </div>
          <button
            type="button"
            className={styles.closeBtn}
            onClick={onClose}
            disabled={isDeleting}
            aria-label={t("Đóng")}
          >
            ✕
          </button>
        </div>

        {/* Modal Body */}
        <div className={styles.modalBody}>
          {/* Retention Heuristic Box - Stanford HCI */}
          <div className={styles.retentionBox}>
            <div className={styles.retentionHeading}>
              <span>{t("🛡️ Bạn sẽ mất các quyền lợi sau nếu thực hiện xoá:")}</span>
            </div>
            <ul className={styles.lostItemsList}>
              {type === "workspace" ? (
                <>
                  <li className={styles.lostItem}>
                    <span className={styles.lostItemIcon}>✕</span>
                    <span>{t("Mất toàn bộ cấu hình giọng văn tiệm & bộ từ khóa cấm đã huấn luyện.")}</span>
                  </li>
                  <li className={styles.lostItem}>
                    <span className={styles.lostItemIcon}>✕</span>
                    <span>{t("Ngắt kết nối các kênh xuất bản tự động (Facebook, TikTok, Google Maps).")}</span>
                  </li>
                  <li className={styles.lostItem}>
                    <span className={styles.lostItemIcon}>✕</span>
                    <span>{t("Xoá toàn bộ bản nháp, lịch đăng và kho media của thương hiệu này.")}</span>
                  </li>
                </>
              ) : type === "account" ? (
                <>
                  <li className={styles.lostItem}>
                    <span className={styles.lostItemIcon}>✕</span>
                    <span>{t("Thu hồi mọi phiên đăng nhập và xoá vĩnh viễn tài khoản khỏi hệ thống.")}</span>
                  </li>
                  <li className={styles.lostItem}>
                    <span className={styles.lostItemIcon}>✕</span>
                    <span>{t("Mất tất cả các tiệm kinh doanh và dữ liệu trợ lý AI đã thiết lập.")}</span>
                  </li>
                  <li className={styles.lostItem}>
                    <span className={styles.lostItemIcon}>✕</span>
                    <span>{t("Mất quyền lợi gói cước đã đăng ký và không thể khôi phục lại tài khoản.")}</span>
                  </li>
                </>
              ) : (
                customLostItems.map((item, idx) => (
                  <li key={idx} className={styles.lostItem}>
                    <span className={styles.lostItemIcon}>✕</span>
                    <span>{item}</span>
                  </li>
                ))
              )}
            </ul>

            <div className={styles.supportCallout}>{t(
              "💬 Gặp khó khăn khi vận hành? Đội ngũ Founder luôn hỗ trợ 1 kèm 1 qua Zalo:"
            )}<strong>0984 883 750</strong>
            </div>
          </div>

          {/* Type-to-confirm input - MIT Security Safeguard */}
          <div className={styles.confirmInputBox}>
            <label htmlFor="confirm-delete-input" className={styles.confirmLabel}>{t("Nhập chính xác chữ")}<span className={styles.confirmKeyword}>{requiredKeyword}</span>{t("vào ô bên dưới để mở khóa nút xóa:")}</label>
            <input
              id="confirm-delete-input"
              type="text"
              className={styles.typeInput}
              placeholder={`Gõ "${requiredKeyword}" để xác nhận`}
              value={confirmInput}
              onChange={(e) => setConfirmInput(e.target.value)}
              disabled={isDeleting}
              autoFocus
            />
          </div>
        </div>

        {/* Modal Footer */}
        <div className={styles.modalFooter}>
          <button
            type="button"
            className={styles.cancelStayBtn}
            onClick={onClose}
            disabled={isDeleting}
          >
            💙 {type === "workspace" ? "Giữ Lại Tiệm (Khuyên dùng)" : type === "account" ? "Giữ Lại Tài Khoản (Khuyên dùng)" : "Hủy thao tác"}
          </button>
          <button
            type="button"
            className={styles.deleteConfirmBtn}
            onClick={onConfirm}
            disabled={!isMatch || isDeleting}
          >
            {isDeleting ? "Đang xử lý xoá..." : type === "custom" ? "Xác nhận xoá" : "Xác nhận xoá vĩnh viễn"}
          </button>
        </div>
      </div>
    </div>
  );
}
