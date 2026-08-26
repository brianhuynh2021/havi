"use client";
import { useLanguage } from "@/lib/i18n/language-context";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Logo } from "@/components/ui/logo";
import { ConnectionList } from "@/features/connections/connection-list";
import { useSession } from "@/lib/auth/session";
import { readTokens } from "@/lib/auth/token-store";

import {
  fetchDefaultShopName,
  initializeBusinessTruthPack,
  saveWorkspace,
} from "./onboarding.api";
import styles from "./onboarding.module.css";

type Step = 1 | 2;

const stepLabels = ["Đặt tên thương hiệu", "Nối kênh"];

export function OnboardingScreen() {
  const {
    t
  } = useLanguage();

  const router = useRouter();
  const { signIn } = useSession();
  // Quay về từ Facebook là một page load MỚI (backend redirect tới
  // /onboarding?ket_noi=...), nên mọi state trước đó đã mất. Không đọc lại bước
  // từ URL thì người dùng rơi về bước 1 và bấm "Tiếp tục" là tạo workspace
  // thứ hai trùng tên. `useState` với initializer chứ không `useEffect`: sửa step sau
  // lần render đầu sẽ nháy qua bước 1 một khung hình.
  const [step, setStep] = useState<Step>(() =>
    typeof window !== "undefined" &&
    new URLSearchParams(window.location.search).has("ket_noi")
      ? 2
      : 1,
  );
  const [createdWorkspaceId, setCreatedWorkspaceId] = useState<string | null>(
    () => readTokens()?.activeWorkspaceId ?? null,
  );
  const [shopName, setShopName] = useState("");
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);



  const handleStep2Proceed = useCallback(async () => {
    setSubmitting(true);
    // Kích hoạt Business Truth Pack: lưu Brand Voice & FAQ mẫu chuẩn ngành vào database
    try {
      await initializeBusinessTruthPack(shopName);
    } catch {
      // Tiếp tục luồng ngay cả khi có cảnh báo mạng
    }
    router.replace("/app");
  }, [shopName, router]);


  useEffect(() => {
    let cancelled = false;
    fetchDefaultShopName().then((name) => {
      if (!cancelled && name) setShopName((current) => current || name);
    });
    return () => {
      cancelled = true;
    };
  }, []);





  /** Lưu hoặc cập nhật thương hiệu (idempotent) ở cuối bước 1.
   *
   * Quay lại bước 1 để sửa tên thì cập nhật workspace hiện tại, không tạo
   * workspace thứ hai trùng tên. */
  async function submitBrandName() {
    if (!shopName.trim()) {
      setError("Nhập tên thương hiệu để Havi gọi đúng tên trên mọi kênh");
      return;
    }

    setError(null);
    setSubmitting(true);
    const currentWsId = createdWorkspaceId || readTokens()?.activeWorkspaceId;
    const result = await saveWorkspace(shopName.trim(), currentWsId);
    setSubmitting(false);
    if (!result.ok) {
      setError(result.message);
      return;
    }
    if (result.tokens.activeWorkspaceId) {
      setCreatedWorkspaceId(result.tokens.activeWorkspaceId);
    }
    signIn(result.tokens);
    setStep(2);
  }


  return (
    <div className={styles.wizard}>
      <div className={styles.brand}>
        <Logo size={44} />
        <div className={styles.brandText}>Havi</div>
      </div>

      <ol className={styles.steps} aria-label={t("Các bước onboarding")}>
        {stepLabels.map((label, index) => {
          const stepNumber = (index + 1) as Step;
          return (
            <li
              key={label}
              className={`${styles.step} ${
                stepNumber === step ? styles.stepActive : ""
              } ${stepNumber < step ? styles.stepDone : ""}`}
            >
              <span className={styles.stepDot}>{stepNumber}</span>
              {label}
            </li>
          );
        })}
      </ol>

      <div className={styles.panel}>
        {step === 1 ? (
          <>
            <h1 className={styles.title}>{t("Thương hiệu bạn quản trị tên gì?")}</h1>
            <p className={styles.subtitle}>{t(
              "Havi gọi đúng tên này trên mọi kênh. Giọng thương hiệu và danh sách điều không được hứa đặt sau, ở Cài đặt."
            )}</p>

            <div className={styles.inputSection}>
              <label className={styles.label} htmlFor="shop-name">{t("Tên thương hiệu")}</label>
              <Input
                id="shop-name"
                scale="large"
                placeholder={t("Ví dụ: Spa An Nhiên, Cà Phê 1985, Nhật Minh…")}
                value={shopName}
                onChange={(e) => setShopName(e.target.value)}
              />
            </div>

            {error ? (
              <p className={styles.error} role="alert">
                {error}
              </p>
            ) : null}

            <div className={styles.actions}>
              <Button
                variant="primary"
                scale="large"
                disabled={!shopName.trim() || submitting}
                onClick={submitBrandName}
              >
                {submitting ? t("Đang lưu…") : t("Tiếp tục")}
              </Button>
            </div>
          </>
        ) : (
          <>
            <h1 className={styles.title}>{t("Kết nối kênh của bạn")}</h1>
            <p className={styles.subtitle}>{t(
              "Nối Facebook bằng API chính thức để Havi thấy được Trang, Reels và\n              Messenger của bạn. TikTok là kênh kế tiếp, sau đó YouTube Shorts rồi\n              Google Business Profile — mỗi kênh chỉ bật sau khi nền tảng duyệt."
            )}</p>
            <div className={styles.connectionListWrapper}>
              <ConnectionList returnTo="onboarding" onUsableChange={setConnected} />
            </div>
            <div className={styles.stepActions}>
              <Button
                variant="ghost"
                scale="large"
                onClick={() => setStep(1)}
              >{t("← Quay lại")}</Button>
              <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
                <Button
                  variant="ghost"
                  onClick={handleStep2Proceed}
                  disabled={submitting}
                >{t("Bỏ qua, kết nối sau")}</Button>
                <Button
                  variant="primary"
                  scale="large"
                  disabled={!connected || submitting}
                  onClick={handleStep2Proceed}
                >
                  {submitting ? "Đang xử lý…" : connected ? "Bắt đầu sử dụng →" : "Bắt đầu sử dụng"}
                </Button>
              </div>
            </div>

          </>
        )}
      </div>
    </div>
  );
}
