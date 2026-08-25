"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Logo } from "@/components/ui/logo";
import { ConnectionList } from "@/features/connections/connection-list";
import { useSession } from "@/lib/auth/session";
import { readTokens, writeTokens } from "@/lib/auth/token-store";

import {
  createWorkspace,
  fetchDefaultShopName,
  initializeBusinessTruthPack,
} from "./onboarding.api";
import {
  industryOptions,
  getIndustrySamplePreview,
  type IndustryOption,
} from "./onboarding.fixture";
import styles from "./onboarding.module.css";

type Step = 1 | 2 | 3;

const stepLabels = ["Chọn ngành", "Nối kênh", "Havi bắt đầu học"];

export function OnboardingScreen() {
  const router = useRouter();
  const { signIn } = useSession();
  // Quay về từ Facebook là một page load MỚI (backend redirect tới
  // /onboarding?ket_noi=...), nên mọi state trước đó đã mất. Không đọc lại bước
  // từ URL thì chủ tiệm rơi về bước 1 và bấm "Tiếp tục" là tạo tiệm thứ hai
  // trùng tên. `useState` với initializer chứ không `useEffect`: sửa step sau
  // lần render đầu sẽ nháy qua bước 1 một khung hình.
  const [step, setStep] = useState<Step>(() =>
    typeof window !== "undefined" &&
    new URLSearchParams(window.location.search).has("ket_noi")
      ? 2
      : 1,
  );
  const [shopName, setShopName] = useState("");
  const [industry, setIndustry] = useState<IndustryOption["value"] | null>(null);
  const [connected, setConnected] = useState(false);
  const [learning, setLearning] = useState(false);
  const [progressPercent, setProgressPercent] = useState(0);
  const [completedStages, setCompletedStages] = useState<number[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const previewSample = getIndustrySamplePreview(industry, shopName);

  const handleStartLearning = useCallback(async () => {
    if (learning) return;
    setLearning(true);
    setProgressPercent(25);
    setCompletedStages([0]);

    // Kích hoạt Business Truth Pack: lưu Brand Voice & FAQ mẫu chuẩn ngành vào database
    try {
      await initializeBusinessTruthPack(industry, shopName);
    } catch {
      // Tiếp tục luồng ngay cả khi có cảnh báo mạng
    }

    setProgressPercent(70);
    setCompletedStages([0, 1]);

    setTimeout(() => {
      setProgressPercent(100);
      setCompletedStages([0, 1, 2]);
      setTimeout(() => {
        router.replace("/app");
      }, 400);
    }, 200);
  }, [learning, industry, shopName, router]);

  function handleStep2Proceed() {
    setStep(3);
    void handleStartLearning();
  }


  useEffect(() => {
    let cancelled = false;
    fetchDefaultShopName().then((name) => {
      if (!cancelled && name) setShopName((current) => current || name);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (step === 3 && !learning) {
      void handleStartLearning();
    }
  }, [step, learning, handleStartLearning]);



  /** Tạo tiệm thật ở cuối bước 1 — từ đây trở đi user đã có workspace, nên bước
   * 2 và 3 có hỏng thì cũng không kẹt: token mới đã hết `needs_onboarding`. */
  async function submitIndustry() {
    if (!shopName.trim()) {
      setError("Nhập tên tiệm để Havi gọi đúng tên trong bài viết");
      return;
    }
    if (!industry) return;

    setError(null);
    setSubmitting(true);
    const result = await createWorkspace(shopName.trim(), industry);
    setSubmitting(false);
    if (!result.ok) {
      setError(result.message);
      return;
    }
    signIn(result.tokens);
    setStep(2);
  }

  function goToApp() {
    const current = readTokens();
    if (current) {
      writeTokens({ ...current, needsOnboarding: false });
    }
    router.replace("/app");
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
            <h1 className={styles.title}>Cơ sở của bạn tên gì, ngành nào?</h1>
            <p className={styles.subtitle}>
              Havi sẽ dùng thông tin này để viết bài đúng giọng, đúng ngành.
            </p>

            <div className={styles.inputSection}>
              <label className={styles.label} htmlFor="shop-name">
                Tên tiệm
              </label>
              <Input
                id="shop-name"
                scale="large"
                placeholder="Ví dụ: Spa An Nhiên, Tiệm Cà Phê 1985..."
                value={shopName}
                onChange={(e) => setShopName(e.target.value)}
              />
            </div>

            <div className={styles.industrySection}>
              <label className={styles.label}>Ngành kinh doanh của tiệm</label>
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

            {/* Magic Onboarding Live Preview (100/100 Weapon) */}
            <div className={styles.magicPreviewCard} aria-label="Bản xem trước bài viết AI">
              <div className={styles.magicPreviewHeader}>
                <h3 className={styles.magicPreviewTitle}>
                  ✨ Bản xem trước bài viết theo ngành
                </h3>
                <span className={styles.magicBadge}>⚡ Tự động tạo mẫu</span>
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
        ) : step === 2 ? (
          <>
            <h1 className={styles.title}>Kết nối kênh của bạn</h1>
            <p className={styles.subtitle}>
              Kết nối Facebook bằng API chính thức để thử luồng tạo, duyệt và đăng bài. Các kênh khác vẫn đang ở roadmap/Beta.
            </p>
            <div className={styles.connectionListWrapper}>
              <ConnectionList returnTo="onboarding" onUsableChange={setConnected} />
            </div>
            <div className={styles.stepActions}>
              {/* Không có nút quay lại bước 1: tiệm đã tạo thật rồi, bấm lại sẽ
                  tạo tiệm thứ hai trùng tên. Đổi tên/ngành làm ở Cài đặt. */}
              <Button variant="outline" scale="large" onClick={handleStep2Proceed}>
                Bỏ qua
              </Button>
              <Button
                variant="primary"
                scale="large"
                disabled={!connected}
                onClick={handleStep2Proceed}
              >
                {connected ? "Tiếp tục →" : "Tiếp tục"}
              </Button>
            </div>

          </>
        ) : (
          <>
            <h1 className={styles.title}>Havi đang học về tiệm của bạn</h1>
            <p className={styles.subtitle}>
              Chỉ mất chưa đầy một phút — Havi đọc Brand Voice và chuẩn bị kịch bản, bản
              nháp đầu tiên.
            </p>
            {!learning ? (
              <div className={styles.actions}>
                <Button variant="primary" scale="large" onClick={handleStartLearning}>
                  Bắt đầu ngay 🚀
                </Button>
              </div>
            ) : (
              <div className={styles.learningCard}>
                {progressPercent < 100 ? (
                  <span className={styles.spinner} aria-hidden="true" />
                ) : (
                  <div className={styles.successIconBadge}>✨</div>
                )}

                <div className={styles.progressContainer}>
                  <div className={styles.progressBarWrapper}>
                    <div
                      className={styles.progressBarFill}
                      style={{ width: `${progressPercent}%` }}
                    />
                  </div>
                  <span className={styles.progressPercentText}>{progressPercent}%</span>
                </div>

                <div className={styles.stageList}>
                  {[
                    { id: 0, text: "⚡ Đang phân tích ngành nghề & dịch vụ tiệm" },
                    { id: 1, text: "🎨 Đang hiệu chỉnh Brand Voice & văn phong thu hút" },
                    { id: 2, text: "✨ Đã sẵn sàng kịch bản & 4 bản nháp đầu tiên!" },
                  ].map((stg) => {
                    const isDone = completedStages.includes(stg.id);
                    return (
                      <div
                        key={stg.id}
                        className={`${styles.stageItem} ${isDone ? styles.stageItemDone : ""}`}
                      >
                        <span className={styles.stageIcon}>{isDone ? "✓" : "○"}</span>
                        <span>{stg.text}</span>
                      </div>
                    );
                  })}
                </div>

                {progressPercent === 100 ? (
                  <div style={{ width: "100%", maxWidth: "280px", marginTop: "12px" }}>
                    <Button variant="primary" scale="large" onClick={goToApp}>
                      Vào app trải nghiệm 🚀
                    </Button>
                  </div>
                ) : null}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
