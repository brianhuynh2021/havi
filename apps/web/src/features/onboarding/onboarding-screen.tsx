"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ConnectionList } from "@/features/connections/connection-list";
import { useSession } from "@/lib/auth/session";
import { createWorkspace, fetchDefaultShopName } from "./onboarding.api";
import { industryOptions, type IndustryOption } from "./onboarding.fixture";
import styles from "./onboarding.module.css";
import { Logo } from "@/components/ui/logo";

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

  useEffect(() => {
    if (!learning) return;
    setProgressPercent(25);
    setCompletedStages([0]);

    const timer1 = setTimeout(() => {
      setProgressPercent(70);
      setCompletedStages([0, 1]);
    }, 400);

    const timer2 = setTimeout(() => {
      setProgressPercent(100);
      setCompletedStages([0, 1, 2]);
    }, 900);

    return () => {
      clearTimeout(timer1);
      clearTimeout(timer2);
    };
  }, [learning]);

  // Tên đã nhập lúc đăng ký thường chính là tên tiệm — điền sẵn để chủ tiệm
  // không phải gõ lại. Vẫn sửa được: nhiều người đăng ký bằng tên riêng.
  useEffect(() => {
    let cancelled = false;
    fetchDefaultShopName().then((name) => {
      if (!cancelled && name) setShopName((current) => current || name);
    });
    return () => {
      cancelled = true;
    };
  }, []);

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
    router.replace("/");
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
            <h1 className={styles.title}>Tiệm của chị/anh tên gì, ngành nào?</h1>
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
              Kết nối Facebook, Google Maps SEO, TikTok, YouTube Shorts để Havi tự động đăng bài, tạo video ngắn và chăm sóc khách 24/7.
            </p>
            <div className={styles.connectionListWrapper}>
              <ConnectionList returnTo="onboarding" onUsableChange={setConnected} />
            </div>
            <div className={styles.stepActions}>
              {/* Không có nút quay lại bước 1: tiệm đã tạo thật rồi, bấm lại sẽ
                  tạo tiệm thứ hai trùng tên. Đổi tên/ngành làm ở Cài đặt. */}
              <Button variant="outline" scale="large" onClick={() => setStep(3)}>
                Bỏ qua
              </Button>
              <Button
                variant="primary"
                scale="large"
                disabled={!connected}
                onClick={() => setStep(3)}
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
                <Button variant="primary" scale="large" onClick={() => setLearning(true)}>
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
                    { id: 2, text: "✨ Đã sẵn sàng kịch bản & 3 bản nháp đầu tiên!" },
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
