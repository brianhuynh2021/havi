"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { faqStripFixture, leadsFixture, type LeadReplyStatus } from "./leads.fixture";
import styles from "./leads.module.css";

const statusLabel: Record<LeadReplyStatus, string> = {
  new: "Mới",
  auto_replied: "Đã trả lời tự động",
  awaiting_approval: "Chờ chị duyệt",
  sent: "Đã gửi",
  booked: "Đã đặt lịch",
};

const statusTone: Record<LeadReplyStatus, "success" | "info" | "warning" | "neutral"> = {
  new: "neutral",
  auto_replied: "info",
  awaiting_approval: "warning",
  sent: "success",
  booked: "success",
};

export function LeadsScreen() {
  const [statuses, setStatuses] = useState<Record<string, LeadReplyStatus>>(() =>
    Object.fromEntries(leadsFixture.map((lead) => [lead.id, lead.status])),
  );

  async function send(id: string) {
    setStatuses((prev) => ({ ...prev, [id]: "sent" }));
  }

  return (
    <>
      <header className={styles.header}>
        <h1 className={styles.title}>Khách tiềm năng</h1>
        <p className={styles.subtitle}>
          Havi soạn sẵn câu trả lời — chị duyệt rồi mới gửi, trừ câu FAQ đã chốt.
        </p>
      </header>

      <section className={styles.faqStrip} aria-label="FAQ đã duyệt sẵn">
        <p className={styles.faqLabel}>FAQ đã duyệt — trả lời ngay, không cần chờ</p>
        <div className={styles.faqChips}>
          {faqStripFixture.map((faq) => (
            <span key={faq.id} className={styles.faqChip}>
              <strong>{faq.question}</strong> {faq.answer}
            </span>
          ))}
        </div>
      </section>

      <section className={styles.leadsList} aria-label="Danh sách khách tiềm năng">
        {leadsFixture.map((lead) => {
          const status = statuses[lead.id];
          return (
            <article key={lead.id} className={styles.leadCard}>
              <div className={styles.leadHeader}>
                <div>
                  <p className={styles.leadName}>{lead.name}</p>
                  <p className={styles.leadMeta}>
                    {lead.source} · {lead.time}
                  </p>
                </div>
                <Badge tone={statusTone[status]}>{statusLabel[status]}</Badge>
              </div>

              <p className={styles.leadMessage}>&ldquo;{lead.message}&rdquo;</p>

              <div className={styles.replyBox}>
                <p className={styles.replyLabel}>Havi gợi ý trả lời</p>
                <p className={styles.replyText}>{lead.suggestedReply}</p>
              </div>

              {status === "awaiting_approval" ? (
                <div className={styles.leadActions}>
                  <Button variant="primary" onClick={() => send(lead.id)}>
                    Duyệt & gửi
                  </Button>
                  <Button variant="outline">Sửa câu trả lời</Button>
                </div>
              ) : null}
            </article>
          );
        })}
      </section>
    </>
  );
}
