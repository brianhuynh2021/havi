"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useLanguage } from "@/lib/i18n/language-context";
import { faqStripFixture, leadsFixture, type LeadReplyStatus } from "./leads.fixture";
import styles from "./leads.module.css";

const statusTone: Record<LeadReplyStatus, "success" | "info" | "warning" | "neutral"> = {
  new: "neutral",
  auto_replied: "info",
  awaiting_approval: "warning",
  sent: "success",
  booked: "success",
};

export function LeadsScreen() {
  const { t } = useLanguage();
  const [statuses, setStatuses] = useState<Record<string, LeadReplyStatus>>(() =>
    Object.fromEntries(leadsFixture.map((lead) => [lead.id, lead.status])),
  );

  const statusLabel: Record<LeadReplyStatus, string> = {
    new: t({ vi: "Mới", en: "New" }),
    auto_replied: t({ vi: "Đã trả lời tự động", en: "Auto-replied" }),
    awaiting_approval: t({ vi: "Chờ bạn duyệt", en: "Awaiting review" }),
    sent: t({ vi: "Đã gửi", en: "Sent" }),
    booked: t({ vi: "Đã đặt lịch", en: "Booked" }),
  };

  async function send(id: string) {
    setStatuses((prev) => ({ ...prev, [id]: "sent" }));
  }

  return (
    <>
      <header className={styles.header}>
        <h1 className={styles.title}>{t("leads.title", "Khách Tiềm Năng & Hộp Thư")}</h1>
        <p className={styles.subtitle}>
          {t("leads.subtitle", "Tự động phản hồi FAQ và quản lý khách hàng từ Zalo, Facebook, Google")}
        </p>
      </header>

      <section className={styles.faqStrip} aria-label="FAQ">
        <p className={styles.faqLabel}>
          {t({ vi: "FAQ đã duyệt — trả lời ngay tự động", en: "Approved FAQs — instant auto-reply" })}
        </p>
        <div className={styles.faqChips}>
          {faqStripFixture.map((faq) => (
            <span key={faq.id} className={styles.faqChip}>
              <strong>{faq.question}</strong> {faq.answer}
            </span>
          ))}
        </div>
      </section>

      <section className={styles.leadsList} aria-label="Leads list">
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
                <p className={styles.replyLabel}>{t({ vi: "Havi gợi ý trả lời", en: "Havi Suggested Reply" })}</p>
                <p className={styles.replyText}>{lead.suggestedReply}</p>
              </div>

              {status === "awaiting_approval" ? (
                <div className={styles.leadActions}>
                  <Button variant="primary" onClick={() => send(lead.id)}>
                    {t({ vi: "Duyệt & gửi", en: "Approve & Send" })}
                  </Button>
                  <Button variant="outline">{t({ vi: "Sửa câu trả lời", en: "Edit reply" })}</Button>
                </div>
              ) : null}
            </article>
          );
        })}
      </section>
    </>
  );
}
