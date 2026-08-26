"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
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
  google_business: "Google Business",
  tiktok: "TikTok",
  youtube: "YouTube",
  zalo_oa: "Zalo OA",
};

interface Thread {
  id: string; // author_name + "::" + platform
  author_name: string;
  platform: string;
  items: InboxItem[];
  latest_created_at: string;
  hasUnread: boolean;
}

export function InboxScreen() {
  const [items, setItems] = useState<InboxItem[]>([]);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [busyId, setBusyId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  const load = useCallback(async () => {
    setLoading(true);
    const result = await listInbox();
    if (result.ok) {
      setItems(result.data);
      // Giữ bản nháp cũ, bổ sung bản nháp mới từ backend
      setDrafts((current) => {
        const newDrafts = { ...current };
        result.data.forEach((item) => {
          if (!newDrafts[item.id] && item.ai_suggested_reply && item.status !== "sent") {
            newDrafts[item.id] = item.ai_suggested_reply;
          }
        });
        return newDrafts;
      });
      setError(null);
    } else {
      setError(result.message);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  // Gom nhóm thành Thread
  const threads = useMemo(() => {
    const map = new Map<string, Thread>();
    items.forEach((item) => {
      const threadId = `${item.author_name}::${item.platform}`;
      if (!map.has(threadId)) {
        map.set(threadId, {
          id: threadId,
          author_name: item.author_name,
          platform: item.platform,
          items: [],
          latest_created_at: item.created_at,
          hasUnread: false,
        });
      }
      const thread = map.get(threadId)!;
      thread.items.push(item);
      if (item.created_at > thread.latest_created_at) {
        thread.latest_created_at = item.created_at;
      }
      if (item.status === "new" || item.status === "drafted" || item.status === "failed") {
        thread.hasUnread = true;
      }
    });

    return Array.from(map.values()).sort((a, b) => 
      new Date(b.latest_created_at).getTime() - new Date(a.latest_created_at).getTime()
    );
  }, [items]);

  // Lọc Thread
  const filteredThreads = useMemo(() => {
    return threads.filter(t => {
      if (statusFilter === "unread" && !t.hasUnread) return false;
      if (statusFilter === "resolved" && t.hasUnread) return false;
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        const matchName = t.author_name.toLowerCase().includes(q);
        const matchContent = t.items.some(i => i.content.toLowerCase().includes(q));
        if (!matchName && !matchContent) return false;
      }
      return true;
    });
  }, [threads, searchQuery, statusFilter]);

  const activeThread = useMemo(() => {
    return threads.find(t => t.id === activeThreadId) || null;
  }, [threads, activeThreadId]);

  // Lấy item cuối cùng đang chờ xử lý để làm Composer target
  const pendingItem = useMemo(() => {
    if (!activeThread) return null;
    return activeThread.items.find(i => i.status === "new" || i.status === "drafted" || i.status === "failed") || null;
  }, [activeThread]);

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
    <div className={styles.container}>
      <header className={styles.header}>
        <h1>Hội thoại</h1>
        <p>Phản hồi khách hàng từ tất cả các kênh tại một nơi.</p>
      </header>

      {error ? <div className={styles.error} role="alert">{error}</div> : null}

      <div className={styles.workspace}>
        {/* Sidebar */}
        <aside className={styles.sidebar}>
          <div className={styles.sidebarHeader}>
            <div className={styles.searchBar}>
              <input 
                type="search" 
                placeholder="Tìm khách hàng hoặc tin nhắn..." 
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
              />
              <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
                <option value="all">Tất cả</option>
                <option value="unread">Cần trả lời</option>
                <option value="resolved">Đã xong</option>
              </select>
            </div>
          </div>
          
          <div className={styles.threadList}>
            {filteredThreads.length === 0 ? (
              <div style={{ padding: "20px", textAlign: "center", color: "var(--color-muted)", fontSize: "14px" }}>
                Không tìm thấy hội thoại nào
              </div>
            ) : (
              filteredThreads.map(thread => {
                const latestItem = thread.items.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())[0];
                return (
                  <div 
                    key={thread.id} 
                    className={`${styles.threadItem} ${activeThreadId === thread.id ? styles.threadItemActive : ""}`}
                    onClick={() => setActiveThreadId(thread.id)}
                  >
                    <div className={styles.threadHeader}>
                      <span className={styles.threadName}>{thread.author_name}</span>
                      <span className={styles.threadTime}>
                        {new Date(thread.latest_created_at).toLocaleDateString("vi-VN", { month: "short", day: "numeric" })}
                      </span>
                    </div>
                    <span className={styles.threadPlatform}>{platformName[thread.platform] ?? thread.platform}</span>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span className={`${styles.threadPreview} ${thread.hasUnread ? styles.threadPreviewUnread : ""}`}>
                        {latestItem.content}
                      </span>
                      {thread.hasUnread && <span className={styles.badgeIndicator} />}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </aside>

        {/* Main Panel */}
        <main className={styles.mainPanel}>
          {activeThread ? (
            <>
              <div className={styles.mainHeader}>
                <div className={styles.mainHeaderTitle}>{activeThread.author_name}</div>
                <span className={styles.threadPlatform}>{platformName[activeThread.platform] ?? activeThread.platform}</span>
              </div>
              
              <div className={styles.chatHistory}>
                {activeThread.items
                  .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())
                  .map(item => (
                    <div key={item.id} style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                      {/* Customer Message */}
                      <div className={`${styles.bubbleWrapper} ${styles.bubbleIncoming}`}>
                        <div className={styles.bubbleContent}>{item.content}</div>
                        <span className={styles.bubbleMeta}>
                          {new Date(item.created_at).toLocaleTimeString("vi-VN", { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>

                      {/* System/Dismissed Notice */}
                      {item.status === "dismissed" && (
                        <div className={styles.systemMessage}>
                          Đã bỏ qua tin nhắn này
                        </div>
                      )}
                      
                      {/* Shop Reply */}
                      {item.status === "sent" && item.ai_suggested_reply && (
                        <div className={`${styles.bubbleWrapper} ${styles.bubbleOutgoing}`}>
                          <div className={styles.bubbleContent}>{item.ai_suggested_reply}</div>
                          <span className={styles.bubbleMeta}>
                            Havi gửi • {new Date(item.created_at).toLocaleTimeString("vi-VN", { hour: '2-digit', minute: '2-digit' })}
                          </span>
                        </div>
                      )}
                    </div>
                ))}
              </div>

              {pendingItem && (
                <div className={styles.composer}>
                  <label htmlFor={`reply-${pendingItem.id}`}>
                    Trả lời {activeThread.author_name}
                  </label>
                  <textarea
                    id={`reply-${pendingItem.id}`}
                    placeholder="Nhập câu trả lời của bạn..."
                    value={drafts[pendingItem.id] ?? ""}
                    onChange={(event) => setDrafts((current) => ({ ...current, [pendingItem.id]: event.target.value }))}
                    rows={3}
                  />
                  <div className={styles.composerActions}>
                    <Button variant="outline" onClick={() => void dismiss(pendingItem)} disabled={busyId === pendingItem.id}>
                      Bỏ qua
                    </Button>
                    <Button onClick={() => void send(pendingItem)} disabled={busyId === pendingItem.id || !(drafts[pendingItem.id] ?? "").trim()}>
                      {busyId === pendingItem.id ? "Đang xử lý…" : "Gửi trả lời"}
                    </Button>
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className={styles.chatEmpty}>
              Chọn một hội thoại ở danh sách bên trái để bắt đầu
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
