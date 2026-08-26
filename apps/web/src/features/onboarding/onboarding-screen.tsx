"use client";

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
import {
  industryOptions,
  getIndustrySamplePreview,
  type IndustryOption,
} from "./onboarding.fixture";
import styles from "./onboarding.module.css";

type Step = 1 | 2;

const stepLabels = ["Khai báo thương hiệu", "Nối kênh"];

export function OnboardingScreen() {
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
  const [industry, setIndustry] = useState<IndustryOption["value"] | null>(null);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const previewSample = getIndustrySamplePreview(industry, shopName);

  const handleStep2Proceed = useCallback(async () => {
    setSubmitting(true);
    // Kích hoạt Business Truth Pack: lưu Brand Voice & FAQ mẫu chuẩn ngành vào database
    try {
      await initializeBusinessTruthPack(industry, shopName);
    } catch {
      // Tiếp tục luồng ngay cả khi có cảnh báo mạng
    }
    router.replace("/app");
  }, [industry, shopName, router]);


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
  async function submitIndustry() {
    if (!shopName.trim()) {
      setError("Nhập tên thương hiệu để Havi gọi đúng tên trên mọi kênh");
      return;
    }
    if (!industry) return;

    setError(null);
    setSubmitting(true);
    const currentWsId = createdWorkspaceId || readTokens()?.activeWorkspaceId;
    const result = await saveWorkspace(shopName.trim(), industry, currentWsId);
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

      <ol className={styles.steps} aria-label="Các bước onboarding">
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
            <h1 className={styles.title}>Thương hiệu bạn quản trị tên gì?</h1>
            <p className={styles.subtitle}>
              Havi dùng tên và ngành để đặt giọng thương hiệu và bộ quy tắc nội
              dung cho workspace này.
            </p>

            <div className={styles.inputSection}>
              <label className={styles.label} htmlFor="shop-name">
                Tên thương hiệu
              </label>
              <Input
                id="shop-name"
                scale="large"
                placeholder="Ví dụ: Spa An Nhiên, Cà Phê 1985, Nhật Minh…"
                value={shopName}
                onChange={(e) => setShopName(e.target.value)}
              />
            </div>

            <div className={styles.industrySection}>
              <label className={styles.label}>Ngành của thương hiệu</label>
              <div className={styles.industryGrid}>
                {industryOptions.map((option) => {
                  const isSelected = industry === option.value;
                  return (
                    <button
                      key={option.value}
                      type="button"
                      aria-pressed={isSelected}
                      className={`${styles.industryCard} ${
                        isSelected ? styles.industryCardActive : ""
                      }`}
                      onClick={() => setIndustry(option.value)}
                    >
                      <div className={styles.cardHeader}>
                        <div className={styles.cardTitleWrapper}>
                          <span className={styles.cardIcon}>{option.icon}</span>
                          <span className={styles.cardTitle}>{option.label}</span>
                        </div>
                        {option.recommended ? (
                          <span className={styles.recommendedTag}>★ Đề xuất pilot</span>
                        ) : null}
                      </div>
                      <div className={styles.cardDesc}>
                        {option.desc}
                      </div>
                      {isSelected ? (
                        <div className={styles.checkBadge}>
                          <svg
                            width="12"
                            height="12"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="3.5"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          >
                            <polyline points="20 6 9 17 4 12" />
                          </svg>
                        </div>
                      ) : null}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Xem trước giọng thương hiệu — để lựa chọn ngành ở trên có hệ quả
                nhìn thấy được, thay vì là một ô radio không biết đổi gì. */}
            <div className={styles.magicPreviewCard} aria-label="Bản xem trước giọng thương hiệu">
              <div className={styles.magicPreviewHeader}>
                <h3 className={styles.magicPreviewTitle}>
                  ✨ Giọng thương hiệu sẽ ra thế này
                </h3>
                <span className={styles.magicBadge}>⚡ Bản mẫu theo ngành</span>
              </div>
              <div className={styles.magicPreviewContent}>
                <div className={styles.mockupHeader}>
                  <div className={styles.mockupAvatar}>
                    {(shopName.trim() || "H")[0].toUpperCase()}
                  </div>
                  <div>
                    <p className={styles.mockupName}>{shopName.trim() || "Thương hiệu của bạn"}</p>
                    <p className={styles.mockupMeta}>Fanpage · Vừa xong · 🌐</p>
                  </div>
                </div>
                <p className={styles.mockupText}>
                  ✨ &ldquo;{previewSample.text}&rdquo;
                </p>
                <div className={styles.mockupFooter}>
                  {previewSample.hashtags.map((tag) => (
                    <span key={tag}>{tag}</span>
                  ))}
                </div>
              </div>
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
                disabled={!industry || submitting}
                onClick={submitIndustry}
              >
                {submitting ? "Đang tạo tiệm…" : "Tiếp tục"}
              </Button>
            </div>
          </>
        ) : (
          <>
            <h1 className={styles.title}>Kết nối kênh của bạn</h1>
            <p className={styles.subtitle}>
              Nối Facebook bằng API chính thức để Havi thấy được Trang, Reels và
              Messenger của bạn. TikTok là kênh kế tiếp, sau đó YouTube Shorts rồi
              Google Business Profile — mỗi kênh chỉ bật sau khi nền tảng duyệt.
            </p>
            <div className={styles.connectionListWrapper}>
              <ConnectionList returnTo="onboarding" onUsableChange={setConnected} />
            </div>
            <div className={styles.stepActions}>
              <Button
                variant="ghost"
                scale="large"
                onClick={() => setStep(1)}
              >
                ← Quay lại
              </Button>
              <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
                <button
                  type="button"
                  className={styles.skipButton}
                  onClick={handleStep2Proceed}
                  disabled={submitting}
                >
                  Bỏ qua, tôi sẽ kết nối sau
                </button>
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
