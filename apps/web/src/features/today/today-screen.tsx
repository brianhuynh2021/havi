"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/state-views";
import { useLanguage } from "@/lib/i18n/language-context";
import { apiClient } from "@/lib/api-client/client";
import { readTokens } from "@/lib/auth/token-store";
import {
  blockTask,
  completeTask,
  createGoal,
  deleteGoal,
  fetchActiveGoal,
  fetchActiveRoadmap,
  fetchTodayAction,
  generateRoadmap,
  type ActiveRoadmapData,
  type Goal,
  type RoadmapTask,
} from "@/features/roadmap/roadmap.api";
import {
  GoalCreateModal,
  getGoalTemplates,
  formatHorizonLabel,
  type GoalTemplate,
} from "@/features/roadmap/goal-create-modal";
import styles from "./today.module.css";

export function TodayScreen() {
  const { lang, t } = useLanguage();
  const [goal, setGoal] = useState<Goal | null>(null);
  const [roadmapData, setRoadmapData] = useState<ActiveRoadmapData | null>(null);
  const [todayAction, setTodayAction] = useState<RoadmapTask | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [workspaceIndustry, setWorkspaceIndustry] = useState<string>("spa");
  const [selectedHorizon, setSelectedHorizon] = useState<number>(7);
  const [isCustomHorizonOpen, setIsCustomHorizonOpen] = useState(false);
  const [customHorizonValue, setCustomHorizonValue] = useState(9);
  const [customHorizonUnit, setCustomHorizonUnit] = useState<"days" | "weeks" | "months" | "years">("months");

  // Modals & Action States
  const [isGoalModalOpen, setIsGoalModalOpen] = useState(false);
  const [evidenceModalTask, setEvidenceModalTask] = useState<RoadmapTask | null>(null);
  const [evidenceText, setEvidenceText] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [stuckTask, setStuckTask] = useState<RoadmapTask | null>(null);
  const [stuckReason, setStuckReason] = useState("");

  const loadData = async () => {
    setLoading(true);
    setError(null);
    const [goalRes, roadmapRes, todayRes] = await Promise.all([
      fetchActiveGoal(),
      fetchActiveRoadmap(),
      fetchTodayAction(),
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
    if (todayRes.ok) {
      setTodayAction(todayRes.data);
    }
    setLoading(false);
  };

  useEffect(() => {
    loadData();
    const activeId = readTokens()?.activeWorkspaceId;
    apiClient
      .GET("/workspaces")
      .then(({ data }) => {
        if (!data) return;
        const list = data as Array<{ id: string; industry: string }>;
        const active = list.find((w) => w.id === activeId) ?? list[0];
        if (active?.industry) {
          setWorkspaceIndustry(active.industry);
        }
      })
      .catch(() => {});
  }, []);

  const quickTemplates = useMemo(
    () => getGoalTemplates(workspaceIndustry, selectedHorizon),
    [workspaceIndustry, selectedHorizon]
  );

  const calculatedCustomDays = useMemo(() => {
    let d = customHorizonValue;
    if (customHorizonUnit === "weeks") d = customHorizonValue * 7;
    if (customHorizonUnit === "months") d = customHorizonValue * 30;
    if (customHorizonUnit === "years") d = customHorizonValue * 365;
    return Math.max(1, d);
  }, [customHorizonValue, customHorizonUnit]);

  const handleLaunchTemplate = async (template: GoalTemplate) => {
    setIsSubmitting(true);
    const goalRes = await createGoal({
      title: template.title,
      category: template.category,
      evidence_definition: template.evidence_definition,
      description: template.description,
      weekly_capacity_hours: template.weekly_capacity_hours,
    });
    if (!goalRes.ok) {
      alert(goalRes.message);
      setIsSubmitting(false);
      return;
    }
    setGoal(goalRes.data);
    const roadmapRes = await generateRoadmap(goalRes.data.id);
    setIsSubmitting(false);
    if (roadmapRes.ok) {
      setRoadmapData(roadmapRes.data);
      const first = roadmapRes.data.tasks.find((t) => t.status === "pending") || null;
      setTodayAction(first);
    }
  };

  const handleResetGoal = async () => {
    if (!goal) return;
    const confirmed = window.confirm(
      "Bạn có chắc chắn muốn đặt lại (hủy) mục tiêu hiện tại để chọn lại mục tiêu mới không?"
    );
    if (!confirmed) return;
    setIsSubmitting(true);
    const res = await deleteGoal(goal.id);
    setIsSubmitting(false);
    if (res.ok) {
      setGoal(null);
      setRoadmapData(null);
      setTodayAction(null);
    } else {
      alert(res.message);
    }
  };

  const handleGenerateRoadmap = async () => {
    if (!goal) return;
    setIsSubmitting(true);
    const res = await generateRoadmap(goal.id);
    setIsSubmitting(false);
    if (res.ok) {
      setRoadmapData(res.data);
      const first = res.data.tasks.find((t) => t.status === "pending") || null;
      setTodayAction(first);
    } else {
      alert(res.message);
    }
  };

  const handleCompleteTask = async () => {
    if (!evidenceModalTask || !evidenceText.trim()) return;
    setIsSubmitting(true);
    const res = await completeTask(evidenceModalTask.id, {
      evidence_text: evidenceText.trim(),
      evidence_type: "note",
    });
    setIsSubmitting(false);
    if (res.ok) {
      setEvidenceModalTask(null);
      setEvidenceText("");
      loadData();
    } else {
      alert(res.message);
    }
  };

  const handleBlockTask = async (useFallback: boolean) => {
    if (!stuckTask) return;
    setIsSubmitting(true);
    const res = await blockTask(stuckTask.id, {
      reason: stuckReason || "Cần điều chỉnh phương án",
      use_fallback: useFallback,
    });
    setIsSubmitting(false);
    if (res.ok) {
      setStuckTask(null);
      setStuckReason("");
      loadData();
    } else {
      alert(res.message);
    }
  };

  const getModuleLink = (module: string) => {
    switch (module) {
      case "video":
        return "/app/video-studio";
      case "content":
        return "/app/content";
      case "inbox":
        return "/app/inbox";
      default:
        return null;
    }
  };

  const dateLine = new Intl.DateTimeFormat(lang === "VN" ? "vi-VN" : "en-US", {
    timeZone: "Asia/Ho_Chi_Minh",
    weekday: "long",
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(new Date());

  const mainHorizonPresets = [
    { days: 7, label: "⚡ 7 ngày" },
    { days: 14, label: "🚀 14 ngày" },
    { days: 30, label: "🎯 30 ngày (1 tháng)" },
    { days: 90, label: "📈 3 tháng (90 ngày)" },
  ];

  const extendedHorizonPresets = [
    { days: 180, label: "🏆 6 tháng", val: 6, unit: "months" as const },
    { days: 270, label: "🎖️ 9 tháng", val: 9, unit: "months" as const },
    { days: 365, label: "🌟 1 năm", val: 1, unit: "years" as const },
  ];

  if (loading) {
    return <LoadingState title={t({ vi: "Đang tải kế hoạch hôm nay...", en: "Loading today's plan..." })} />;
  }

  if (error) {
    return <ErrorState title={error} action={<Button onClick={loadData}>{t({ vi: "Thử lại", en: "Retry" })}</Button>} />;
  }

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h1 className={styles.title}>{t({ vi: "Hôm nay cùng Havi", en: "Today with Havi" })}</h1>
        <p className={styles.subtitle}>
          {dateLine} — {t({
            vi: "Chúc bạn một ngày nhiều năng lượng & hiệu quả! Cùng làm một việc hôm nay nhé.",
            en: "Wishing you an energetic and productive day! Let's accomplish today's focus.",
          })}
        </p>
      </header>

      {/* Smart Quick Actions (One-Touch Minimalist Hub) */}
      <section className={styles.quickActionsGrid} aria-label="Công cụ thực thi nhanh">
        <Link href="/app/content" className={styles.quickActionCard}>
          <span className={styles.quickActionIcon}>✍️</span>
          <div>
            <strong className={styles.quickActionTitle}>Tạo bài viết AI</strong>
            <span className={styles.quickActionDesc}>Viết bài Facebook, ý tưởng & kịch bản</span>
          </div>
        </Link>

        <Link href="/app/video-studio" className={styles.quickActionCard}>
          <span className={styles.quickActionIcon}>🎬</span>
          <div>
            <strong className={styles.quickActionTitle}>Studio Video 9:16</strong>
            <span className={styles.quickActionDesc}>Dựng clip, chèn kinetic & nhạc nền</span>
          </div>
        </Link>

        <Link href="/app/inbox" className={styles.quickActionCard}>
          <span className={styles.quickActionIcon}>💬</span>
          <div>
            <strong className={styles.quickActionTitle}>Hộp thư & CSKH</strong>
            <span className={styles.quickActionDesc}>Trả lời Fanpage & kéo khách cũ CRM</span>
          </div>
        </Link>

        <Link href="/app/calendar" className={styles.quickActionCard}>
          <span className={styles.quickActionIcon}>📅</span>
          <div>
            <strong className={styles.quickActionTitle}>Lịch đăng bài</strong>
            <span className={styles.quickActionDesc}>Duyệt bài & hẹn giờ tự động</span>
          </div>
        </Link>
      </section>

      {!goal ? (
        <section className={styles.welcomeHero} aria-label="Khởi động mục tiêu">
          <div className={styles.heroHeader}>
            <span className={styles.heroBadge}>✨ KHỞI ĐỘNG CÙNG HAVI 3.0</span>
            <h2 className={styles.heroTitle}>
              {t({
                vi: "Bạn muốn ưu tiên đạt kết quả gì tiếp theo?",
                en: "What outcome do you want to prioritize next?",
              })}
            </h2>
            <p className={styles.heroSubtitle}>
              {t({
                vi: "Chọn khung thời gian và 1 mục tiêu bên dưới để Havi tự động sinh lộ trình & việc hôm nay cho bạn.",
                en: "Select a timeframe and a starter goal below to automatically generate your roadmap & daily action.",
              })}
            </p>

            {/* Timeframe Selection Hub */}
            <div style={{ display: "flex", flexDirection: "column", gap: "8px", marginTop: "12px", background: "rgba(255, 255, 255, 0.85)", padding: "12px 16px", borderRadius: "14px", border: "1px solid #e2e8f0", backdropFilter: "blur(4px)" }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "6px" }}>
                <span style={{ fontSize: "13px", fontWeight: 700, color: "#0f172a" }}>
                  ⏱️ Khung thời gian: <span style={{ color: "#2563eb" }}>{formatHorizonLabel(selectedHorizon)}</span>
                </span>
                <button
                  type="button"
                  onClick={() => setIsCustomHorizonOpen(!isCustomHorizonOpen)}
                  style={{
                    background: isCustomHorizonOpen ? "#dbeafe" : "#ffffff",
                    border: isCustomHorizonOpen ? "1.5px solid #2563eb" : "1px solid #94a3b8",
                    padding: "4px 12px",
                    borderRadius: "8px",
                    fontSize: "12px",
                    fontWeight: 700,
                    color: isCustomHorizonOpen ? "#1d4ed8" : "#1e293b",
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    gap: "4px",
                  }}
                >
                  ⚙️ {isCustomHorizonOpen ? "Đóng tùy chỉnh" : "Tùy chỉnh khác..."}
                </button>
              </div>

              {/* Clean Main Presets */}
              <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                {mainHorizonPresets.map((h) => {
                  const isSelected = selectedHorizon === h.days && !isCustomHorizonOpen;
                  return (
                    <button
                      key={h.days}
                      type="button"
                      onClick={() => {
                        setIsCustomHorizonOpen(false);
                        setSelectedHorizon(h.days);
                      }}
                      style={{
                        padding: "6px 14px",
                        borderRadius: "20px",
                        border: isSelected ? "2px solid #2563eb" : "1px solid #cbd5e1",
                        background: isSelected ? "#eff6ff" : "#ffffff",
                        color: isSelected ? "#1d4ed8" : "#475569",
                        fontWeight: 700,
                        fontSize: "12.5px",
                        cursor: "pointer",
                        transition: "all 0.15s ease",
                      }}
                    >
                      {h.label}
                    </button>
                  );
                })}
              </div>

              {/* Custom Drawer (Extended Presets + Arbitrary Number Input + Apply Button) */}
              {isCustomHorizonOpen && (
                <div style={{ display: "flex", flexDirection: "column", gap: "10px", marginTop: "6px", padding: "12px 14px", background: "#f8fafc", borderRadius: "10px", border: "1.5px solid #93c5fd" }}>
                  {/* Extended presets (6 months, 9 months, 1 year) */}
                  <div style={{ display: "flex", alignItems: "center", gap: "6px", flexWrap: "wrap" }}>
                    <span style={{ fontSize: "12px", fontWeight: 600, color: "#64748b" }}>Mốc dài hạn:</span>
                    {extendedHorizonPresets.map((h) => {
                      const isSelected = selectedHorizon === h.days;
                      return (
                        <button
                          key={h.days}
                          type="button"
                          onClick={() => {
                            setSelectedHorizon(h.days);
                            setCustomHorizonValue(h.val);
                            setCustomHorizonUnit(h.unit);
                          }}
                          style={{
                            padding: "4px 12px",
                            borderRadius: "14px",
                            border: isSelected ? "2px solid #2563eb" : "1px solid #cbd5e1",
                            background: isSelected ? "#eff6ff" : "#ffffff",
                            color: isSelected ? "#1d4ed8" : "#475569",
                            fontWeight: 700,
                            fontSize: "12px",
                            cursor: "pointer",
                          }}
                        >
                          {h.label} {isSelected ? "✓" : ""}
                        </button>
                      );
                    })}
                  </div>

                  {/* Arbitrary input with explicit Apply button */}
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap", borderTop: "1px dashed #cbd5e1", paddingTop: "10px" }}>
                    <span style={{ fontSize: "12px", fontWeight: 600, color: "#334155" }}>Hoặc tự nhập số lượng:</span>
                    <input
                      type="number"
                      min={1}
                      max={3650}
                      value={customHorizonValue}
                      onChange={(e) => {
                        const val = Math.max(1, Number(e.target.value) || 1);
                        setCustomHorizonValue(val);
                      }}
                      style={{
                        width: "65px",
                        padding: "5px 8px",
                        borderRadius: "6px",
                        border: "1px solid #cbd5e1",
                        fontSize: "13px",
                        fontWeight: 700,
                        color: "#0f172a",
                        background: "#ffffff",
                      }}
                    />
                    <select
                      value={customHorizonUnit}
                      onChange={(e) => {
                        const unit = e.target.value as "days" | "weeks" | "months" | "years";
                        setCustomHorizonUnit(unit);
                      }}
                      style={{
                        padding: "5px 8px",
                        borderRadius: "6px",
                        border: "1px solid #cbd5e1",
                        fontSize: "12.5px",
                        fontWeight: 700,
                        color: "#0f172a",
                        background: "#ffffff",
                      }}
                    >
                      <option value="days">Ngày</option>
                      <option value="weeks">Tuần</option>
                      <option value="months">Tháng</option>
                      <option value="years">Năm</option>
                    </select>
                    <span style={{ fontSize: "12px", color: "#64748b" }}>
                      = <strong style={{ color: "#2563eb" }}>{calculatedCustomDays} ngày</strong> ({formatHorizonLabel(calculatedCustomDays)})
                    </span>

                    <button
                      type="button"
                      onClick={() => {
                        setSelectedHorizon(calculatedCustomDays);
                        setIsCustomHorizonOpen(false);
                      }}
                      style={{
                        marginLeft: "auto",
                        padding: "6px 14px",
                        background: selectedHorizon === calculatedCustomDays ? "#10b981" : "#2563eb",
                        color: "#ffffff",
                        border: "none",
                        borderRadius: "8px",
                        fontSize: "12px",
                        fontWeight: 700,
                        cursor: "pointer",
                        boxShadow: "0 1px 2px rgba(0,0,0,0.08)",
                        transition: "all 0.15s ease",
                      }}
                    >
                      {selectedHorizon === calculatedCustomDays ? "✓ Đang áp dụng" : "🚀 Áp dụng mốc này"}
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className={styles.heroGoalGrid}>
            {quickTemplates.map((item) => (
              <div key={item.title} className={styles.heroGoalCard}>
                <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span className={styles.heroGoalIcon}>{item.icon}</span>
                    <span style={{ fontSize: "11.5px", fontWeight: 700, color: "#2563eb", background: "#dbeafe", padding: "2px 8px", borderRadius: "6px" }}>
                      ⏱️ ~{item.weekly_capacity_hours}h/tuần
                    </span>
                  </div>
                  <h3 className={styles.heroGoalCardTitle}>{item.title}</h3>
                  <p className={styles.heroGoalCardEvidence}>
                    📌 <strong>Kết quả:</strong> {item.evidence_definition}
                  </p>
                </div>

                <button
                  type="button"
                  disabled={isSubmitting}
                  onClick={() => handleLaunchTemplate(item)}
                  className={styles.heroGoalBtn}
                >
                  {isSubmitting ? "⚡ Đang khởi tạo..." : "🚀 Bắt đầu kế hoạch (1 chạm)"}
                </button>
              </div>
            ))}
          </div>

          <button
            type="button"
            onClick={() => setIsGoalModalOpen(true)}
            className={styles.heroCustomTrigger}
          >
            ✍️ Hoặc tự đặt mục tiêu theo nhu cầu riêng của bạn ➔
          </button>
        </section>
      ) : (
        <>
          {/* Goal Header */}
          <section className={styles.goalBanner} aria-label="Mục tiêu hiện tại">
            <div className={styles.goalInfo}>
              <span className={styles.goalBadge}>🎯 MỤC TIÊU ĐANG THỰC HIỆN</span>
              <strong className={styles.goalTitle}>{goal.title}</strong>
              <span className={styles.goalEvidence}>
                📌 <strong>Kết quả mong muốn:</strong> {goal.evidence_definition}
              </span>
            </div>
            <div style={{ display: "flex", gap: "8px", alignItems: "center", flexWrap: "wrap" }}>
              <button
                type="button"
                onClick={() => setIsGoalModalOpen(true)}
                style={{
                  background: "transparent",
                  border: "1px solid rgba(37, 99, 235, 0.3)",
                  color: "#2563eb",
                  borderRadius: "8px",
                  padding: "6px 12px",
                  fontSize: "12.5px",
                  fontWeight: 700,
                  cursor: "pointer",
                }}
              >
                🔄 Đổi mục tiêu
              </button>
              <button
                type="button"
                disabled={isSubmitting}
                onClick={handleResetGoal}
                style={{
                  background: "transparent",
                  border: "1px solid rgba(239, 68, 68, 0.3)",
                  color: "#dc2626",
                  borderRadius: "8px",
                  padding: "6px 12px",
                  fontSize: "12.5px",
                  fontWeight: 700,
                  cursor: "pointer",
                }}
              >
                🗑️ Đặt lại từ đầu
              </button>
              <Link href="/app/roadmap" style={{ color: "#2563eb", fontWeight: 700, fontSize: "13px", textDecoration: "none", marginLeft: "4px" }}>
                Xem Lộ trình ➔
              </Link>
            </div>
          </section>


          {/* If goal exists but roadmap is not yet generated */}
          {!roadmapData ? (
            <section className={styles.actionCard}>
              <h2 className={styles.actionTitle}>Lộ trình chưa được khởi tạo</h2>
              <p className={styles.actionReason}>
                Bấm nút bên dưới để Havi phân rã mục tiêu <strong>{goal.title}</strong> thành kế hoạch 90 ngày, 30 ngày, 7 ngày và một việc hôm nay.
              </p>
              <Button variant="primary" disabled={isSubmitting} onClick={handleGenerateRoadmap}>
                {isSubmitting ? "Đang sinh lộ trình..." : "⚡ Sinh Lộ Trình Thực Hiện Ngay"}
              </Button>
            </section>
          ) : todayAction ? (
            /* Spotlight Action Card */
            <section className={styles.actionCard} aria-label="Hành động đề xuất hôm nay">
              <div className={styles.actionHeader}>
                <div>
                  <span className={styles.actionBadge}>⚡ VIỆC NÊN LÀM HÔM NAY</span>
                  <h2 className={styles.actionTitle}>{todayAction.title}</h2>
                </div>
                <span style={{ fontSize: "13px", fontWeight: 700, color: "#2563eb" }}>
                  ⏱️ ~{todayAction.time_estimate_minutes} phút
                </span>
              </div>

              <div className={styles.actionReason}>
                💡 <strong>Vì sao nên làm việc này trước?</strong> {todayAction.why_this_is_next}
              </div>

              {/* Explicit role breakdown */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", background: "var(--bg-canvas)", padding: "12px", borderRadius: "8px", border: "1px solid var(--border-color)", fontSize: "13px" }}>
                <div>
                  <strong style={{ color: "#2563eb", display: "block", marginBottom: "4px" }}>🤖 Havi chuẩn bị sẵn:</strong>
                  <span>{todayAction.owner_type === "user" ? "Gợi ý cách làm & ghi nhận kết quả" : "Soạn sẵn bài viết, ý tưởng và kịch bản video"}</span>
                </div>
                <div>
                  <strong style={{ color: "#059669", display: "block", marginBottom: "4px" }}>👤 Bạn chỉ cần:</strong>
                  <span>{todayAction.owner_type === "user" ? "Làm thực tế (quay clip ngắn, tư vấn, chăm sóc học viên / khách hàng)" : "Xem lại, chỉnh sửa theo ý mình và bấm đăng bài"}</span>
                </div>
              </div>

              <div className={styles.doneRuleBox}>
                <div className={styles.doneRuleTitle}>✅ Tiêu chuẩn hoàn thành:</div>
                <div>{todayAction.done_rule}</div>
              </div>

              {todayAction.fallback_action ? (
                <div className={styles.fallbackCard}>
                  🔄 <strong>Phương án nhẹ hơn nếu hôm nay bận:</strong> {todayAction.fallback_action}
                </div>
              ) : null}


              <div className={styles.buttonGroup}>
                {getModuleLink(todayAction.capability_module) ? (
                  <Link href={getModuleLink(todayAction.capability_module)!} className={styles.primaryActionBtn}>
                    🚀 {t({ vi: "Mở công cụ thực hiện", en: "Open Tool to Execute" })}
                  </Link>
                ) : null}

                <button
                  type="button"
                  className={styles.completeBtn}
                  onClick={() => setEvidenceModalTask(todayAction)}
                >
                  ✓ {t({ vi: "Đã làm xong việc này", en: "Mark Done" })}
                </button>

                <button
                  type="button"
                  className={styles.stuckBtn}
                  onClick={() => setStuckTask(todayAction)}
                >
                  ⚠️ {t({ vi: "Cần đổi cách làm khác", en: "Need Alternative" })}
                </button>
              </div>
            </section>
          ) : (
            <EmptyState
              title={t({ vi: "Hôm nay bạn đã hoàn thành xong mọi việc!", en: "All tasks completed for today!" })}
              body={t({ vi: "Tuyệt vời! Kết quả đã được ghi nhận vào kế hoạch tuần của bạn.", en: "Awesome! Your results are updated in your weekly plan." })}
              action={
                <Link href="/app/roadmap" className={styles.primaryActionBtn}>
                  Xem tiến độ tuần này ➔
                </Link>
              }
            />
          )}

          {/* Upcoming 7-day commitment checklist */}
          {roadmapData && roadmapData.tasks.length > 0 ? (
            <section className={styles.upcomingSection} aria-label="Kế hoạch tuần">
              <h2 className={styles.upcomingHeader}>
                📋 {t({ vi: "Kế hoạch tuần này", en: "This Week's Plan" })}
              </h2>
              <div className={styles.taskList}>
                {roadmapData.tasks.map((task, idx) => (
                  <div
                    key={task.id}
                    className={`${styles.taskItem} ${task.status === "completed" ? styles.taskItemCompleted : ""}`}
                  >
                    <div>
                      <span style={{ fontWeight: 700, marginRight: "8px", color: "#2563eb" }}>
                        #{idx + 1}
                      </span>
                      <strong className={styles.taskTitle}>{task.title}</strong>
                      <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "2px" }}>
                        {task.done_rule} · ~{task.time_estimate_minutes}p
                      </div>
                    </div>
                    <div>
                      {task.status === "completed" ? (
                        <span style={{ color: "#10b981", fontWeight: 700, fontSize: "13px" }}>✓ Đã xong</span>
                      ) : (
                        <button
                          type="button"
                          className={styles.completeBtn}
                          style={{ padding: "6px 12px", fontSize: "12px" }}
                          onClick={() => setEvidenceModalTask(task)}
                        >
                          Xong
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </section>
          ) : null}
        </>
      )}

      {/* Evidence Submission Modal */}
      {evidenceModalTask ? (
        <div className={styles.modalOverlay} role="dialog" aria-modal="true">
          <div className={styles.modalContent}>
            <h3 className={styles.modalTitle}>📝 Ghi nhận kết quả hôm nay</h3>
            <p style={{ fontSize: "13px", color: "var(--text-secondary)", margin: 0 }}>
              Việc đã làm: <strong>{evidenceModalTask.title}</strong>
            </p>
            <textarea
              className={styles.textarea}
              placeholder="Chia sẻ nhanh kết quả bạn vừa đạt được (VD: Đã đăng bài lên Fanpage, có 2 học viên/khách nhắn tin hỏi, hoặc doanh thu hôm nay...)"
              value={evidenceText}
              onChange={(e) => setEvidenceText(e.target.value)}
              rows={4}
            />
            <div className={styles.buttonGroup} style={{ justifyContent: "flex-end" }}>
              <Button variant="outline" onClick={() => setEvidenceModalTask(null)}>
                Huỷ
              </Button>
              <Button variant="primary" disabled={isSubmitting || !evidenceText.trim()} onClick={handleCompleteTask}>
                {isSubmitting ? "Đang lưu..." : "Xác nhận & Cập nhật kế hoạch"}
              </Button>
            </div>
          </div>
        </div>
      ) : null}

      {/* Stuck / Blocked Modal */}
      {stuckTask ? (
        <div className={styles.modalOverlay} role="dialog" aria-modal="true">
          <div className={styles.modalContent}>
            <h3 className={styles.modalTitle}>💡 Bạn đang gặp khó khăn gì?</h3>
            <textarea
              className={styles.textarea}
              placeholder="Chia sẻ lý do (VD: Hôm nay bận quá chưa kịp làm, hoặc muốn đổi hướng khác...)"
              value={stuckReason}
              onChange={(e) => setStuckReason(e.target.value)}
              rows={3}
            />
            <div className={styles.buttonGroup} style={{ justifyContent: "flex-end" }}>
              <Button variant="outline" onClick={() => setStuckTask(null)}>
                Đóng
              </Button>
              {stuckTask.fallback_action ? (
                <Button variant="primary" disabled={isSubmitting} onClick={() => handleBlockTask(true)}>
                  Đổi sang việc nhẹ hơn hôm nay
                </Button>
              ) : (
                <Button variant="primary" disabled={isSubmitting} onClick={() => handleBlockTask(false)}>
                  Tạm hoãn & Chuyển việc tiếp theo
                </Button>
              )}
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
          if (newRoadmap) {
            setRoadmapData(newRoadmap);
            const first = newRoadmap.tasks.find((t) => t.status === "pending") || null;
            setTodayAction(first);
          } else {
            loadData();
          }
        }}
      />
    </div>
  );
}
