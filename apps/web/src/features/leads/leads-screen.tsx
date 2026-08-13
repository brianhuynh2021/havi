"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useLanguage } from "@/lib/i18n/language-context";
import {
  dismissInboxItem,
  listInbox,
  listLeads,
  sendInboxReply,
  type InboxItem,
  type Lead,
} from "./leads.api";
import styles from "./leads.module.css";

type BadgeTone = "success" | "info" | "warning" | "neutral" | "primary";

const statusTone: Record<string, BadgeTone> = {
  new: "neutral",
  drafted: "warning",
  awaiting_approval: "warning",
  sent: "success",
  dismissed: "neutral",
};

export function LeadsScreen() {
  const { t } = useLanguage();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [items, setItems] = useState<InboxItem[]>([]);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [replyTextMap, setReplyTextMap] = useState<Record<string, string>>({});
  const [sendingId, setSendingId] = useState<string | null>(null);

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
      setLoading(false);
    }
    init();
    return () => {
      isMounted = false;
    };
  }, []);

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

  const getStatusLabel = (status: string) => {
    switch (status) {
      case "new":
        return t({ vi: "Mới", en: "New" });
      case "drafted":
      case "awaiting_approval":
        return t({ vi: "Chờ bạn duyệt", en: "Awaiting review" });
      case "sent":
        return t({ vi: "Đã gửi", en: "Sent" });
      case "dismissed":
        return t({ vi: "Đã bỏ qua", en: "Dismissed" });
      default:
        return status;
    }
  };

  return (
    <>
      <header className={styles.header}>
        <h1 className={styles.title}>{t("leads.title", "Hộp Thư & Khách Tiềm Năng")}</h1>
        <p className={styles.subtitle}>
          {t("leads.subtitle", "Tự động phản hồi FAQ và quản lý khách hàng từ Zalo, Facebook, Google")}
        </p>
      </header>

      {error ? (
        <div className={styles.errorBox} role="alert">
          <p>{error}</p>
          <Button variant="outline" onClick={loadData}>
            {t({ vi: "Thử lại", en: "Retry" })}
          </Button>
        </div>
      ) : loading ? (
        <div className={styles.loadingState}>
          <p>{t({ vi: "Đang tải hộp thư...", en: "Loading inbox..." })}</p>
        </div>
      ) : (
        <section className={styles.leadsList} aria-label="Inbox list">
          {items.length === 0 ? (
            <div className={styles.emptyState}>
              <p>{t({ vi: "Chưa có tin nhắn hoặc bình luận nào.", en: "No messages or comments yet." })}</p>
            </div>
          ) : (
            items.map((item) => {
              const currentReply = replyTextMap[item.id] ?? item.ai_suggested_reply ?? "";
              const isEditing = editingId === item.id;
              const isPending = item.status === "drafted";

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

          {leads.length > 0 ? (
            <div className={styles.leadSectionHeader}>
              <h2>{t({ vi: "Khách hàng ghi nhận", en: "Captured Leads" })} ({leads.length})</h2>
            </div>
          ) : null}
        </section>
      )}
    </>
  );
}
