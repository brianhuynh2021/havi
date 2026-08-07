"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { industryOptions, type IndustryOption } from "./onboarding.fixture";
import styles from "./onboarding.module.css";

type Step = 1 | 2 | 3;

const stepLabels = ["Chọn ngành", "Nối kênh", "Havi bắt đầu học"];

export function OnboardingScreen() {
  const router = useRouter();
  const [step, setStep] = useState<Step>(1);
  const [industry, setIndustry] = useState<IndustryOption["value"] | null>(null);
  const [connected, setConnected] = useState(false);
  const [learning, setLearning] = useState(false);

  function goToApp() {
    router.push("/");
  }

  return (
    <div className={styles.wizard}>
      <div className={styles.brand}>
        <div className={styles.brandMark}>Ha</div>
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
            <h1 className={styles.title}>Tiệm của chị/anh thuộc ngành nào?</h1>
            <p className={styles.subtitle}>
              Havi sẽ dùng thông tin này để viết bài đúng giọng, đúng ngành.
            </p>
            <div className={styles.industryGrid}>
              {industryOptions.map((option) => (
                <button
                  key={option.value}
                  type="button"
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
            <Button
              variant="primary"
              disabled={!industry}
              onClick={() => setStep(2)}
            >
              Tiếp tục
            </Button>
          </>
        ) : step === 2 ? (
          <>
            <h1 className={styles.title}>Nối kênh Facebook Page</h1>
            <p className={styles.subtitle}>
              Havi cần quyền đăng bài trên Page để giúp chị/anh đăng đúng lịch.
            </p>
            {connected ? (
              <div className={styles.connectedCard}>
                <span className={styles.connectedDot} aria-hidden="true" />
                Đã kết nối Page &quot;Spa An Nhiên&quot;
              </div>
            ) : (
              <Button variant="primary" onClick={() => setConnected(true)}>
                Kết nối Facebook Page
              </Button>
            )}
            <div className={styles.stepActions}>
              <Button variant="outline" onClick={() => setStep(1)}>
                Quay lại
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
                  Havi đã sẵn sàng — bản nháp đầu tiên đang chờ ở tab Tạo nội
                  dung.
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
