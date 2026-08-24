"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/state-views";
import { ToastContainer, type ToastItem } from "@/components/ui/toast";
import { useLanguage } from "@/lib/i18n/language-context";
import {
  createWeeklyReview,
  deleteGoal,
  fetchActiveGoal,
  fetchActiveRoadmap,
  fetchRoadmapHistory,
  generateRoadmap,
  restoreRoadmap,
  type ActiveRoadmapData,
  type Goal,
  type Roadmap,
} from "./roadmap.api";
import { GoalCreateModal } from "./goal-create-modal";
import styles from "./roadmap.module.css";

export function RoadmapScreen() {
  const { t } = useLanguage();
  const [goal, setGoal] = useState<Goal | null>(null);
  const [roadmapData, setRoadmapData] = useState<ActiveRoadmapData | null>(null);
  const [history, setHistory] = useState<Roadmap[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isGoalModalOpen, setIsGoalModalOpen] = useState(false);
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const toastCounterRef = useRef(0);

  const addToast = useCallback((toast: Omit<ToastItem, "id">) => {
    toastCounterRef.current += 1;
    const id = `toast-${toastCounterRef.current}`;
    setToasts((prev) => [...prev, { ...toast, id }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4000);
  }, []);

  const dismissToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  // Review Modal State
  const [showReviewModal, setShowReviewModal] = useState(false);
  const [completedSummary, setCompletedSummary] = useState("");
  const [evidenceSummary, setEvidenceSummary] = useState("");
  const [obstaclesSummary, setObstaclesSummary] = useState("");
  const [decision, setDecision] = useState<"continue" | "improve" | "pivot" | "pause" | "stop">("continue");
  const [isSubmittingReview, setIsSubmittingReview] = useState(false);

  // History Drawer State
  const [showHistory, setShowHistory] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    const [goalRes, roadmapRes, historyRes] = await Promise.all([
      fetchActiveGoal(),
      fetchActiveRoadmap(),
      fetchRoadmapHistory(),
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
    if (historyRes.ok) {
      setHistory(historyRes.data);
    }
    setLoading(false);
  }, []);

  const handleResetGoal = async () => {
    if (!goal) return;
    const confirmed = window.confirm(
      "Bạn có chắc chắn muốn đặt lại (hủy) mục tiêu hiện tại để chọn lại mục tiêu mới không?"
    );
    if (!confirmed) return;
    const res = await deleteGoal(goal.id);
    if (res.ok) {
      setGoal(null);
      setRoadmapData(null);
      addToast({ type: "info", title: "Đã đặt lại mục tiêu", description: "Bạn có thể thiết lập mục tiêu chiến lược mới." });
      void loadData();
    } else {
      addToast({ type: "error", title: "Lỗi đặt lại mục tiêu", description: res.message });
    }
  };

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const handleGenerateRoadmap = async () => {
    if (!goal) return;
    setIsGenerating(true);
    const res = await generateRoadmap(goal.id);
    setIsGenerating(false);
    if (res.ok) {
      setRoadmapData(res.data);
      addToast({ type: "success", title: "⚡ Đã tái tạo lộ trình!", description: "Lộ trình mới đã sẵn sàng cho cơ sở." });
      loadData();
    } else {
      addToast({ type: "error", title: "Lỗi tạo lộ trình", description: res.message });
    }
  };

  const handleRestoreRoadmap = async (roadmapId: string) => {
    const res = await restoreRoadmap(roadmapId);
    if (res.ok) {
      setRoadmapData(res.data);
      setShowHistory(false);
      addToast({ type: "success", title: "Đã khôi phục phiên bản", description: "Lộ trình đã được khôi phục thành công." });
      loadData();
    } else {
      addToast({ type: "error", title: "Lỗi khôi phục lộ trình", description: res.message });
    }
  };

  const handleSubmitReview = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!roadmapData) return;
    setIsSubmittingReview(true);
    const res = await createWeeklyReview(roadmapData.roadmap.id, {
      completed_summary: completedSummary,
      evidence_summary: evidenceSummary,
      obstacles_summary: obstaclesSummary,
      decision,
    });
    setIsSubmittingReview(false);
    if (res.ok) {
      setShowReviewModal(false);
      setCompletedSummary("");
      setEvidenceSummary("");
      setObstaclesSummary("");
      addToast({ type: "success", title: "✓ Đã ghi nhận tổng kết tuần", description: "Báo cáo chu kỳ đã được cập nhật thành công." });
      loadData();
    } else {
      addToast({ type: "error", title: "Lỗi lưu tổng kết tuần", description: res.message });
    }
  };

  if (loading) {
    return <LoadingState title={t({ vi: "Đang tải lộ trình mục tiêu...", en: "Loading goal roadmap..." })} />;
  }

  if (error) {
    return <ErrorState title={error} action={<Button onClick={loadData}>{t({ vi: "Thử lại", en: "Retry" })}</Button>} />;
  }

  if (!goal) {
    return (
      <div className={styles.container}>
        <EmptyState
          title={t({ vi: "Chưa có mục tiêu nào được tạo", en: "No active goal found" })}
          body={t({
            vi: "Để Havi sinh lộ trình thực hiện, hãy bắt đầu bằng việc thiết lập mục tiêu đầu tiên.",
            en: "Set up your first goal to let Havi build your multi-horizon execution roadmap.",
          })}
          action={
            <Button variant="primary" onClick={() => setIsGoalModalOpen(true)}>
              🚀 Tạo Mục Tiêu Đầu Tiên (1 chạm)
            </Button>
          }
        />
        <GoalCreateModal
          isOpen={isGoalModalOpen}
          onClose={() => setIsGoalModalOpen(false)}
          onGoalCreated={(newGoal, newRoadmap) => {
            setGoal(newGoal);
            if (newRoadmap) setRoadmapData(newRoadmap);
            loadData();
          }}
        />
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "10px" }}>
          <div>
            <h1 className={styles.title}>{t({ vi: "Lộ Trình Thực Hiện Mục Tiêu", en: "Goal Execution Roadmap" })}</h1>
            <p className={styles.subtitle}>
              Mục tiêu: <strong>{goal.title}</strong> · Phiên bản v{roadmapData?.roadmap.version || 1}
            </p>
          </div>
          <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
            <Button variant="outline" onClick={() => setIsGoalModalOpen(true)}>
              🎯 Đổi mục tiêu
            </Button>
            <Button variant="outline" onClick={handleResetGoal} style={{ color: "#dc2626", borderColor: "rgba(239, 68, 68, 0.4)" }}>
              🗑️ Đặt lại từ đầu
            </Button>
            <Button variant="outline" onClick={() => setShowHistory(!showHistory)}>
              📜 Lịch sử ({history.length})
            </Button>
            <Button variant="primary" onClick={() => setShowReviewModal(true)}>
              📋 Đánh giá tuần
            </Button>
          </div>
        </div>
      </header>

      {/* History Drawer */}
      {showHistory ? (
        <section className={styles.assumptionsCard} style={{ background: "#eff6ff", borderColor: "#bfdbfe" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
            <strong style={{ color: "#1e40af" }}>📜 Lịch sử các phiên bản Lộ trình</strong>
            <button
              type="button"
              onClick={() => setShowHistory(false)}
              style={{ background: "transparent", border: "none", cursor: "pointer", color: "#64748b" }}
            >
              ✕ Đóng
            </button>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            {history.map((h) => (
              <div
                key={h.id}
                style={{
                  padding: "10px 14px",
                  background: "#ffffff",
                  borderRadius: "8px",
                  border: "1px solid #dbeafe",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <div>
                  <strong>Phiên bản v{h.version}: {h.title}</strong>
                  <div style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
                    Tạo ngày: {new Date(h.created_at).toLocaleDateString("vi-VN")} · Trạng thái: {h.status}
                  </div>
                </div>
                {h.id !== roadmapData?.roadmap.id ? (
                  <Button variant="outline" disabled={isGenerating} onClick={() => handleRestoreRoadmap(h.id)}>
                    Khôi phục bản này
                  </Button>
                ) : (
                  <span style={{ fontSize: "12px", color: "#10b981", fontWeight: 700 }}>Đang sử dụng</span>
                )}
              </div>
            ))}
          </div>
        </section>
      ) : null}

      {!roadmapData ? (
        <EmptyState
          title="Lộ trình chưa khởi tạo"
          body="Bấm nút bên dưới để Havi tự động phân rã kế hoạch đa tầng cho mục tiêu này."
          action={
            <Button variant="primary" disabled={isGenerating} onClick={handleGenerateRoadmap}>
              ⚡ Sinh Lộ Trình Ngay
            </Button>
          }
        />
      ) : (
        <>
          {/* 90-day Direction Horizon */}
          <section className={styles.horizonCard}>
            <span className={styles.horizonBadge}>🔭 TẦNG 1: ĐỊNH HƯỚNG 90 NGÀY</span>
            <p className={styles.horizonText}>{roadmapData.roadmap.horizon_90d}</p>
          </section>

          {/* 30-day Focus Horizon */}
          <section className={styles.horizonCard}>
            <span className={styles.horizonBadge} style={{ background: "rgba(16, 185, 129, 0.1)", color: "#059669" }}>
              🎯 TẦNG 2: TRỌNG TÂM 30 NGÀY
            </span>
            <p className={styles.horizonText}>{roadmapData.roadmap.horizon_30d}</p>
          </section>

          {/* 7-day Commitment Horizon */}
          <section className={styles.horizonCard}>
            <span className={styles.horizonBadge} style={{ background: "rgba(245, 158, 11, 0.1)", color: "#d97706" }}>
              ⚡ TẦNG 3: CAM KẾT 7 NGÀY
            </span>
            <p className={styles.horizonText}>{roadmapData.roadmap.horizon_7d}</p>
          </section>

          {/* Assumptions & Confidence */}
          {roadmapData.roadmap.assumptions && roadmapData.roadmap.assumptions.length > 0 ? (
            <section className={styles.assumptionsCard}>
              <strong style={{ fontSize: "14px", color: "var(--text-primary)" }}>
                💡 Giả định cốt lõi & Độ tin cậy ({Math.round(roadmapData.roadmap.confidence_score * 100)}%):
              </strong>
              <ul className={styles.assumptionList}>
                {roadmapData.roadmap.assumptions.map((assump, i) => (
                  <li key={i}>{assump}</li>
                ))}
              </ul>
            </section>
          ) : null}

          {/* Tasks Breakdown */}
          <section className={styles.tasksCard}>
            <div className={styles.tasksHeader}>
              <h2 className={styles.tasksTitle}>
                📋 Danh sách nhiệm vụ ({roadmapData.tasks.length})
              </h2>
              <Link href="/app" style={{ color: "#2563eb", fontWeight: 700, fontSize: "13px", textDecoration: "none" }}>
                Đi đến việc Hôm nay ➔
              </Link>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
              {roadmapData.tasks.map((task, idx) => (
                <div
                  key={task.id}
                  style={{
                    padding: "14px",
                    borderRadius: "8px",
                    background: task.status === "completed" ? "rgba(16, 185, 129, 0.05)" : "var(--bg-canvas)",
                    border: "1px solid var(--border-color)",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                >
                  <div>
                    <span style={{ fontWeight: 700, color: "#2563eb", marginRight: "8px" }}>#{idx + 1}</span>
                    <strong style={{ fontSize: "14px" }}>{task.title}</strong>
                    <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "4px" }}>
                      {task.why_this_is_next} · Tiêu chí: {task.done_rule}
                    </div>
                  </div>
                  <div>
                    {task.status === "completed" ? (
                      <span style={{ color: "#10b981", fontWeight: 700, fontSize: "13px" }}>✓ Đã hoàn thành</span>
                    ) : (
                      <span style={{ color: "#d97706", fontWeight: 700, fontSize: "13px" }}>⏳ Đang chờ</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </section>
        </>
      )}

      {/* Weekly Review Modal */}
      {showReviewModal ? (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0, 0, 0, 0.5)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            padding: "20px",
          }}
          role="dialog"
          aria-modal="true"
        >
          <div
            style={{
              background: "var(--bg-surface)",
              borderRadius: "16px",
              maxWidth: "560px",
              width: "100%",
              padding: "24px",
              display: "flex",
              flexDirection: "column",
              gap: "16px",
            }}
          >
            <h3 style={{ margin: 0, fontSize: "18px", fontWeight: 800 }}>📋 Đánh Giá Tiến Độ Tuần (Weekly Review)</h3>
            <p style={{ margin: 0, fontSize: "13px", color: "var(--text-secondary)" }}>
              Dựa trên bằng chứng và khó khăn thực tế, Havi sẽ cùng bạn quyết định bước tiếp theo.
            </p>

            <div>
              <label style={{ fontSize: "13px", fontWeight: 700, display: "block", marginBottom: "4px" }}>
                1. Những việc bạn đã hoàn thành tuần này?
              </label>
              <textarea
                style={{ width: "100%", padding: "8px 12px", borderRadius: "8px", border: "1px solid var(--border-color)", fontSize: "13px" }}
                rows={2}
                placeholder="VD: Đã duyệt 3 bài viết và đăng lên Fanpage..."
                value={completedSummary}
                onChange={(e) => setCompletedSummary(e.target.value)}
              />
            </div>

            <div>
              <label style={{ fontSize: "13px", fontWeight: 700, display: "block", marginBottom: "4px" }}>
                2. Bằng chứng hoặc kết quả thực tế xuất hiện?
              </label>
              <textarea
                style={{ width: "100%", padding: "8px 12px", borderRadius: "8px", border: "1px solid var(--border-color)", fontSize: "13px" }}
                rows={2}
                placeholder="VD: Có 5 tin nhắn quan tâm, 2 học viên đóng cọc VietQR..."
                value={evidenceSummary}
                onChange={(e) => setEvidenceSummary(e.target.value)}
              />
            </div>

            <div>
              <label style={{ fontSize: "13px", fontWeight: 700, display: "block", marginBottom: "4px" }}>
                3. Bạn gặp trở ngại hoặc rào cản gì?
              </label>
              <textarea
                style={{ width: "100%", padding: "8px 12px", borderRadius: "8px", border: "1px solid var(--border-color)", fontSize: "13px" }}
                rows={2}
                placeholder="VD: Thiếu người quay clip, thời gian phản hồi tin nhắn còn chậm..."
                value={obstaclesSummary}
                onChange={(e) => setObstaclesSummary(e.target.value)}
              />
            </div>

            <div>
              <label style={{ fontSize: "13px", fontWeight: 700, display: "block", marginBottom: "4px" }}>
                4. Quyết định tiếp theo cho Lộ trình:
              </label>
              <select
                style={{ width: "100%", padding: "10px 12px", borderRadius: "8px", border: "1px solid var(--border-color)", fontSize: "14px" }}
                value={decision}
                onChange={(e) => setDecision(e.target.value as "continue" | "improve" | "pivot" | "pause" | "stop")}
              >
                <option value="continue">✅ Tiếp tục (Giữ nguyên chiến lược, tiếp tục làm nhiệm vụ)</option>
                <option value="improve">⚡ Cải tiến (Điều chỉnh thông điệp/chiến thuật & sinh phiên bản mới)</option>
                <option value="pivot">🔄 Đổi hướng (Đổi giả định cốt lõi & sinh lộ trình mới)</option>
                <option value="pause">⏸️ Tạm dừng (Giữ nguyên trạng thái để chờ tài nguyên)</option>
                <option value="stop">🏁 Kết thúc (Mục tiêu đã hoàn tất hoặc không còn phù hợp)</option>
              </select>
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "8px" }}>
              <Button variant="outline" onClick={() => setShowReviewModal(false)}>
                Huỷ
              </Button>
              <Button variant="primary" disabled={isSubmittingReview} onClick={handleSubmitReview}>
                {isSubmittingReview ? "Đang lưu..." : "Xác nhận & Cập nhật"}
              </Button>
            </div>
          </div>
        </div>
      ) : null}

      {/* Goal Creation Modal */}
      <GoalCreateModal
        isOpen={isGoalModalOpen}
        onClose={() => setIsGoalModalOpen(false)}
        onGoalCreated={(newGoal, newRoadmap) => {
          setGoal(newGoal);
          if (newRoadmap) setRoadmapData(newRoadmap);
          loadData();
        }}
      />

      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
    </div>
  );
}

