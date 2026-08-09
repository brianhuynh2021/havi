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
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

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

            <label className={styles.label} htmlFor="shop-name">
              Tên tiệm
            </label>
            <Input
              id="shop-name"
              placeholder="Spa An Nhiên"
              value={shopName}
              onChange={(e) => setShopName(e.target.value)}
            />

            <div className={styles.industryGrid}>
              {industryOptions.map((option) => (
                <button
                  key={option.value}
                  type="button"
                  aria-pressed={industry === option.value}
                  className={`${styles.industryCard} ${
                    industry === option.value ? styles.industryCardActive : ""
                  }`}
                  onClick={() => setIndustry(option.value)}
                >
                  {option.label}
                  {option.recommended ? (
                    <span className={styles.recommendedTag}>Đề xuất pilot</span>
                  ) : null}
                </button>
              ))}
            </div>

            {error ? (
              <p className={styles.error} role="alert">
                {error}
              </p>
            ) : null}

            <Button
              variant="primary"
              disabled={!industry || submitting}
              onClick={submitIndustry}
            >
              {submitting ? "Đang tạo tiệm…" : "Tiếp tục"}
            </Button>
          </>
        ) : step === 2 ? (
          <>
            <h1 className={styles.title}>Nối kênh Facebook Page</h1>
            <p className={styles.subtitle}>
              Havi cần quyền đăng bài trên Page để giúp chị/anh đăng đúng lịch.
            </p>
            <ConnectionList onUsableChange={setConnected} />
            <div className={styles.stepActions}>
              {/* Không có nút quay lại bước 1: tiệm đã tạo thật rồi, bấm lại sẽ
                  tạo tiệm thứ hai trùng tên. Đổi tên/ngành làm ở Cài đặt. */}
              <Button variant="outline" onClick={() => setStep(3)}>
                Để sau
              </Button>
              <Button
                variant="primary"
                disabled={!connected}
                onClick={() => setStep(3)}
              >
                Tiếp tục
              </Button>
            </div>
          </>
        ) : (
          <>
            <h1 className={styles.title}>Havi đang học về tiệm của chị/anh</h1>
            <p className={styles.subtitle}>
              Chỉ mất chưa đầy một phút — Havi đọc brand voice và chuẩn bị bản
              nháp đầu tiên.
            </p>
            {!learning ? (
              <Button variant="primary" onClick={() => setLearning(true)}>
                Bắt đầu
              </Button>
            ) : (
              <div className={styles.learningCard}>
                <span className={styles.spinner} aria-hidden="true" />
                <p className={styles.learningText}>
                  Havi đã sẵn sàng — tạo bản nháp đầu tiên ở tab Tạo nội dung.
                </p>
                <Button variant="primary" onClick={goToApp}>
                  Vào app
                </Button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
