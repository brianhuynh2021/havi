"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/state-views";
import { useLanguage } from "@/lib/i18n/language-context";
import {
  fetchActiveGoal,
  fetchActiveRoadmap,
  fetchEvidenceList,
  type ActiveRoadmapData,
  type EvidenceLog,
  type Goal,
} from "@/features/roadmap/roadmap.api";
import styles from "./evidence.module.css";

export function EvidenceScreen() {
  const { t } = useLanguage();
  const [goal, setGoal] = useState<Goal | null>(null);
  const [roadmapData, setRoadmapData] = useState<ActiveRoadmapData | null>(null);
  const [evidenceList, setEvidenceList] = useState<EvidenceLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    const [goalRes, roadmapRes, evidenceRes] = await Promise.all([
      fetchActiveGoal(),
      fetchActiveRoadmap(),
      fetchEvidenceList(),
    ]);

    if (!goalRes.ok) {
      setError(goalRes.message);
      setLoading(false);
      return;
    }
    setGoal(goalRes.data);
    if (roadmapRes.ok) {
      setRoadmapData(roadmapRes.data);
    }
    if (evidenceRes.ok) {
      setEvidenceList(evidenceRes.data);
    }
    setLoading(false);
  };

  useEffect(() => {
    loadData();
  }, []);

  if (loading) {
    return <LoadingState title={t({ vi: "Đang tải bằng chứng & kết quả...", en: "Loading evidence & outcomes..." })} />;
  }

  if (error) {
    return <ErrorState title={error} action={<Button onClick={loadData}>{t({ vi: "Thử lại", en: "Retry" })}</Button>} />;
  }

  const completedTasks = (roadmapData?.tasks ?? []).filter((t) => t.status === "completed");

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h1 className={styles.title}>{t({ vi: "Bằng Chứng & Kết Quả Thực Tế", en: "Evidence & Verified Outcomes" })}</h1>
        <p className={styles.subtitle}>
          {t({
            vi: "Havi chỉ ghi nhận kết quả và đánh giá lộ trình dựa trên bằng chứng thật (VietQR, Check-in, Lead đã chốt, Bàn giao).",
            en: "Havi evaluates progress and reviews roadmaps exclusively from verified evidence.",
          })}
        </p>
      </header>

      {goal ? (
        <section className={styles.goalProofCard}>
          <div className={styles.proofHeader}>
            <div>
              <span className={styles.proofBadge}>🎯 TIÊU CHUẨN XÁC MINH CỦA MỤC TIÊU</span>
              <h2 className={styles.proofTitle}>{goal.title}</h2>
              <p className={styles.proofText}>
                📌 <strong>Bằng chứng yêu cầu:</strong> {goal.evidence_definition}
              </p>
            </div>
            <div className={styles.progressCircle}>
              <span style={{ fontSize: "20px", fontWeight: 800, color: "#10b981" }}>
                {completedTasks.length}/{roadmapData?.tasks.length ?? 0}
              </span>
              <span style={{ fontSize: "11px", color: "var(--text-secondary)" }}>Đã hoàn thành</span>
            </div>
          </div>
        </section>
      ) : null}

      <section className={styles.evidenceListSection}>
        <h2 className={styles.sectionTitle}>
          📋 Nhật ký bằng chứng kết quả ({evidenceList.length || completedTasks.length})
        </h2>

        {evidenceList.length === 0 && completedTasks.length === 0 ? (
          <EmptyState
            title={t({ vi: "Chưa có bằng chứng kết quả nào", en: "No verified evidence yet" })}
            body={t({
              vi: "Khi bạn hoàn thành một nhiệm vụ hôm nay và đính kèm kết quả, bằng chứng sẽ xuất hiện ở đây.",
              en: "When you complete a daily action and submit evidence, it will appear here.",
            })}
            action={
              <Link href="/app" style={{ background: "#2563eb", color: "#fff", padding: "10px 18px", borderRadius: "8px", textDecoration: "none", fontWeight: 700 }}>
                Đi đến việc Hôm nay ➔
              </Link>
            }
          />
        ) : (
          <div className={styles.evidenceGrid}>
            {evidenceList.map((ev) => (
              <article key={ev.id} className={styles.evidenceCard}>
                <div className={styles.cardHeader}>
                  <strong className={styles.taskName}>Nguồn: {ev.source.toUpperCase()} ({ev.evidence_type})</strong>
                  <span className={styles.completedBadge}>
                    ✓ Độ tin cậy {Math.round(ev.confidence * 100)}%
                  </span>
                </div>
                <div className={styles.evidenceBody}>
                  &ldquo;{ev.value_text}&rdquo;
                </div>
                <div className={styles.cardFooter}>
                  <span>{ev.value_number ? `Giá trị: ${ev.value_number.toLocaleString("vi-VN")}` : "Đã xác nhận"}</span>
                  <span>{new Date(ev.created_at).toLocaleDateString("vi-VN")}</span>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

