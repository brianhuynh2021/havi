"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/state-views";
import { ToastContainer, type ToastItem } from "@/components/ui/toast";
import { useLanguage } from "@/lib/i18n/language-context";
import { apiClient } from "@/lib/api-client/client";
import { readTokens } from "@/lib/auth/token-store";
import {
  blockTask,
  completeTask,
  reopenTask,
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
import {
  listInbox,
  listLeads,
  listNudges,
  approveNudge,
  triggerNudgeScan,
  type CrmNudge,
  type InboxItem,
  type Lead,
} from "@/features/leads/leads.api";
import { AuthenticVideoDropzone } from "./authentic-video-dropzone";
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

  // Leads, Inbox & Revenue Radar State
  const [inboxItems, setInboxItems] = useState<InboxItem[]>([]);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [nudges, setNudges] = useState<CrmNudge[]>([]);
  const [isDayZeroMode, setIsDayZeroMode] = useState<boolean>(false);
  const [isScanningNudges, setIsScanningNudges] = useState(false);

  // Modals & Action States
  const [isGoalModalOpen, setIsGoalModalOpen] = useState(false);
  const [evidenceModalTask, setEvidenceModalTask] = useState<RoadmapTask | null>(null);
  const [evidenceText, setEvidenceText] = useState("");
  const [verificationModalTask, setVerificationModalTask] = useState<RoadmapTask | null>(null);
  const [externalProofLink, setExternalProofLink] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [stuckTask, setStuckTask] = useState<RoadmapTask | null>(null);
  const [stuckReason, setStuckReason] = useState("");
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

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    const activeId = readTokens()?.activeWorkspaceId;

    const [goalRes, roadmapRes, todayRes, inboxRes, leadsRes, nudgesRes] = await Promise.all([
      fetchActiveGoal(),
      fetchActiveRoadmap(),
      fetchTodayAction(),
      listInbox().catch(() => ({ ok: false as const, message: "error" })),
      listLeads().catch(() => ({ ok: false as const, message: "error" })),
      activeId ? listNudges(activeId).catch(() => ({ ok: false as const, message: "error" })) : Promise.resolve({ ok: false as const, message: "no ws" }),
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
    if (todayRes.ok && todayRes.data) {
      setTodayAction(todayRes.data);
    } else if (roadmapRes.ok && roadmapRes.data) {
      const firstPending = roadmapRes.data.tasks.find((t) => t.status === "pending") || null;
      setTodayAction(firstPending);
    } else {
      setTodayAction(null);
    }

    if (inboxRes.ok && Array.isArray(inboxRes.data)) {
      setInboxItems(inboxRes.data);
    }
    if (leadsRes.ok && Array.isArray(leadsRes.data)) {
      setLeads(leadsRes.data);
      if (leadsRes.data.length === 0) {
        setIsDayZeroMode(true);
      }
    }
    if (nudgesRes.ok && nudgesRes.data && Array.isArray(nudgesRes.data.items)) {
      setNudges(nudgesRes.data.items);
    }

    setLoading(false);
  }, []);

  const handleTriggerNudgeScan = async () => {
    const activeId = readTokens()?.activeWorkspaceId;
    if (!activeId) return;
    setIsScanningNudges(true);
    const res = await triggerNudgeScan(activeId);
    setIsScanningNudges(false);
    if (res.ok) {
      const count = Array.isArray(res.data) ? res.data.length : 0;
      addToast({
        type: "success",
        title: "🎯 Đã quét xong tệp khách cũ!",
        description: `Tìm thấy ${count} cơ hội kích hoạt lại doanh thu.`,
      });
      const nudgesRes = await listNudges(activeId);
      if (nudgesRes.ok && Array.isArray(nudgesRes.data?.items)) {
        setNudges(nudgesRes.data.items);
      }
    } else {
      addToast({ type: "info", title: "Thông báo", description: "Đã quét toàn bộ danh sách khách hàng." });
    }
  };

  const handleApproveNudgeAction = async (nudgeId: string) => {
    const activeId = readTokens()?.activeWorkspaceId;
    if (!activeId) return;
    setIsSubmitting(true);
    const res = await approveNudge(activeId, nudgeId);
    setIsSubmitting(false);
    if (res.ok) {
      addToast({
        type: "success",
        title: "⚡ Đã gửi tin ưu đãi thành công!",
        description: "Thông điệp kích hoạt lại đã được chuyển tới khách hàng.",
      });
      setNudges((prev) => prev.filter((n) => n.id !== nudgeId));
    } else {
      addToast({ type: "error", title: "Lỗi gửi tin", description: res.message });
    }
  };

  useEffect(() => {
    void (async () => {
      await loadData();
      const activeId = readTokens()?.activeWorkspaceId;
      try {
        const { data } = await apiClient.GET("/workspaces");
        if (data) {
          const list = data as Array<{ id: string; industry: string }>;
          const active = list.find((w) => w.id === activeId) ?? list[0];
          if (active?.industry) {
            setWorkspaceIndustry(active.industry);
          }
        }
      } catch {
        // ignore
      }
    })();
  }, [loadData]);

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
      addToast({ type: "error", title: "Không thể tạo mục tiêu", description: goalRes.message });
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
      addToast({ type: "success", title: "🎯 Đã tạo lộ trình thành công!", description: "Bắt đầu hành trình tăng trưởng ngay hôm nay." });
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
      addToast({ type: "info", title: "Đã đặt lại mục tiêu", description: "Bạn có thể chọn mục tiêu chiến lược mới." });
    } else {
      addToast({ type: "error", title: "Không thể đặt lại mục tiêu", description: res.message });
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
      addToast({ type: "success", title: "⚡ Đã tái tạo lộ trình!", description: "Các hành động mới đã sẵn sàng." });
    } else {
      addToast({ type: "error", title: "Không thể tạo lộ trình", description: res.message });
    }
  };

  const handleQuickCompleteTask = async (task: RoadmapTask, customEvidence?: string) => {
    setIsSubmitting(true);
    const evidence = customEvidence?.trim() || task.done_rule || "Đã hoàn thành xuất sắc theo tiêu chuẩn";
    const res = await completeTask(task.id, {
      evidence_text: evidence,
      evidence_type: "note",
    });
    setIsSubmitting(false);
    if (res.ok) {
      setEvidenceModalTask(null);
      setEvidenceText("");
      setVerificationModalTask(null);
      setExternalProofLink("");
      addToast({ type: "success", title: "🎉 Hoàn thành xuất sắc!", description: "Đã xác minh và ghi nhận tiến độ." });
      await loadData();
    } else {
      addToast({ type: "error", title: "Lỗi ghi nhận hoàn thành", description: res.message });
    }
  };

  const onTriggerCompleteTask = (task: RoadmapTask) => {
    if (task.capability_module === "content" || task.capability_module === "video") {
      setVerificationModalTask(task);
      setExternalProofLink("");
    } else {
      handleQuickCompleteTask(task, `[Tự ghi nhận thực tế] ${task.done_rule}`);
    }
  };

  const handleReopenTask = async (task: RoadmapTask) => {
    setIsSubmitting(true);
    const res = await reopenTask(task.id);
    setIsSubmitting(false);
    if (res.ok) {
      addToast({ type: "info", title: "↩️ Đã mở lại nhiệm vụ", description: "Nhiệm vụ đã chuyển về trạng thái đang làm." });
      await loadData();
    } else {
      addToast({ type: "error", title: "Không thể mở lại nhiệm vụ", description: res.message });
    }
  };

  const handleCompleteTask = async () => {
    if (!evidenceModalTask || !evidenceText.trim()) return;
    await handleQuickCompleteTask(evidenceModalTask, evidenceText);
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
      addToast({ type: "info", title: "Đã chuyển phương án", description: "Nhiệm vụ đã được cập nhật." });
      loadData();
    } else {
      addToast({ type: "error", title: "Không thể chuyển phương án", description: res.message });
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
      case "calendar":
        return "/app/calendar";
      default:
        return null;
    }
  };

  const getModuleLinkWithTask = (task: RoadmapTask) => {
    const query = `task_id=${task.id}&goal_id=${task.goal_id}&topic=${encodeURIComponent(task.title)}`;
    switch (task.capability_module) {
      case "video":
        return `/app/video-studio?${query}&track=video`;
      case "content":
        return `/app/content?${query}&track=posts`;
      case "inbox":
        return `/app/inbox?${query}`;
      case "calendar":
        return `/app/calendar?${query}`;
      default:
        return `/app/content?${query}`;
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
            vi: "Chúc bạn một ngày nhiều năng lượng & bình yên! Havi luôn ở đây đồng hành cùng bạn.",
            en: "Wishing you a peaceful and productive day! Havi is always here by your side.",
          })}
        </p>
      </header>

      {/* Companion Spark: 30s Inspiration without cognitive load */}
      <section className={styles.companionCard} aria-label="Gợi ý cảm hứng hôm nay">
        <div className={styles.companionContent}>
          <div className={styles.companionBadge}>💡 TIA SÁNG CẢM HỨNG 30 GIÂY</div>
          <h3 className={styles.companionTitle}>
            {workspaceIndustry.includes("education")
              ? "Hôm nay lớp học có khoảnh khắc hào hứng nào không?"
              : workspaceIndustry.includes("spa")
              ? "Hôm nay tiệm có khách hàng nào khen ngợi dịch vụ không?"
              : workspaceIndustry.includes("food")
              ? "Hôm nay quán có món ngon hoặc không gian ấm cúng nào muốn chia sẻ?"
              : "Hôm nay cơ sở của bạn có khoảnh khắc đáng nhớ nào muốn chia sẻ?"}
          </h3>
          <p className={styles.companionDesc}>
            {workspaceIndustry.includes("education")
              ? "Chỉ cần chụp 1 bức ảnh học viên chăm chú thực hành hoặc quay 15s bạn nhỏ chạy thử sản phẩm, Havi sẽ viết bài truyền cảm hứng & kịch bản Video 9:16 giúp bạn."
              : "Chỉ cần 30 giây thu âm hoặc chụp 1 tấm ảnh thật tại tiệm, Havi sẽ lo toàn bộ việc biên soạn bài đăng và trực khách trên Facebook."}
          </p>
        </div>
        <Link
          href={`/app/content?topic=${encodeURIComponent(
            workspaceIndustry.includes("education")
              ? "Khoảnh khắc học viên thực hành hào hứng tại lớp và lời khuyên học tập thực tế"
              : "Chia sẻ hoạt động thật và không gian phục vụ khách hàng chu đáo hôm nay"
          )}&track=posts`}
          className={styles.companionButton}
        >
          ✨ Soạn bài cho ý tưởng này ngay (1 chạm) ➔
        </Link>
      </section>

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

      {/* =====================================================================
          HAVI 3.0 ACTION CENTER: BẢNG ĐIỀU KHIỂN TÁC CHIẾN 3 PHÚT MỖI NGÀY
          ===================================================================== */}
      <section className={styles.actionCenterSection} aria-label="Bảng điều khiển tác chiến 3 phút">
        <div className={styles.actionCenterHeader}>
          <h2 className={styles.actionCenterTitle}>
            ⚡ {t({ vi: "Bảng Điều Khiển Tác Chiến Hôm Nay (3 Phút)", en: "Today's 3-Minute Action Center" })}
          </h2>
          <span style={{ fontSize: "12.5px", color: "#64748b", fontWeight: 600 }}>
            {t({ vi: "Làm hộ việc & bảo vệ dòng tiền cho bạn", en: "Automating tasks & protecting your revenue" })}
          </span>
        </div>

        <div className={styles.actionCenterGrid}>
          {/* THẺ 1: RADAR TRỰC CHIẾN & CỨU LEAD 24/7 */}
          <div className={styles.actionMissionCard}>
            <div className={styles.cardTop}>
              <span className={styles.cardBadgeAmber}>⚡ TRỰC CHIẾN 24/7</span>
              <h3 className={styles.cardMissionTitle}>Hộp Thư & Giữ Khách Tức Thì</h3>
              <p className={styles.cardMissionDesc}>
                Túc trực Fanpage & Messenger ngày đêm, phản hồi &lt;10s để không bao giờ bị rớt khách.
              </p>

              {inboxItems.length > 0 || leads.length > 0 ? (
                <div className={styles.activeLeadItem}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <strong style={{ fontSize: "13px", color: "#0f172a" }}>
                      👤 {leads[0]?.name || inboxItems[0]?.author_name || "Khách hàng mới"}
                    </strong>
                    <span style={{ fontSize: "11px", fontWeight: 700, color: "#2563eb", background: "#dbeafe", padding: "2px 6px", borderRadius: "4px" }}>
                      Tin nhắn mới
                    </span>
                  </div>
                  <p style={{ fontSize: "12.5px", color: "#475569", margin: "2px 0", lineHeight: 1.4 }}>
                    💬 &ldquo;{inboxItems[0]?.content || leads[0]?.message || "Đang hỏi thông tin khóa học / dịch vụ..."}&rdquo;
                  </p>
                  {leads[0]?.phone ? (
                    <span style={{ fontSize: "12px", color: "#10b981", fontWeight: 700 }}>
                      📞 SĐT: {leads[0].phone}
                    </span>
                  ) : null}
                </div>
              ) : (
                <div className={styles.aiGuardBox}>
                  <span className={styles.aiGuardPulse} />
                  <div>
                    <strong style={{ fontSize: "13px", color: "#065f46", display: "block" }}>
                      🛡️ AI Guard Mode Đang Bật
                    </strong>
                    <span style={{ fontSize: "12px", color: "#047857" }}>
                      Sẵn sàng phản hồi &lt;10s &amp; xin SĐT khách khi có tin nhắn mới.
                    </span>
                  </div>
                </div>
              )}
            </div>

            <Link
              href="/app/inbox"
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "6px",
                background: "#f8fafc",
                border: "1.5px solid #cbd5e1",
                color: "#1e293b",
                padding: "8px 14px",
                borderRadius: "10px",
                fontSize: "12.5px",
                fontWeight: 700,
                textDecoration: "none",
                transition: "all 0.15s ease",
              }}
            >
              💬 Xem Hộp Thư &amp; Kịch Bản Tư Vấn ➔
            </Link>
          </div>

          {/* THẺ 2: RADAR DOANH THU & SĂN KHÁCH (DAY 0 / EXISTING) */}
          <div className={styles.actionMissionCard}>
            <div className={styles.cardTop}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span className={styles.cardBadgeEmerald}>🎯 DOANH THU &amp; SĂN KHÁCH</span>
                <div style={{ display: "flex", gap: "4px" }}>
                  <button
                    type="button"
                    onClick={() => setIsDayZeroMode(false)}
                    style={{
                      border: "none",
                      background: !isDayZeroMode ? "#10b981" : "#e2e8f0",
                      color: !isDayZeroMode ? "#ffffff" : "#475569",
                      padding: "2px 8px",
                      borderRadius: "6px",
                      fontSize: "11px",
                      fontWeight: 700,
                      cursor: "pointer",
                    }}
                  >
                    Khách cũ
                  </button>
                  <button
                    type="button"
                    onClick={() => setIsDayZeroMode(true)}
                    style={{
                      border: "none",
                      background: isDayZeroMode ? "#8b5cf6" : "#e2e8f0",
                      color: isDayZeroMode ? "#ffffff" : "#475569",
                      padding: "2px 8px",
                      borderRadius: "6px",
                      fontSize: "11px",
                      fontWeight: 700,
                      cursor: "pointer",
                    }}
                  >
                    Cơ sở mới (Day 0)
                  </button>
                </div>
              </div>

              {!isDayZeroMode ? (
                <>
                  <h3 className={styles.cardMissionTitle}>Kích Hoạt Tệp Khách Cũ</h3>
                  <p className={styles.cardMissionDesc}>
                    Quét học viên / khách hàng cũ đã lâu chưa quay lại để gửi ưu đãi 1-chạm.
                  </p>

                  {nudges.length > 0 ? (
                    <div style={{ background: "#f0fdf4", border: "1px solid #bbf7d0", padding: "10px 12px", borderRadius: "10px", fontSize: "12.5px" }}>
                      <strong style={{ color: "#166534", display: "block", marginBottom: "4px" }}>
                        🎁 Có {nudges.length} khách quen cần gửi ưu đãi:
                      </strong>
                      <span style={{ color: "#374151" }}>&ldquo;{nudges[0].message.substring(0, 75)}...&rdquo;</span>
                      <button
                        type="button"
                        disabled={isSubmitting}
                        onClick={() => handleApproveNudgeAction(nudges[0].id)}
                        style={{
                          marginTop: "8px",
                          width: "100%",
                          padding: "6px 12px",
                          background: "#10b981",
                          color: "#ffffff",
                          border: "none",
                          borderRadius: "6px",
                          fontWeight: 700,
                          fontSize: "12px",
                          cursor: "pointer",
                        }}
                      >
                        ⚡ Gửi ưu đãi cho khách này ngay
                      </button>
                    </div>
                  ) : (
                    <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", padding: "10px 12px", borderRadius: "10px", fontSize: "12.5px", color: "#64748b" }}>
                      <span>Chưa có gợi ý nhắc hẹn mới. Bấm nút dưới để quét tìm cơ hội doanh thu từ khách cũ.</span>
                    </div>
                  )}

                  <button
                    type="button"
                    disabled={isScanningNudges}
                    onClick={handleTriggerNudgeScan}
                    style={{
                      width: "100%",
                      padding: "8px 14px",
                      background: "#ffffff",
                      border: "1.5px solid #10b981",
                      color: "#065f46",
                      borderRadius: "10px",
                      fontSize: "12.5px",
                      fontWeight: 700,
                      cursor: "pointer",
                    }}
                  >
                    {isScanningNudges ? "⚡ Đang quét tệp khách..." : "🔍 Quét Tệp Khách Cũ (1 Chạm)"}
                  </button>
                </>
              ) : (
                <>
                  <h3 className={styles.cardMissionTitle}>Săn 10 Khách Đầu Tiên (Day 0)</h3>
                  <p className={styles.cardMissionDesc}>
                    Cơ sở mới mở chưa có khách? Thực hiện 3 bước khởi động nhanh:
                  </p>

                  <div className={styles.dayZeroContainer}>
                    <div className={styles.dayZeroStepItem}>
                      <span>📍</span>
                      <span><strong>1. Mặt tiền số:</strong> Cắm mốc Google Maps SEO &amp; chuẩn nhận diện trong 5 phút.</span>
                    </div>
                    <div className={styles.dayZeroStepItem}>
                      <span>🎁</span>
                      <span><strong>2. Mồi câu:</strong> Tặng 30 suất học thử / trải nghiệm miễn phí không thể từ chối.</span>
                    </div>
                    <div className={styles.dayZeroStepItem}>
                      <span>🏘️</span>
                      <span><strong>3. Du kích:</strong> Quét hội nhóm cư dân/phụ huynh bán kính 2km quanh cơ sở.</span>
                    </div>
                  </div>

                  <Link
                    href={`/app/content?topic=${encodeURIComponent(
                      workspaceIndustry.includes("education")
                        ? "Khai trương tặng 30 suất học thử Lắp ráp Robot miễn phí cho học sinh tiểu học"
                        : "Khai trương tặng suất trải nghiệm dịch vụ đặc quyền cho cư dân khu vực"
                    )}&track=posts`}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      gap: "6px",
                      background: "linear-gradient(135deg, #8b5cf6, #7c3aed)",
                      color: "#ffffff",
                      padding: "8px 14px",
                      borderRadius: "10px",
                      fontSize: "12.5px",
                      fontWeight: 700,
                      textDecoration: "none",
                      boxShadow: "0 2px 8px rgba(139, 92, 246, 0.25)",
                    }}
                  >
                    🚀 Soạn Mồi Câu Khai Trương (1 Chạm) ➔
                  </Link>
                </>
              )}
            </div>
          </div>

          {/* THẺ 3: BIẾN CLIP THẬT 10S THÀNH KHÁCH */}
          <div className={styles.actionMissionCard} style={{ gridColumn: "span 1" }}>
            <div className={styles.cardTop}>
              <span className={styles.cardBadgeIndigo}>🎬 CLIP THẬT 10S</span>
              <h3 className={styles.cardMissionTitle}>Biến Hoạt Động Thật Thành Khách</h3>
              <p className={styles.cardMissionDesc}>
                Không cần học dựng phim — Chỉ cần ném clip thật, Havi tự gắn Hook 3s &amp; xuất bản đa kênh.
              </p>

              <AuthenticVideoDropzone
                industry={workspaceIndustry}
                onSuccessToast={(title, desc) => addToast({ type: "success", title, description: desc })}
              />
            </div>
          </div>
        </div>
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
            <div className={styles.goalInfo} style={{ flex: 1 }}>
              <span className={styles.goalBadge}>🎯 MỤC TIÊU ĐANG THỰC HIỆN</span>
              <strong className={styles.goalTitle}>{goal.title}</strong>
              <span className={styles.goalEvidence}>
                📌 <strong>Kết quả mong muốn:</strong> {goal.evidence_definition}
              </span>

              {/* Weekly Progress Bar */}
              {roadmapData && roadmapData.tasks.length > 0 ? (
                <div style={{ display: "flex", alignItems: "center", gap: "10px", marginTop: "8px", maxWidth: "420px" }}>
                  <div style={{ flex: 1, height: "8px", background: "rgba(0,0,0,0.08)", borderRadius: "4px", overflow: "hidden" }}>
                    <div
                      style={{
                        width: `${Math.round((roadmapData.tasks.filter((t) => t.status === "completed").length / roadmapData.tasks.length) * 100)}%`,
                        height: "100%",
                        background: "linear-gradient(90deg, #2563eb, #10b981)",
                        borderRadius: "4px",
                        transition: "width 0.3s ease",
                      }}
                    />
                  </div>
                  <span style={{ fontSize: "12px", fontWeight: 700, color: "#2563eb" }}>
                    {roadmapData.tasks.filter((t) => t.status === "completed").length}/{roadmapData.tasks.length} việc (
                    {Math.round((roadmapData.tasks.filter((t) => t.status === "completed").length / roadmapData.tasks.length) * 100)}%)
                  </span>
                </div>
              ) : null}
            </div>
            <div style={{ display: "flex", gap: "8px", alignItems: "center", flexWrap: "wrap" }}>
              <button
                type="button"
                onClick={() => setIsGoalModalOpen(true)}
                style={{
                  background: "#ffffff",
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
                  background: "#ffffff",
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
              {/* 3-Step Guided Timeline */}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  background: "linear-gradient(135deg, #eff6ff, #f0fdf4)",
                  border: "1px solid #bfdbfe",
                  borderRadius: "10px",
                  padding: "10px 14px",
                  fontSize: "12.5px",
                  color: "#1e3a8a",
                  flexWrap: "wrap",
                  gap: "6px",
                }}
              >
                <span><strong>Bước 1:</strong> Đọc gợi ý 💡</span>
                <span style={{ color: "#94a3b8" }}>➔</span>
                <span style={{ color: "#1d4ed8", fontWeight: 700 }}><strong>Bước 2:</strong> Bấm &ldquo;Làm ngay&rdquo; bên dưới 🚀</span>
                <span style={{ color: "#94a3b8" }}>➔</span>
                <span><strong>Bước 3:</strong> Xác nhận xong để ghi nhận ✅</span>
              </div>

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

              {/* Clear Action Button Flow */}
              <div style={{ display: "flex", flexDirection: "column", gap: "12px", marginTop: "8px", borderTop: "1px solid #e2e8f0", paddingTop: "16px" }}>
                {/* Step 2 Hero Action Trigger */}
                {getModuleLink(todayAction.capability_module) ? (
                  <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                    <span style={{ fontSize: "12.5px", fontWeight: 700, color: "#2563eb" }}>
                      👉 BƯỚC TIẾP THEO: Bấm vào đây để làm việc này ngay cùng Havi:
                    </span>
                    <Link
                      href={getModuleLinkWithTask(todayAction)}
                      style={{
                        background: "linear-gradient(135deg, #2563eb, #1d4ed8)",
                        color: "#ffffff",
                        padding: "14px 24px",
                        borderRadius: "10px",
                        fontWeight: 800,
                        fontSize: "15px",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        gap: "10px",
                        textDecoration: "none",
                        boxShadow: "0 4px 14px rgba(37, 99, 235, 0.25)",
                        transition: "all 0.15s ease",
                      }}
                    >
                      {todayAction.capability_module === "content" && "✍️ Soạn bài viết này ngay bằng AI ➔"}
                      {todayAction.capability_module === "video" && "🎬 Mở Studio Video 9:16 & Máy nhắc chữ ➔"}
                      {todayAction.capability_module === "inbox" && "💬 Mở Hộp thư CSKH & Gửi tin CRM ➔"}
                      {todayAction.capability_module === "calendar" && "📅 Mở Lịch đăng bài ➔"}
                      {!["content", "video", "inbox", "calendar"].includes(todayAction.capability_module) && "🚀 Bắt đầu thực hiện việc này ➔"}
                    </Link>
                  </div>
                ) : null}

                {/* Step 3 Confirmation Buttons */}
                <div style={{ display: "flex", gap: "10px", flexWrap: "wrap", alignItems: "center" }}>
                  <button
                    type="button"
                    disabled={isSubmitting}
                    onClick={() => onTriggerCompleteTask(todayAction)}
                    style={{
                      flex: "1 1 auto",
                      padding: "12px 20px",
                      fontSize: "14px",
                      fontWeight: 800,
                      borderRadius: "10px",
                      background: "linear-gradient(135deg, #10b981, #059669)",
                      color: "#ffffff",
                      border: "none",
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      gap: "8px",
                      boxShadow: "0 2px 8px rgba(16, 185, 129, 0.25)",
                      transition: "transform 0.15s ease",
                    }}
                  >
                    {isSubmitting ? "⚡ Đang cập nhật..." : "✓ Đã làm xong việc này"}
                  </button>

                  <button
                    type="button"
                    disabled={isSubmitting}
                    onClick={() => setEvidenceModalTask(todayAction)}
                    style={{
                      padding: "12px 16px",
                      fontSize: "13px",
                      fontWeight: 600,
                      borderRadius: "10px",
                      background: "#ffffff",
                      border: "1px solid #cbd5e1",
                      color: "#475569",
                      cursor: "pointer",
                    }}
                  >
                    📝 Ghi chú thêm
                  </button>

                  <button
                    type="button"
                    className={styles.stuckBtn}
                    onClick={() => setStuckTask(todayAction)}
                    style={{
                      padding: "12px 16px",
                      fontSize: "13px",
                      borderRadius: "10px",
                    }}
                  >
                    ⚠️ Cần đổi cách làm khác
                  </button>
                </div>
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
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px", flexWrap: "wrap", gap: "8px" }}>
                <h2 className={styles.upcomingHeader} style={{ margin: 0 }}>
                  📋 {t({ vi: "Kế hoạch tuần này", en: "This Week's Plan" })}
                </h2>
                <span style={{ fontSize: "12.5px", color: "#64748b" }}>
                  💡 Bấm vào việc bất kỳ để xem lại nội dung hoặc đổi thứ tự thực hiện
                </span>
              </div>
              <div className={styles.taskList}>
                {roadmapData.tasks.map((task, idx) => {
                  const isCurrent = todayAction && task.id === todayAction.id;
                  const isDone = task.status === "completed";
                  const isSystemVerified = task.evidence_notes?.includes("[Xác minh hệ thống]") || task.evidence_notes?.includes("[Auto-Verified]");
                  const cleanEvidence = (task.evidence_notes || "")
                    .replace("[Xác minh hệ thống]", "")
                    .replace("[Auto-Verified]", "")
                    .replace("[Tự xác nhận]", "")
                    .replace("[Tự ghi nhận thực tế]", "")
                    .trim();

                  return (
                    <div
                      key={task.id}
                      className={`${styles.taskItem} ${isDone ? styles.taskItemCompleted : ""}`}
                      style={{
                        border: isCurrent ? "2px solid #2563eb" : undefined,
                        background: isCurrent ? "#eff6ff" : undefined,
                        padding: "14px 16px",
                        display: "flex",
                        flexDirection: "column",
                        gap: "8px",
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "12px", width: "100%" }}>
                        <div style={{ flex: 1 }}>
                          <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px", flexWrap: "wrap" }}>
                            <span style={{ fontWeight: 800, color: isDone ? "#059669" : "#2563eb", fontSize: "13px" }}>
                              #{idx + 1}
                            </span>
                            <strong className={styles.taskTitle} style={{ color: isDone ? "#065f46" : undefined }}>
                              {task.title}
                            </strong>
                            {isCurrent && (
                              <span style={{ background: "#2563eb", color: "#ffffff", fontSize: "11px", fontWeight: 800, padding: "2px 8px", borderRadius: "12px" }}>
                                ⚡ ĐANG LÀM
                              </span>
                            )}
                          </div>
                          <div style={{ fontSize: "12.5px", color: isDone ? "#047857" : "var(--text-secondary)" }}>
                            {task.done_rule} · ~{task.time_estimate_minutes}p
                          </div>
                          {isDone && cleanEvidence ? (
                            <div style={{ fontSize: "12px", color: "#166534", marginTop: "4px", background: "rgba(16, 185, 129, 0.1)", padding: "4px 8px", borderRadius: "6px", display: "inline-block" }}>
                              📌 <strong>Ghi nhận:</strong> {cleanEvidence}
                            </div>
                          ) : null}
                        </div>

                        {/* Task Action Controls */}
                        <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap", justifyContent: "flex-end" }}>
                          {isDone ? (
                            <>
                              {isSystemVerified ? (
                                <span style={{ color: "#047857", fontWeight: 800, fontSize: "12px", background: "#dcfce7", border: "1px solid #86efac", padding: "4px 10px", borderRadius: "14px", display: "inline-flex", alignItems: "center", gap: "4px" }}>
                                  🛡️ ĐÃ XÁC MINH HỆ THỐNG
                                </span>
                              ) : (
                                <span style={{ color: "#475569", fontWeight: 700, fontSize: "12px", background: "#f1f5f9", border: "1px solid #cbd5e1", padding: "4px 10px", borderRadius: "14px", display: "inline-flex", alignItems: "center", gap: "4px" }}>
                                  📝 TỰ XÁC NHẬN
                                </span>
                              )}
                              {getModuleLink(task.capability_module) && (
                                <Link
                                  href={getModuleLinkWithTask(task)}
                                  style={{
                                    color: "#1d4ed8",
                                    fontWeight: 700,
                                    fontSize: "12px",
                                    textDecoration: "none",
                                    background: "#ffffff",
                                    padding: "4px 10px",
                                    borderRadius: "8px",
                                    border: "1px solid #bfdbfe",
                                    display: "inline-flex",
                                    alignItems: "center",
                                    gap: "4px",
                                  }}
                                >
                                  👁️ Xem lại ➔
                                </Link>
                              )}
                              <button
                                type="button"
                                disabled={isSubmitting}
                                onClick={() => handleReopenTask(task)}
                                style={{
                                  background: "transparent",
                                  border: "none",
                                  color: "#64748b",
                                  fontSize: "12px",
                                  cursor: "pointer",
                                  textDecoration: "underline",
                                  padding: "2px 4px",
                                }}
                              >
                                ↩️ Mở lại
                              </button>
                            </>
                          ) : isCurrent ? (
                            <div style={{ display: "flex", gap: "6px" }}>
                              {getModuleLink(task.capability_module) && (
                                <Link
                                  href={getModuleLinkWithTask(task)}
                                  style={{
                                    background: "#2563eb",
                                    color: "#ffffff",
                                    fontWeight: 700,
                                    fontSize: "12px",
                                    padding: "6px 12px",
                                    borderRadius: "6px",
                                    textDecoration: "none",
                                    display: "inline-flex",
                                    alignItems: "center",
                                    gap: "4px",
                                  }}
                                >
                                  🚀 Làm ngay ➔
                                </Link>
                              )}
                              <button
                                type="button"
                                style={{
                                  background: "#10b981",
                                  color: "#ffffff",
                                  border: "none",
                                  padding: "6px 14px",
                                  borderRadius: "6px",
                                  fontSize: "12px",
                                  fontWeight: 700,
                                  cursor: "pointer",
                                }}
                                onClick={() => onTriggerCompleteTask(task)}
                              >
                                ✓ Xác nhận xong
                              </button>
                            </div>
                          ) : (
                            <div style={{ display: "flex", gap: "6px" }}>
                              <button
                                type="button"
                                style={{
                                  background: "#ffffff",
                                  color: "#1e293b",
                                  border: "1px solid #cbd5e1",
                                  padding: "6px 12px",
                                  borderRadius: "6px",
                                  fontSize: "12px",
                                  fontWeight: 700,
                                  cursor: "pointer",
                                }}
                                onClick={() => setTodayAction(task)}
                              >
                                Chọn làm việc này
                              </button>
                              <button
                                type="button"
                                style={{
                                  background: "#f0fdf4",
                                  color: "#059669",
                                  border: "1px solid #bbf7d0",
                                  padding: "6px 10px",
                                  borderRadius: "6px",
                                  fontSize: "11.5px",
                                  fontWeight: 700,
                                  cursor: "pointer",
                                }}
                                onClick={() => onTriggerCompleteTask(task)}
                              >
                                ✓ Xong nhanh
                              </button>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>
          ) : null}
        </>
      )}

      {/* Truthful Verification Dialog for Digital Tasks */}
      {verificationModalTask ? (
        <div className={styles.modalOverlay} role="dialog" aria-modal="true">
          <div className={styles.modalContent} style={{ maxWidth: "540px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "8px" }}>
              <span style={{ fontSize: "28px" }}>🛡️</span>
              <div>
                <h3 className={styles.modalTitle} style={{ margin: 0 }}>Xác nhận hoàn thành nhiệm vụ</h3>
                <p style={{ fontSize: "13px", color: "var(--text-secondary)", margin: "2px 0 0" }}>
                  {verificationModalTask.title}
                </p>
              </div>
            </div>

            <div style={{ background: "#f8fafc", padding: "12px 14px", borderRadius: "10px", border: "1px solid #e2e8f0", fontSize: "13px", lineHeight: "1.5", color: "#334155", margin: "14px 0" }}>
              🎯 <strong>Tiêu chuẩn hoàn thành:</strong> {verificationModalTask.done_rule}
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              {/* Option 1: In-app AI Fast Creation (Recommended) */}
              <div style={{ border: "2px solid #2563eb", background: "#eff6ff", padding: "14px", borderRadius: "10px", display: "flex", flexDirection: "column", gap: "6px" }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <strong style={{ color: "#1d4ed8", fontSize: "13.5px" }}>✨ Cách 1: Làm ngay cùng Havi AI (Khuyên dùng)</strong>
                  <span style={{ background: "#2563eb", color: "#ffffff", fontSize: "10.5px", fontWeight: 800, padding: "2px 8px", borderRadius: "8px" }}>
                    TỰ ĐỘNG XÁC MINH
                  </span>
                </div>
                <p style={{ fontSize: "12px", color: "#1e40af", margin: 0 }}>
                  Havi sẽ nạp sẵn chủ đề này vào Studio. Bạn chỉ cần xem lại và bấm đăng bài để hệ thống tự động tích xanh!
                </p>
                <Link
                  href={getModuleLinkWithTask(verificationModalTask)}
                  style={{
                    background: "#2563eb",
                    color: "#ffffff",
                    padding: "10px 16px",
                    borderRadius: "8px",
                    fontWeight: 700,
                    fontSize: "13px",
                    textDecoration: "none",
                    textAlign: "center",
                    marginTop: "6px",
                    boxShadow: "0 2px 6px rgba(37, 99, 235, 0.2)",
                  }}
                >
                  {verificationModalTask.capability_module === "content" ? "✍️ Mở công cụ soạn bài AI ngay ➔" : "🎬 Mở Studio Video 9:16 ngay ➔"}
                </Link>
              </div>

              {/* Option 2: Self-attestation / External Done */}
              <div style={{ border: "1px solid #cbd5e1", background: "#ffffff", padding: "14px", borderRadius: "10px", display: "flex", flexDirection: "column", gap: "8px" }}>
                <strong style={{ color: "#0f172a", fontSize: "13.5px" }}>🏷️ Cách 2: Tôi đã tự đăng trực tiếp bên ngoài</strong>
                <p style={{ fontSize: "12px", color: "#64748b", margin: 0 }}>
                  Nếu bạn đã tự đăng bài trên Facebook hoặc hoàn thành ngoài app, hãy dán link bài viết hoặc ghi chú nhanh:
                </p>
                <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                  <input
                    type="text"
                    placeholder="Dán link bài viết Facebook (hoặc ghi chú ngắn...)"
                    value={externalProofLink}
                    onChange={(e) => setExternalProofLink(e.target.value)}
                    style={{
                      flex: 1,
                      padding: "9px 12px",
                      borderRadius: "6px",
                      border: "1px solid #cbd5e1",
                      fontSize: "12.5px",
                    }}
                  />
                  <button
                    type="button"
                    disabled={isSubmitting}
                    onClick={() => {
                      const note = externalProofLink.trim()
                        ? `[Tự xác nhận] ${externalProofLink.trim()}`
                        : `[Tự xác nhận] Đã hoàn thành trực tiếp bên ngoài app`;
                      handleQuickCompleteTask(verificationModalTask, note);
                    }}
                    style={{
                      background: "#059669",
                      color: "#ffffff",
                      border: "none",
                      padding: "9px 16px",
                      borderRadius: "6px",
                      fontSize: "12.5px",
                      fontWeight: 700,
                      cursor: "pointer",
                      whiteSpace: "nowrap",
                    }}
                  >
                    Xác nhận xong
                  </button>
                </div>
              </div>
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "16px" }}>
              <Button variant="outline" onClick={() => setVerificationModalTask(null)}>
                Đóng
              </Button>
            </div>
          </div>
        </div>
      ) : null}

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

      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
    </div>
  );
}
