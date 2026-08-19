"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useLanguage } from "@/lib/i18n/language-context";
import {
  approveNudge,
  dismissInboxItem,
  dismissNudge,
  getActiveWorkspaceId,
  listInbox,
  listLeads,
  listNudges,
  sendInboxReply,
  testTelegramAlert,
  triggerNudgeScan,
  type CrmNudge,
  type InboxItem,
  type Lead,
} from "./leads.api";
import styles from "./leads.module.css";

type BadgeTone = "success" | "info" | "warning" | "neutral" | "primary";

const statusTone: Record<string, BadgeTone> = {
  new: "neutral",
  drafted: "warning",
  awaiting_approval: "warning",
  pending_approval: "warning",
  sent: "success",
  dismissed: "neutral",
};

type Props = {
  defaultTab?: "inbox" | "leads";
};

export function LeadsScreen({ defaultTab = "inbox" }: Props) {
  const { t } = useLanguage();
  const workspaceId = getActiveWorkspaceId();
  const [activeTabOverride, setActiveTabOverride] = useState<"inbox" | "leads" | null>(null);
  const [prevDefaultTab, setPrevDefaultTab] = useState(defaultTab);
  if (defaultTab !== prevDefaultTab) {
    setPrevDefaultTab(defaultTab);
    setActiveTabOverride(null);
  }
  const activeTab = activeTabOverride ?? defaultTab;
  const setActiveTab = (tab: "inbox" | "leads") => setActiveTabOverride(tab);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [items, setItems] = useState<InboxItem[]>([]);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [nudges, setNudges] = useState<CrmNudge[]>([]);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [replyTextMap, setReplyTextMap] = useState<Record<string, string>>({});
  const [sendingId, setSendingId] = useState<string | null>(null);
  const [scanningNudges, setScanningNudges] = useState(false);
  const [processingNudgeId, setProcessingNudgeId] = useState<string | null>(null);
  const [testingTelegram, setTestingTelegram] = useState(false);
  const [telegramNotice, setTelegramNotice] = useState<string | null>(null);

  const handleTestTelegram = async () => {
    setTestingTelegram(true);
    setTelegramNotice(null);
    const res = await testTelegramAlert();
    if (res.ok) {
      setTelegramNotice(res.data);
      loadData();
    } else {
      setTelegramNotice(res.message);
    }
    setTestingTelegram(false);
  };

  const loadData = async () => {
    setLoading(true);
    setError(null);
    const [inboxRes, leadRes] = await Promise.all([listInbox(), listLeads()]);

    if (!inboxRes.ok) {
      setError(inboxRes.message);
      setLoading(false);
      return;
    }
    setItems(inboxRes.data);

    if (leadRes.ok) {
      setLeads(leadRes.data);
    }

    if (workspaceId) {
      const nudgeRes = await listNudges(workspaceId);
      if (nudgeRes.ok && Array.isArray(nudgeRes.data?.items)) {
        setNudges(nudgeRes.data.items);
      } else {
        setNudges([]);
      }
    }
    setLoading(false);
  };

  useEffect(() => {
    let isMounted = true;
    async function init() {
      const [inboxRes, leadRes] = await Promise.all([listInbox(), listLeads()]);
      if (!isMounted) return;
      if (!inboxRes.ok) {
        setError(inboxRes.message);
        setLoading(false);
        return;
      }
      setItems(inboxRes.data);
      if (leadRes.ok) {
        setLeads(leadRes.data);
      }

      if (workspaceId) {
        const nudgeRes = await listNudges(workspaceId);
        if (isMounted && nudgeRes.ok && Array.isArray(nudgeRes.data?.items)) {
          setNudges(nudgeRes.data.items);
        } else if (isMounted) {
          setNudges([]);
        }
      }
      setLoading(false);
    }
    init();
    return () => {
      isMounted = false;
    };
  }, [workspaceId]);

  const handleSend = async (id: string, text: string) => {
    setSendingId(id);
    const res = await sendInboxReply(id, text);
    setSendingId(null);
    if (res.ok) {
      setItems((prev) =>
        prev.map((item) => (item.id === id ? { ...item, status: "sent" as const, ai_suggested_reply: text } : item))
      );
      setEditingId(null);
    } else {
      alert(res.message);
    }
  };

  const handleDismiss = async (id: string) => {
    const res = await dismissInboxItem(id);
    if (res.ok) {
      setItems((prev) =>
        prev.map((item) => (item.id === id ? { ...item, status: "dismissed" as const } : item))
      );
    } else {
      alert(res.message);
    }
  };

  const handleScanNudges = async () => {
    if (!workspaceId) return;
    setScanningNudges(true);
    const res = await triggerNudgeScan(workspaceId, 30);
    setScanningNudges(false);
    if (res.ok) {
      const nudgeRes = await listNudges(workspaceId);
      if (nudgeRes.ok) {
        setNudges(nudgeRes.data.items);
      }
    } else {
      alert(res.message);
    }
  };

  const handleApproveNudge = async (nudgeId: string) => {
    if (!workspaceId) return;
    setProcessingNudgeId(nudgeId);
    const res = await approveNudge(workspaceId, nudgeId);
    setProcessingNudgeId(null);
    if (res.ok) {
      setNudges((prev) =>
        prev.map((n) => (n.id === nudgeId ? { ...n, status: "sent" } : n))
      );
    } else {
      alert(res.message);
    }
  };

  const handleDismissNudge = async (nudgeId: string) => {
    if (!workspaceId) return;
    setProcessingNudgeId(nudgeId);
    const res = await dismissNudge(workspaceId, nudgeId);
    setProcessingNudgeId(null);
    if (res.ok) {
      setNudges((prev) =>
        prev.map((n) => (n.id === nudgeId ? { ...n, status: "dismissed" } : n))
      );
    } else {
      alert(res.message);
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case "new":
        return t({ vi: "Mới", en: "New" });
      case "drafted":
      case "awaiting_approval":
      case "pending_approval":
        return t({ vi: "Chờ bạn duyệt", en: "Awaiting review" });
      case "sent":
        return t({ vi: "Đã gửi", en: "Sent" });
      case "dismissed":
        return t({ vi: "Đã bỏ qua", en: "Dismissed" });
      default:
        return status;
    }
  };

  const pendingDraftsCount = items.filter((i) => i.status === "drafted").length;
  const pendingNudgesCount = nudges.filter((n) => n.status === "pending_approval").length;

  return (
    <>
      <header className={styles.header}>
        <h1 className={styles.title}>
          {activeTab === "inbox"
            ? t("leads.inboxTitle", "Hộp Thư & AI Trực Tin Nhắn")
            : t("leads.title", "Khách Tiềm Năng & CRM Nudge")}
        </h1>
        <p className={styles.subtitle}>
          {activeTab === "inbox"
            ? t({
                vi: "Tự động phản hồi FAQ và trực tin nhắn 24/7 từ Facebook, Google Maps SEO, TikTok, YouTube",
                en: "Auto-reply FAQ and 24/7 inbox care across Facebook, Google Maps SEO, TikTok, YouTube",
              })
            : t({
                vi: "Quản lý danh sách khách hàng tự động trích xuất và gửi ưu đãi kích hoạt khách cũ",
                en: "Manage captured leads and re-engage inactive customers with personalized offers",
              })}
        </p>
      </header>

      {/* Segmented Tab Navigation Bar */}
      <div className={styles.tabBar} role="tablist" aria-label="Inbox and Leads Tabs">
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "inbox"}
          className={`${styles.tabBtn} ${activeTab === "inbox" ? styles.tabBtnActive : ""}`}
          onClick={() => setActiveTab("inbox")}
        >
          <span>💬 {t({ vi: "Hộp thư & AI Trả lời", en: "Inbox & AI Reply" })}</span>
          {pendingDraftsCount > 0 ? (
            <span className={styles.tabBadge}>{pendingDraftsCount}</span>
          ) : null}
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "leads"}
          className={`${styles.tabBtn} ${activeTab === "leads" ? styles.tabBtnActive : ""}`}
          onClick={() => setActiveTab("leads")}
        >
          <span>👥 {t({ vi: "Khách hàng & CRM Nudge", en: "Leads & CRM Nudge" })}</span>
          {leads.length > 0 ? (
            <span className={styles.tabBadgeMuted}>{leads.length}</span>
          ) : null}
          {pendingNudgesCount > 0 ? (
            <span className={styles.tabBadgeAlert}>⚡ {pendingNudgesCount}</span>
          ) : null}
        </button>
      </div>

      {error ? (
        <div className={styles.errorBox} role="alert">
          <p>{error}</p>
          <Button variant="outline" onClick={loadData}>
            {t({ vi: "Thử lại", en: "Retry" })}
          </Button>
        </div>
      ) : loading ? (
        <div className={styles.loadingState}>
          <p>{t({ vi: "Đang tải dữ liệu...", en: "Loading data..." })}</p>
        </div>
      ) : activeTab === "inbox" ? (
        <section className={styles.leadsList} aria-label="Inbox list">
          {items.length === 0 ? (
            <div className={styles.emptyState}>
              <p>{t({ vi: "Chưa có tin nhắn hoặc bình luận nào cần xử lý.", en: "No messages or comments yet." })}</p>
            </div>
          ) : (
            items.map((item) => {
              const currentReply = replyTextMap[item.id] ?? item.ai_suggested_reply ?? "";
              const isEditing = editingId === item.id;
              const isPending = item.status === "drafted";
              const phoneMatch = item.content.match(/(0\d{9,10}|\+84\d{9,10})/);

              return (
                <article key={item.id} className={styles.leadCard}>
                  <div className={styles.leadHeader}>
                    <div>
                      <p className={styles.leadName}>{item.author_name}</p>
                      <p className={styles.leadMeta}>
                        {item.platform} · {new Date(item.created_at).toLocaleString("vi-VN")}
                      </p>
                    </div>
                    <Badge tone={statusTone[item.status] || "neutral"}>
                      {getStatusLabel(item.status)}
                    </Badge>
                  </div>

                  <p className={styles.leadMessage}>&ldquo;{item.content}&rdquo;</p>

                  {phoneMatch ? (
                    <div className={styles.inboxHotLeadBadge}>
                      <span className={styles.inboxHotLeadText}>
                        🔥 {t({ vi: "Đã bắt được SĐT khách:", en: "Captured Phone:" })}{" "}
                        <strong>{phoneMatch[0]}</strong>
                      </span>
                      <div className={styles.hotActionsGroup}>
                        <a
                          href={`tel:${phoneMatch[0].replace(/[^0-9+]/g, "")}`}
                          className={styles.callActionBtn}
                        >
                          📞 {t({ vi: "Gọi ngay", en: "Call now" })}
                        </a>
                        <a
                          href={`https://zalo.me/${phoneMatch[0].replace(/[^0-9+]/g, "")}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className={styles.zaloActionBtn}
                        >
                          💬 {t({ vi: "Nhắn Zalo", en: "Chat Zalo" })}
                        </a>
                      </div>
                    </div>
                  ) : null}

                  {item.ai_suggested_reply ? (
                    <div className={styles.replyBox}>
                      <p className={styles.replyLabel}>
                        {t({ vi: "Havi gợi ý trả lời", en: "Havi Suggested Reply" })}
                      </p>
                      {isEditing ? (
                        <textarea
                          className={styles.replyInput}
                          value={currentReply}
                          onChange={(e) =>
                            setReplyTextMap((prev) => ({ ...prev, [item.id]: e.target.value }))
                          }
                          rows={3}
                        />
                      ) : (
                        <p className={styles.replyText}>{currentReply}</p>
                      )}
                    </div>
                  ) : null}

                  {isPending ? (
                    <div className={styles.leadActions}>
                      <Button
                        variant="primary"
                        disabled={sendingId === item.id}
                        onClick={() => handleSend(item.id, currentReply)}
                      >
                        {sendingId === item.id
                          ? t({ vi: "Đang gửi...", en: "Sending..." })
                          : t({ vi: "Duyệt & gửi", en: "Approve & Send" })}
                      </Button>

                      {isEditing ? (
                        <Button variant="outline" onClick={() => setEditingId(null)}>
                          {t({ vi: "Huỷ", en: "Cancel" })}
                        </Button>
                      ) : (
                        <Button variant="outline" onClick={() => setEditingId(item.id)}>
                          {t({ vi: "Sửa câu trả lời", en: "Edit reply" })}
                        </Button>
                      )}

                      <Button variant="ghost" onClick={() => handleDismiss(item.id)}>
                        {t({ vi: "Bỏ qua", en: "Dismiss" })}
                      </Button>
                    </div>
                  ) : null}
                </article>
              );
            })
          )}
        </section>
      ) : (
        <>
          {/* Hot Lead Radar Telegram Banner */}
          <div className={styles.radarBanner}>
            <div className={styles.radarLeft}>
              <div className={styles.radarPulse}>⚡</div>
              <div>
                <h3 className={styles.radarTitle}>
                  {t({
                    vi: "Hot Lead Radar — Chuông báo SĐT về Telegram",
                    en: "Hot Lead Radar — Instant Telegram Alert",
                  })}
                  <span className={styles.radarTag}>{t({ vi: "< 3 giây", en: "< 3s" })}</span>
                </h3>
                <p className={styles.radarDesc}>
                  {t({
                    vi: "Tự động báo chuông điện thoại của bạn ngay khi có khách để lại số điện thoại trên Fanpage hoặc TikTok.",
                    en: "Instantly alert your phone via Telegram whenever a customer leaves their phone number.",
                  })}
                </p>
              </div>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "8px", alignItems: "flex-end" }}>
              <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", alignItems: "center" }}>
                <Button
                  variant="outline"
                  disabled={testingTelegram}
                  onClick={handleTestTelegram}
                >
                  {testingTelegram ? "Đang bắn thử…" : "⚡ Bắn Thử Chuông Báo"}
                </Button>
                <a
                  href="https://t.me/HaviLeadAlertBot"
                  target="_blank"
                  rel="noopener noreferrer"
                  className={styles.radarBtn}
                >
                  🔔 {t({ vi: "Mở Bot Telegram", en: "Open Telegram Bot" })}
                </a>
              </div>
              {telegramNotice ? (
                <span style={{ fontSize: "12px", color: "#34d399", fontWeight: 700 }}>
                  ✓ {telegramNotice}
                </span>
              ) : null}
            </div>
          </div>

          {/* CRM Leads List */}
          <section className={styles.leadsSection} aria-label="Captured Leads List">
            <div className={styles.sectionHeader}>
              <div>
                <h2>{t({ vi: "📋 Danh sách khách hàng đã bắt số", en: "📋 Captured Leads" })} ({leads.length})</h2>
                <p className={styles.subtitle}>
                  {t({
                    vi: "Khách hàng để lại số điện thoại qua tin nhắn, bình luận hoặc khảo sát.",
                    en: "Leads with captured phone numbers from inbox, comments, or forms.",
                  })}
                </p>
              </div>
            </div>

            {leads.length === 0 ? (
              <div className={styles.emptyState}>
                <p>
                  {t({
                    vi: "Chưa có khách hàng nào để lại số điện thoại. Havi sẽ tự động bắt số khi khách inbox hỏi giá hoặc tư vấn.",
                    en: "No captured leads yet. Havi will automatically extract phone numbers from inbox conversations.",
                  })}
                </p>
              </div>
            ) : (
              <div className={styles.leadsGrid}>
                {leads.map((lead) => (
                  <article
                    key={lead.id}
                    className={`${styles.customerCard} ${lead.phone ? styles.hotLeadCard : ""}`}
                  >
                    <div className={styles.leadHeader}>
                      <div className={styles.customerInfo}>
                        <div className={styles.avatarCircle}>
                          {(lead.name || "K")[0].toUpperCase()}
                        </div>
                        <div>
                          <p className={styles.leadName}>{lead.name || t({ vi: "Khách hàng", en: "Customer" })}</p>
                          <p className={styles.leadMeta}>
                            {lead.source} · {new Date(lead.created_at).toLocaleDateString("vi-VN")}
                          </p>
                        </div>
                      </div>
                      <Badge tone={lead.stage === "won" ? "success" : "info"}>
                        {lead.stage === "won"
                          ? t({ vi: "Đã chốt đơn", en: "Won" })
                          : t({ vi: "Tiềm năng", en: "Qualified" })}
                      </Badge>
                    </div>

                    {lead.phone ? (
                      <div className={styles.phoneRow}>
                        <span className={styles.phoneLabel}>📞 SĐT:</span>
                        <a href={`tel:${lead.phone.replace(/[^0-9+]/g, "")}`} className={styles.phoneLink}>
                          {lead.phone}
                        </a>
                      </div>
                    ) : null}

                    {lead.phone ? (
                      <div className={styles.hotActionsGroup}>
                        <a
                          href={`tel:${lead.phone.replace(/[^0-9+]/g, "")}`}
                          className={styles.callActionBtn}
                        >
                          📞 {t({ vi: "Gọi điện ngay", en: "Call now" })}
                        </a>
                        <a
                          href={`https://zalo.me/${lead.phone.replace(/[^0-9+]/g, "")}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className={styles.zaloActionBtn}
                        >
                          💬 {t({ vi: "Nhắn Zalo", en: "Chat Zalo" })}
                        </a>
                      </div>
                    ) : null}

                    {lead.message ? (
                      <p className={styles.leadNote}>
                        &ldquo;{lead.message}&rdquo;
                      </p>
                    ) : null}
                  </article>
                ))}
              </div>
            )}
          </section>

          {/* CRM Re-engagement Nudge Section */}
          <section className={styles.nudgeSection} aria-label="CRM Nudges">
            <div className={styles.nudgeHeader}>
              <div>
                <h2>{t({ vi: "🔔 Chăm sóc khách cũ tự động (>30 ngày)", en: "🔔 CRM Re-engagement (>30 Days)" })}</h2>
                <p className={styles.subtitle}>
                  {t({
                    vi: "Havi tự động soạn tin nhắn ưu đãi cá nhân hoá để kéo khách quay lại tiệm.",
                    en: "Havi auto-generates personalized discount messages to bring customers back.",
                  })}
                </p>
              </div>
              <Button
                variant="outline"
                disabled={scanningNudges || !workspaceId}
                onClick={handleScanNudges}
              >
                {scanningNudges
                  ? t({ vi: "Đang quét...", en: "Scanning..." })
                  : t({ vi: "⚡ Quét khách cũ ngay", en: "⚡ Scan Inactive Leads" })}
              </Button>
            </div>

            {(nudges ?? []).length === 0 ? (
              <div className={styles.emptyState}>
                <p>
                  {t({
                    vi: "Chưa có tin nhắn chăm sóc khách cũ nào cần duyệt. Bấm 'Quét khách cũ ngay' để tìm khách chưa quay lại.",
                    en: "No pending re-engagement nudges. Click 'Scan Inactive Leads' to find inactive customers.",
                  })}
                </p>
              </div>
            ) : (
              (nudges ?? []).map((nudge) => {
                const isPending = nudge.status === "pending_approval";
                const isProcessing = processingNudgeId === nudge.id;

                return (
                  <article key={nudge.id} className={styles.nudgeCard}>
                    <div className={styles.leadHeader}>
                      <div>
                        <p className={styles.leadName}>
                          {t({ vi: "Khách hàng thân thiết", en: "Valued Customer" })}
                        </p>
                        <p className={styles.leadMeta}>
                          {t({ vi: "Loại: Khách >30 ngày chưa ghé", en: "Type: >30 Days Inactive" })} · {new Date(nudge.created_at).toLocaleDateString("vi-VN")}
                        </p>
                      </div>
                      <Badge tone={statusTone[nudge.status] || "neutral"}>
                        {getStatusLabel(nudge.status)}
                      </Badge>
                    </div>

                    <div className={styles.nudgeMessage}>
                      <p>{nudge.message}</p>
                    </div>

                    {isPending ? (
                      <div className={styles.leadActions}>
                        <Button
                          variant="primary"
                          disabled={isProcessing}
                          onClick={() => handleApproveNudge(nudge.id)}
                        >
                          {isProcessing
                            ? t({ vi: "Đang xử lý...", en: "Processing..." })
                            : t({ vi: "Duyệt & Gửi tin nhắn", en: "Approve & Send" })}
                        </Button>
                        <Button
                          variant="ghost"
                          disabled={isProcessing}
                          onClick={() => handleDismissNudge(nudge.id)}
                        >
                          {t({ vi: "Bỏ qua", en: "Dismiss" })}
                        </Button>
                      </div>
                    ) : null}
                  </article>
                );
              })
            )}
          </section>
        </>
      )}
    </>
  );
}
