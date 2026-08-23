"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/state-views";
import { useLanguage } from "@/lib/i18n/language-context";
import {
  fetchDashboardActivity,
  fetchDashboardSummary,
  type DashboardActivityEvent,
  type DashboardContentSummary,
} from "./dashboard.api";
import { fetchSubscription, type Subscription } from "@/features/billing/billing.api";
import { listLeads, type Lead } from "@/features/leads/leads.api";
import styles from "./dashboard.module.css";

function activityCopy(event: DashboardActivityEvent, t: (obj: { vi: string; en: string }) => string) {
  if (event.job_kind === "publish.run_job" && event.error) {
    return {
      text: t({ vi: "Một bài chưa đăng được, cần xem lại kết nối hoặc thử đăng lại.", en: "A post failed to publish, check connection or retry." }),
      tag: t({ vi: "Lỗi đăng", en: "Publish error" }),
    };
  }
  if (event.job_kind === "publish.run_job") {
    return { text: t({ vi: "Một bài đã đăng thành công.", en: "A post was published successfully." }), tag: t({ vi: "Đã đăng", en: "Published" }) };
  }
  if (event.job_kind === "content.approve") {
    return {
      text: t({ vi: "Một bài đã được duyệt và đưa vào lịch đăng.", en: "A post was approved and added to schedule." }),
      tag: t({ vi: "Đã duyệt", en: "Approved" }),
    };
  }
  if (event.job_kind === "content.reject") {
    return { text: t({ vi: "Một bản nháp đã được trả về để chỉnh lại.", en: "A draft was sent back for revision." }), tag: t({ vi: "Cần sửa", en: "Needs edit" }) };
  }
  if (event.job_kind === "content.reschedule") {
    return { text: t({ vi: "Một bài đã được đổi giờ đăng.", en: "A post was rescheduled." }), tag: t({ vi: "Đổi lịch", en: "Rescheduled" }) };
  }
  if (event.job_kind === "content.generate_drafts") {
    return { text: t({ vi: "Havi đã tạo bản nháp mới để bạn duyệt.", en: "Havi generated new drafts for review." }), tag: t({ vi: "Bản nháp", en: "New draft" }) };
  }
  return { text: t({ vi: "Workspace vừa có cập nhật mới.", en: "Workspace has a new update." }), tag: t({ vi: "Cập nhật", en: "Updated" }) };
}

export function DashboardScreen() {
  const { lang, t } = useLanguage();
  const [summary, setSummary] = useState<DashboardContentSummary | null>(null);
  const [activity, setActivity] = useState<DashboardActivityEvent[]>([]);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [sub, setSub] = useState<Subscription | null>(null);
  const [daysLeft, setDaysLeft] = useState(7);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activityError, setActivityError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  const dateLine = new Intl.DateTimeFormat(lang === "VN" ? "vi-VN" : "en-US", {
    timeZone: "Asia/Ho_Chi_Minh",
    weekday: "long",
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(new Date());

  const activityTime = new Intl.DateTimeFormat(lang === "VN" ? "vi-VN" : "en-US", {
    timeZone: "Asia/Ho_Chi_Minh",
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });

  useEffect(() => {
    let cancelled = false;
    async function run() {
      const [summaryResult, activityResult, subResult, leadsResult] = await Promise.all([
        fetchDashboardSummary(),
        fetchDashboardActivity(),
        fetchSubscription(),
        listLeads(),
      ]);
      if (cancelled) return;
      if (summaryResult.ok) {
        setSummary(summaryResult.data);
        setError(null);
      } else {
        setError(summaryResult.message);
      }
      if (activityResult.ok) {
        setActivity(activityResult.data);
        setActivityError(null);
      } else {
        setActivity([]);
        setActivityError(activityResult.message);
      }
      if (leadsResult.ok) {
        setLeads(leadsResult.data);
      }
      if (subResult.ok) {
        setSub(subResult.data);
        if (subResult.data.current_period_end) {
          const left = Math.max(
            0,
            Math.ceil(
              (new Date(subResult.data.current_period_end).getTime() - Date.now()) /
                (1000 * 60 * 60 * 24),
            ),
          );
          setDaysLeft(left);
        }
      }
      setLoading(false);
    }
    run();
    return () => {
      cancelled = true;
    };
  }, [reloadKey]);

  function getStatsList(summaryData: DashboardContentSummary) {
    return [
      { value: summaryData.pending_approval, label: t({ vi: "bài chờ duyệt", en: "posts pending review" }) },
      { value: summaryData.scheduled, label: t({ vi: "bài đã lên lịch", en: "scheduled posts" }) },
      { value: summaryData.failed, label: t({ vi: "bài đăng lỗi", en: "failed posts" }) },
    ];
  }

  const isTrial = !sub || sub.plan === "trial";

  const totalLeads = leads.length;
  const activeLeads = leads.filter(
    (l) => l.stage === "contacted" || l.stage === "qualified" || l.stage === "won",
  ).length;
  const qualifiedLeads = leads.filter(
    (l) => l.stage === "qualified" || l.stage === "won",
  ).length;
  const wonLeads = leads.filter((l) => l.stage === "won").length;
  const totalRevenue = leads.reduce((sum, l) => sum + (l.revenue_vnd || 0), 0);
  const progressPercent = totalLeads > 0 ? Math.round((wonLeads / totalLeads) * 100) : 0;
  const activeSources = Array.from(new Set(leads.map((lead) => lead.source)));
  const sourceLabel: Record<string, string> = {
    fanpage: "Facebook Fanpage",
    inbox: "Inbox",
    group: "Facebook Group",
    google_business: "Google Business",
    tiktok: "TikTok",
    maps: "Google Maps",
    crm: "CRM",
    pos: "POS",
  };
  const formattedRevenue = `${new Intl.NumberFormat(lang === "VN" ? "vi-VN" : "en-US", {
    maximumFractionDigits: 0,
  }).format(totalRevenue)} đ`;

  return (
    <>
      <header className={styles.header}>
        <h1 className={styles.title}>{t("dashboard.title", "Tổng quan hoạt động")}</h1>
        <p className={styles.subtitle}>
          {dateLine} — {t({ vi: "số liệu từ workspace này", en: "metrics from this workspace" })}
        </p>
      </header>

      {/* Trial Countdown / Beta Pilot Banner */}
      {isTrial ? (
        <section className={styles.trialBanner} aria-label="Thời hạn dùng thử">
          <div className={styles.trialContent}>
            <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
              <span className={styles.trialBadge}>
                ✨ {lang === "VN" ? `DÙNG THỬ CÒN ${daysLeft} NGÀY` : `${daysLeft} DAYS TRIAL LEFT`}
              </span>
              <span className={styles.trialTitle}>
                {t({
                  vi: "Trải nghiệm trọn vẹn nhân viên AI đa kênh của Havi",
                  en: "Experience full multi-channel AI marketing employee",
                })}
              </span>
            </div>
            <p className={styles.trialDesc}>
              {t({
                vi: "Tạo nội dung, duyệt trước khi đăng và theo dõi lead trên dữ liệu thật của workspace.",
                en: "Create content, review before publishing, and track leads from this workspace's real data.",
              })}
            </p>
          </div>
        </section>
      ) : null}

      {error ? (
        <ErrorState
          title={error}
          action={
            <Button variant="outline" onClick={() => setReloadKey((key) => key + 1)}>
              {t({ vi: "Thử lại", en: "Retry" })}
            </Button>
          }
        />
      ) : loading || !summary ? (
        <LoadingState title={t({ vi: "Đang tải tổng quan…", en: "Loading overview…" })} />
      ) : (
        <>
          {/* Quick Start Action Guide (Time-to-Value for New Users) */}
          {summary.published === 0 && totalLeads === 0 ? (
            <section className={styles.quickStartCard} aria-label="Hướng dẫn khởi động nhanh">
              <div className={styles.quickStartHeader}>
                <h2 className={styles.quickStartTitle}>
                  🚀 {t({ vi: "Khởi động nhanh: 3 bước để có khách đầu tiên", en: "Quick Start: 3 Steps to Your First Customer" })}
                </h2>
                <span className={styles.quickStartBadge}>
                  {t({ vi: "BẮT ĐẦU NGAY", en: "GET STARTED" })}
                </span>
              </div>
              <div className={styles.quickStartSteps}>
                <Link href="/app/settings" className={styles.quickStepItem}>
                  <span className={styles.quickStepNum}>1</span>
                  <div>
                    <strong className={styles.quickStepTitle}>{t({ vi: "Kết nối Fanpage / Kênh mạng xã hội", en: "Connect Fanpage / Channels" })}</strong>
                    <p className={styles.quickStepDesc}>{t({ vi: "Nối Facebook để duyệt, đăng bài và nhận inbox qua API chính thức.", en: "Connect Facebook to review, publish, and receive inbox events through official APIs." })}</p>
                  </div>
                  <span className={styles.quickStepArrow}>➔</span>
                </Link>
                <Link href="/app/content" className={styles.quickStepItem}>
                  <span className={styles.quickStepNum}>2</span>
                  <div>
                    <strong className={styles.quickStepTitle}>{t({ vi: "Tạo bài viết chiến dịch đầu tiên", en: "Create Your First Campaign Post" })}</strong>
                    <p className={styles.quickStepDesc}>{t({ vi: "Duyệt kịch bản AI đề xuất và lên lịch đăng.", en: "Review AI suggested drafts and schedule post." })}</p>
                  </div>
                  <span className={styles.quickStepArrow}>➔</span>
                </Link>
                <Link href="/app/inbox" className={styles.quickStepItem}>
                  <span className={styles.quickStepNum}>3</span>
                  <div>
                    <strong className={styles.quickStepTitle}>{t({ vi: "Trực hộp thư & Bắt lead tự động", en: "Inbox & Auto Lead Radar" })}</strong>
                    <p className={styles.quickStepDesc}>{t({ vi: "Bắt số điện thoại và chuyển đổi khách quan tâm thành lịch hẹn.", en: "Capture phone numbers and convert leads to bookings." })}</p>
                  </div>
                  <span className={styles.quickStepArrow}>➔</span>
                </Link>
              </div>
            </section>
          ) : null}

          {/* Customer Acquisition & Revenue Radar (Havi 2.0 OS) */}
          <section className={styles.revenueRadarCard} aria-label="Phễu tìm khách & doanh thu">
            <div className={styles.radarHeader}>
              <h2 className={styles.radarTitle}>
                🎯 {t({ vi: "Hệ Điều Hành Tìm Khách & Doanh Thu", en: "Customer Acquisition & Revenue Radar" })}

              </h2>
              <span className={styles.radarBadge}>
                ⚡ {t({ vi: "PHỄU KHÉP KÍN TỰ ĐỘNG", en: "CLOSED-LOOP FUNNEL" })}
              </span>
            </div>

            <div className={styles.goalProgressWrapper}>
              <div className={styles.goalProgressHeader}>
                <span>
                  {t({
                    vi: "Tỷ lệ lead đã chốt trên dữ liệu CRM hiện có",
                    en: "Won-lead rate from current CRM data",
                  })}
                </span>
                <span style={{ color: "#10b981", fontWeight: 800 }}>
                  {wonLeads}/{totalLeads} {t({ vi: "Đã chốt", en: "Won" })} ({progressPercent}%)
                </span>
              </div>
              <div className={styles.goalProgressBarBg}>
                <div className={styles.goalProgressBarFill} style={{ width: `${progressPercent}%` }} />
              </div>
            </div>

            <div className={styles.pipelineGrid}>
              <div className={styles.pipelineCol}>
                <span className={styles.pipelineStepNum}>Bước 1</span>
                <div className={styles.pipelineValue}>{totalLeads}</div>
                <div className={styles.pipelineLabel}>
                  {t({ vi: "Khách quan tâm", en: "Inquiries / Leads" })}
                </div>
                <span className={styles.pipelineSubtext}>{t({ vi: "Theo nguồn đã ghi nhận", en: "From recorded sources" })}</span>
              </div>

              <div className={styles.pipelineCol}>
                <span className={styles.pipelineStepNum}>Bước 2</span>
                <div className={styles.pipelineValue}>{activeLeads}</div>
                <div className={styles.pipelineLabel}>
                  {t({ vi: "Đang được chăm sóc", en: "In active follow-up" })}
                </div>
                <span className={styles.pipelineSubtext}>{t({ vi: "Theo trạng thái CRM", en: "From CRM stages" })}</span>
              </div>

              <div className={styles.pipelineCol}>
                <span className={styles.pipelineStepNum}>Bước 3</span>
                <div className={styles.pipelineValue}>{qualifiedLeads}</div>
                <div className={styles.pipelineLabel}>
                  {t({ vi: "Lead đủ điều kiện", en: "Qualified Leads" })}
                </div>
                <span className={styles.pipelineSubtext}>{t({ vi: "Chưa đồng nghĩa đã đến", en: "Not a verified visit" })}</span>
              </div>

              <div className={`${styles.pipelineCol} ${styles.pipelineColHighlight}`}>
                <span className={styles.pipelineStepNum}>Bước 4</span>
                <div className={styles.pipelineValue} style={{ color: "#10b981" }}>{wonLeads}</div>
                <div className={styles.pipelineLabel} style={{ color: "#15803D" }}>
                  {t({ vi: "Đã chốt", en: "Won" })}
                </div>
                <span className={styles.pipelineSubtext} style={{ color: "#15803D" }}>{t({ vi: "Trạng thái CRM", en: "CRM status" })}</span>
              </div>

              <div className={styles.pipelineCol}>
                <span className={styles.pipelineStepNum}>Doanh thu</span>
                <div className={styles.pipelineRevenueVal}>{formattedRevenue}</div>
                <div className={styles.pipelineLabel}>
                  {t({ vi: "Doanh thu mang lại", en: "Attributed Revenue" })}
                </div>
                <span className={styles.pipelineSubtext}>
                  {totalRevenue > 0
                    ? t({ vi: "Được ghi nhận từ POS", en: "Recorded from POS" })
                    : t({ vi: "Chưa có doanh thu POS được ghi nhận", en: "No POS revenue recorded yet" })}
                </span>
              </div>
            </div>

            <div className={styles.channelMetaRow}>
              <span>
                📍 <strong>{t({ vi: "Nguồn lead có dữ liệu:", en: "Lead sources with data:" })}</strong>{" "}
                {activeSources.length > 0
                  ? activeSources.map((source) => (
                      <span key={source} className={styles.channelBestTag}>{sourceLabel[source] ?? source}</span>
                    ))
                  : t({ vi: "Chưa có", en: "None yet" })}
              </span>
              <Link href="/app/leads" style={{ color: "var(--color-primary)", fontWeight: 700, textDecoration: "none", fontSize: "13px" }}>
                Xem chi tiết danh sách Lead & Lịch hẹn ➔
              </Link>
            </div>
          </section>

          <section className={styles.statsGrid} aria-label={t("dashboard.quickStats", "Thống kê nhanh")}>
            {getStatsList(summary).map((item) => (
              <div key={item.label} className={styles.cardButton}>
                <div className={styles.statValue}>{item.value}</div>
                <div className={styles.statLabel}>{item.label}</div>
              </div>
            ))}
          </section>

          <section className={styles.uploadCard}>
            <h2 className={styles.uploadTitle}>
              {t({ vi: "🚀 Thiết kế Chiến Dịch Tìm Khách Tuần Này", en: "Launch This Week's Customer Campaign" })}
            </h2>
            <p className={styles.uploadBody}>
              {t({
                vi: "Nhập gói dịch vụ, giá ưu đãi và số suất giới hạn — Havi tự động triển khai nội dung đa kênh dẫn thẳng về Messenger và trang đặt lịch.",
                en: "Enter your service offer, discount price and limited slots — Havi launches multi-channel campaigns leading directly to Messenger and booking.",
              })}
            </p>
            <div className={styles.uploadActions}>
              <Link href="/app/content" className={styles.primaryButton}>
                + {t("dashboard.createContent", "Tạo chiến dịch tìm khách")}
              </Link>
              <Link href="/app/content?tab=voice" className={styles.micButton}>
                🎙️ {t({ vi: "Nói để tạo bài", en: "Voice Note to Post" })}
              </Link>
            </div>
          </section>

          {/* Chỉ hiển thị dữ liệu có nguồn; không suy diễn ROI hoặc chi phí tiết kiệm. */}
          <section className={styles.roiCard} aria-label="Hiệu quả đầu tư">
            <div className={styles.roiHeader}>
              <h2 className={styles.roiTitle}>
                💎 {t({ vi: "Bằng Chứng Giá Trị Hiện Có", en: "Current Value Evidence" })}
              </h2>
              <span className={styles.roiBadge}>
                {t({ vi: "DỮ LIỆU WORKSPACE", en: "WORKSPACE DATA" })}
              </span>
            </div>

            <div className={styles.roiGrid}>
              <div className={styles.roiCol}>
                <span className={styles.roiLabel}>
                  {t({ vi: "Bài đã xuất bản", en: "Published Posts" })}
                </span>
                <span className={styles.roiValue}>{summary.published}</span>
                <span style={{ fontSize: "12px", color: "#94a3b8" }}>
                  {t({ vi: "Chỉ tính bài có trạng thái đã xuất bản", en: "Only platform-published records" })}
                </span>
              </div>

              <div className={`${styles.roiCol} ${styles.roiColHighlight}`}>
                <span className={styles.roiLabel}>
                  {t({ vi: "Lead đã chốt", en: "Won Leads" })}
                </span>
                <span className={`${styles.roiValue} ${styles.roiSavedValue}`}>{wonLeads}</span>
                <span style={{ fontSize: "12px", color: "#34d399" }}>
                  {t({ vi: "Theo trạng thái CRM của workspace", en: "From workspace CRM status" })}
                </span>
              </div>

              <div className={styles.roiCol}>
                <span className={styles.roiLabel}>
                  {t({ vi: "Doanh thu được ghi nhận", en: "Recorded Revenue" })}
                </span>
                <span className={`${styles.roiValue} ${styles.roiMultiValue}`}>{formattedRevenue}</span>
                <span style={{ fontSize: "12px", color: "#fbbf24" }}>
                  {t({ vi: "Từ webhook POS; không phải ROI ước tính", en: "From POS webhooks; not estimated ROI" })}
                </span>
              </div>
            </div>

            <p className={styles.roiFootnote}>
              💡 {t({
                vi: "Havi chưa suy diễn lượt khách đến, chi phí tiết kiệm hoặc ROI khi chưa có nguồn dữ liệu xác minh.",
                en: "Havi does not infer visits, savings, or ROI without a verified data source.",
              })}
            </p>
          </section>

          {/* Việc kích hoạt không tự ý gia hạn trial; mọi entitlement do backend quản lý. */}
          <section className={styles.tasksCard} aria-label="Nhiệm vụ kích hoạt tiệm">
            <div className={styles.tasksHeader}>
              <h2 className={styles.tasksTitle}>
                🎯 {t({
                  vi: "Việc Cần Hoàn Tất Để Nhận Giá Trị Thật",
                  en: "Tasks for Reaching Verified Value",
                })}
              </h2>
            </div>

            <div className={styles.tasksList}>
              <div className={styles.taskItem}>
                <div className={styles.taskContent}>
                  <span className={styles.taskIcon}>🔗</span>
                  <div>
                    <p className={styles.taskName}>
                      {t({ vi: "Nối Facebook Fanpage", en: "Connect a Facebook Page" })}
                    </p>
                    <p className={styles.taskDesc}>
                      {t({ vi: "Để duyệt đăng bài và nhận tin nhắn qua kết nối Meta", en: "Enable reviewed publishing and Meta inbox ingestion" })}
                    </p>
                  </div>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  <Link href="/app/connections" className={styles.taskActionBtn}>
                    {t({ vi: "Nối kênh ➔", en: "Connect ➔" })}
                  </Link>
                </div>
              </div>

              <div className={styles.taskItem}>
                <div className={styles.taskContent}>
                  <span className={styles.taskIcon}>✍️</span>
                  <div>
                    <p className={styles.taskName}>
                      {t({ vi: "Duyệt xuất bản bài viết đầu tiên", en: "Approve and publish your first post" })}
                    </p>
                    <p className={styles.taskDesc}>
                      {t({ vi: "Trải nghiệm tốc độ tạo bài 1-chạm của Havi", en: "Experience 1-tap fast publishing" })}
                    </p>
                  </div>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  <Link href="/app/content" className={styles.taskActionBtn}>
                    {t({ vi: "Tạo bài ➔", en: "Create ➔" })}
                  </Link>
                </div>
              </div>

              <div className={styles.taskItem}>
                <div className={styles.taskContent}>
                  <span className={styles.taskIcon}>📲</span>
                  <div>
                    <p className={styles.taskName}>
                      {t({ vi: "Cài app Havi lên màn hình điện thoại", en: "Install Havi App to Home Screen" })}
                    </p>
                    <p className={styles.taskDesc}>
                      {t({ vi: "Nhận thông báo khách nóng và duyệt bài tiện lợi mọi lúc", en: "Get instant hot lead alerts anywhere" })}
                    </p>
                  </div>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  <Link href="/app/settings" className={styles.taskActionBtn}>
                    {t({ vi: "Cài app ➔", en: "Install ➔" })}
                  </Link>
                </div>
              </div>
            </div>
          </section>

          <section className={styles.darkCard}>
            <div className={styles.darkHeader}>
              <h2 className={styles.darkTitle}>{t({ vi: "Việc cần xem tiếp", en: "Pending Tasks" })}</h2>
              <p className={styles.darkMeta}>{t({ vi: "Ưu tiên theo dữ liệu hiện có", en: "Prioritized by current activity" })}</p>
            </div>

            <div className={styles.suggestionsGrid}>
              {summary.pending_approval > 0 ? (
                <article className={styles.suggestionCard}>
                  <p className={styles.suggestionTag}>{t({ vi: "Chờ duyệt", en: "Pending Review" })}</p>
                  <p className={styles.suggestionText}>
                    {t({
                      vi: `Có ${summary.pending_approval} bài đang chờ xem lại trước khi lên lịch.`,
                      en: `There are ${summary.pending_approval} posts pending review before scheduling.`,
                    })}
                  </p>
                  <Link href="/app/content" className={styles.ghostButton}>
                    {t({ vi: "Xem bản nháp", en: "View Drafts" })}
                  </Link>
                </article>
              ) : null}

              {summary.scheduled > 0 ? (
                <article className={styles.suggestionCard}>
                  <p className={styles.suggestionTag}>{t({ vi: "Đã sẵn sàng", en: "Ready to Post" })}</p>
                  <p className={styles.suggestionText}>
                    {t({
                      vi: `${summary.scheduled} bài đã được duyệt và nằm trong lịch đăng.`,
                      en: `${summary.scheduled} posts approved and added to calendar.`,
                    })}
                  </p>
                  <Link href="/app/calendar" className={styles.successPill}>
                    {t("dashboard.viewCalendar", "Xem lịch đăng bài")}
                  </Link>
                </article>
              ) : null}

              {summary.pending_approval === 0 && summary.scheduled === 0 ? (
                <EmptyState
                  title={t({ vi: "Chưa có việc nào đang chờ", en: "No pending tasks" })}
                  body={t({ vi: "Khi có bản nháp hoặc bài đã lên lịch, Havi sẽ gom lại ở đây.", en: "Drafts and scheduled posts will appear here." })}
                />
              ) : null}
            </div>
          </section>

          <section className={styles.aiTipBanner}>
            <div className={styles.aiTipBadge}>💡 Mẹo AI Marketing</div>
            <div>
              <p className={styles.aiTipTitle}>
                {t({
                  vi: "Chuẩn bị video ngắn từ tư liệu thật của cơ sở",
                  en: "Prepare short videos from authentic business footage",
                })}
              </p>
              <p className={styles.aiTipBody}>
                {t({
                  vi: "Havi hỗ trợ hook, kịch bản và khung 9:16; hiệu quả thực tế được đo sau khi xuất bản.",
                  en: "Havi helps with hooks, scripts, and 9:16 framing; actual results are measured after publishing.",
                })}
              </p>
            </div>
            <Link href="/app/video-studio" className={styles.aiTipLink}>
              {t({ vi: "Mở Studio Video →", en: "Open Video Studio →" })}
            </Link>
          </section>

          <section className={styles.activityCard}>
            <p className={styles.sectionEyebrow}>{t("dashboard.recentActivity", "Hoạt động gần đây")}</p>
            {activityError ? (
              <p className={styles.activityError} role="alert">
                {activityError}
              </p>
            ) : activity.length === 0 ? (
              <EmptyState
                title={t({ vi: "Chưa có hoạt động gần đây", en: "No recent activity" })}
                body={t({ vi: "Hoạt động sáng tạo và đăng bài sẽ hiện ở đây.", en: "Content generation and publishing logs will show here." })}
              />
            ) : (
              <div className={styles.activityList}>
                {activity.map((event) => {
                  const copy = activityCopy(event, t);
                  return (
                    <article key={event.id} className={styles.activityItem}>
                      <p className={styles.activityTime}>
                        {activityTime.format(new Date(event.created_at))}
                      </p>
                      <p className={styles.activityText}>{copy.text}</p>
                      <span className={styles.activityTag}>{copy.tag}</span>
                    </article>
                  );
                })}
              </div>
            )}
          </section>
        </>
      )}
    </>
  );
}
