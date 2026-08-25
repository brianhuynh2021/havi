"use client";

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/state-views";
import {
  dismissInboxItem,
  listInbox,
  sendInboxReply,
  type InboxItem,
} from "./inbox.api";
import styles from "./inbox.module.css";

const platformName: Record<string, string> = {
  facebook: "Facebook",
  google_business: "Google Business Profile",
  tiktok: "TikTok",
  youtube: "YouTube",
  zalo_oa: "Zalo OA",
};

const statusName: Record<string, string> = {
  new: "Mới",
  drafted: "Có bản nháp",
  sent: "Đã trả lời",
  failed: "Gửi thất bại",
  dismissed: "Đã bỏ qua",
};

export function InboxScreen() {
  const [items, setItems] = useState<InboxItem[]>([]);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [busyId, setBusyId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    const result = await listInbox();
    if (result.ok) {
      setItems(result.data);
      setDrafts(Object.fromEntries(result.data.map((item) => [item.id, item.ai_suggested_reply ?? ""])));
      setError(null);
    } else {
      setError(result.message);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function send(item: InboxItem) {
    const text = (drafts[item.id] ?? "").trim();
    if (!text) return;
    setBusyId(item.id);
    const result = await sendInboxReply(item.id, text);
    if (result.ok) {
      setItems((current) => current.map((row) => (row.id === item.id ? result.data : row)));
      setError(null);
    } else {
      setError(result.message);
    }
    setBusyId(null);
  }

  async function dismiss(item: InboxItem) {
    setBusyId(item.id);
    const result = await dismissInboxItem(item.id);
    if (result.ok) {
      setItems((current) =>
        current.map((row) => (row.id === item.id ? { ...row, status: "dismissed" } : row)),
      );
      setError(null);
    } else {
      setError(result.message);
    }
    setBusyId(null);
  }

  if (loading) return <LoadingState title="Đang tải hội thoại…" />;
  if (error && items.length === 0) {
    return <ErrorState title={error} action={<Button variant="outline" onClick={load}>Thử lại</Button>} />;
  }

  return (
    <>
      <header className={styles.header}>
        <h1>Hội thoại</h1>
        <p>Tin nhắn, bình luận và đánh giá từ các kênh đã kết nối.</p>
      </header>

      {error ? <p className={styles.error} role="alert">{error}</p> : null}

      {items.length === 0 ? (
        <EmptyState title="Chưa có hội thoại" body="Hội thoại mới từ các kênh đã kết nối sẽ xuất hiện tại đây." />
      ) : (
        <section className={styles.list} aria-label="Danh sách hội thoại">
          {items.map((item) => {
            const closed = item.status === "sent" || item.status === "dismissed";
            return (
              <article key={item.id} className={styles.card}>
                <div className={styles.meta}>
                  <strong>{item.author_name}</strong>
                  <span>{platformName[item.platform] ?? item.platform}</span>
                  <span>{statusName[item.status] ?? item.status}</span>
                  <time dateTime={item.created_at}>{new Date(item.created_at).toLocaleString("vi-VN")}</time>
                </div>
                <p className={styles.message}>{item.content}</p>
                {!closed ? (
                  <div className={styles.reply}>
                    <label htmlFor={`reply-${item.id}`}>Bản nháp trả lời — kiểm tra trước khi gửi</label>
                    <textarea
                      id={`reply-${item.id}`}
                      value={drafts[item.id] ?? ""}
                      onChange={(event) => setDrafts((current) => ({ ...current, [item.id]: event.target.value }))}
                      rows={3}
                    />
                    <div className={styles.actions}>
                      <Button onClick={() => void send(item)} disabled={busyId === item.id || !(drafts[item.id] ?? "").trim()}>
                        {busyId === item.id ? "Đang xử lý…" : "Gửi trả lời"}
                      </Button>
                      <Button variant="outline" onClick={() => void dismiss(item)} disabled={busyId === item.id}>Bỏ qua</Button>
                    </div>
                  </div>
                ) : null}
              </article>
            );
          })}
        </section>
      )}
    </>
  );
}
