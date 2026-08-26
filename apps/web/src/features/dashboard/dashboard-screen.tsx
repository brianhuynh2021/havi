"use client";

/**
 * Tổng quan — bảng điều khiển vận hành, trả lời đúng sáu câu hỏi:
 *
 *   1. Các kênh có đang hoạt động bình thường không?
 *   2. Có bài nào đang chờ lên lịch?
 *   3. Có nội dung nào đang chờ duyệt?
 *   4. Có bài nào đăng thất bại?
 *   5. Có hội thoại nào chưa xử lý?
 *   6. Có kết nối nào cần xác thực lại?
 *
 * **Không hỏi "mục tiêu của bạn là gì".** Bản trước hiện phễu lead bốn bước,
 * thanh tiến độ "đã chốt / tổng", doanh thu quy cho Havi và một dải "PHỄU KHÉP
 * KÍN TỰ ĐỘNG" — tức là quản trị *kết quả kinh doanh của khách*, nằm ngoài phạm
 * vi sản phẩm. Havi quản trị hệ thống social; kết quả kinh doanh thuộc về doanh
 * nghiệp.
 *
 * Mỗi ô là một **việc cần làm hoặc một sự yên tâm**, không phải một thành tích.
 * Ô nào bằng 0 vẫn hiện, kèm câu "không có gì cần xử lý" — biết chắc mọi thứ
 * đang ổn cũng là thông tin, và giấu ô đi thì người dùng không phân biệt được
 * "ổn" với "chưa tải được".
 */

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { ErrorState, LoadingState } from "@/components/ui/state-views";
import { useLanguage } from "@/lib/i18n/language-context";
import { fetchDashboardSummary, type DashboardContentSummary } from "./dashboard.api";
import styles from "./dashboard.module.css";

type Tile = {
  key: string;
  /** Câu hỏi vận hành mà ô này trả lời. */
  question: string;
  count: number;
  /** Câu hiện khi `count === 0`. */
  calm: string;
  /** Câu hiện khi có việc; `{n}` thay bằng số. */
  busy: string;
  href: string;
  action: string;
  /** `true` = cần người xử lý, tô cảnh báo. */
  needsAttention: boolean;
};

export function DashboardScreen() {
  const { lang, t } = useLanguage();
  const [summary, setSummary] = useState<DashboardContentSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    const summaryResult = await fetchDashboardSummary();

    if (summaryResult.ok) {
      setSummary(summaryResult.data);
      setError(null);
    } else {
      setError(summaryResult.message);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const dateLine = new Intl.DateTimeFormat(lang === "VN" ? "vi-VN" : "en-US", {
    timeZone: "Asia/Ho_Chi_Minh",
    weekday: "long",
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(new Date());

  if (error && !summary) {
    return (
      <ErrorState
        title={error}
        action={
          <Button variant="outline" onClick={load}>
            {t({ vi: "Thử lại", en: "Retry" })}
          </Button>
        }
      />
    );
  }

  if (loading || !summary) {
    return <LoadingState title={t({ vi: "Đang tải tổng quan…", en: "Loading overview…" })} />;
  }

  const tiles: Tile[] = [
    {
      key: "connections",
      question: "Các kênh có hoạt động bình thường không?",
      count: summary.broken_connections,
      calm:
        summary.total_connections > 0
          ? `${summary.total_connections} kênh đang hoạt động bình thường`
          : "Chưa nối kênh nào — nối Facebook để bắt đầu",
      busy: "{n} kênh cần xác thực lại",
      href: "/app/connections",
      action: "Mở Kênh kết nối",
      needsAttention: summary.broken_connections > 0 || summary.total_connections === 0,
    },
    {
      key: "pending",
      question: "Có nội dung nào đang chờ duyệt?",
      count: summary.pending_approval,
      calm: "Không có nội dung nào chờ duyệt",
      busy: "{n} nội dung đang chờ người duyệt",
      href: "/app/content",
      action: "Duyệt nhanh →",
      needsAttention: summary.pending_approval > 0,
    },
    {
      key: "scheduled",
      question: "Có bài nào đang chờ lên lịch?",
      count: summary.scheduled,
      calm: "Chưa có bài nào được xếp lịch",
      busy: "{n} bài đã xếp lịch, chờ tới giờ",
      href: "/app/calendar",
      action: "Mở Lịch đăng",
      // Bài chờ tới giờ là chuyện bình thường, không phải sự cố.
      needsAttention: false,
    },
    {
      key: "failed",
      question: "Có bài nào đăng thất bại?",
      count: summary.failed,
      calm: "Không có bài nào thất bại",
      busy: "{n} bài chưa lên được kênh",
      href: "/app/calendar",
      action: "Xem lý do",
      needsAttention: summary.failed > 0,
    },
    {
      key: "inbox",
      question: "Có hội thoại nào chưa xử lý?",
      count: summary.unhandled_inbox,
      calm: "Không còn hội thoại nào chờ",
      busy: "{n} hội thoại chưa được trả lời",
      href: "/app/inbox",
      action: "Mở Hội thoại",
      needsAttention: summary.unhandled_inbox > 0,
    },
  ];

  const attention = tiles.filter((tile) => tile.needsAttention);
  const calm = tiles.filter((tile) => !tile.needsAttention);

  return (
    <>
      <header className={styles.header}>
        <h1 className={styles.title}>{t("dashboard.title", "Tổng quan")}</h1>
        <p className={styles.subtitle}>
          {dateLine} —{" "}
          {attention.length === 0
            ? "mọi thứ đang chạy bình thường"
            : `${attention.length} việc cần bạn xử lý`}
        </p>
      </header>

      {error ? (
        <p className={styles.partialError} role="status">
          Một phần số liệu chưa tải được: {error}
        </p>
      ) : null}

      {/*
        Ngoại lệ trước, phần yên ổn nén lại — khuôn của một bảng điều khiển vận
        hành, không phải một lưới thẻ.

        Bản trước hiện năm ô cùng kích cỡ: "3 nội dung chờ duyệt" trông ngang
        hàng với "không có bài nào thất bại". Mắt phải quét cả năm ô mới biết
        hôm nay cần làm gì. Ở đây việc cần làm chiếm hết bề ngang, còn những thứ
        đang ổn gộp thành một dải mỏng — vẫn hiện, vì biết chắc mọi thứ ổn cũng
        là thông tin, nhưng không giành chỗ của việc cần làm.
      */}
      {attention.length > 0 ? (
        <section className={styles.attentionList} aria-label="Việc cần xử lý">
          {attention.map((tile) => (
            <article key={tile.key} className={styles.attentionCard}>
              <div className={styles.attentionBody}>
                <p className={styles.tileQuestion}>{tile.question}</p>
                <p className={styles.attentionAnswer}>
                  {tile.count === 0
                    ? tile.calm
                    : tile.busy.replace("{n}", String(tile.count))}
                </p>
              </div>
              <Link href={tile.href} className={styles.attentionAction}>
                {tile.action}
              </Link>
            </article>
          ))}
        </section>
      ) : (
        <section className={styles.allClear} aria-label="Tình trạng vận hành">
          <span className={styles.allClearMark} aria-hidden="true">✓</span>
          <div>
            <p className={styles.allClearTitle}>Không có việc nào cần xử lý</p>
            <p className={styles.allClearBody}>
              Kênh đang hoạt động, không có bài nào thất bại, và mọi hội thoại
              đều đã được trả lời.
            </p>
          </div>
        </section>
      )}

      {/* Dải này KHÔNG có link. "Xem lý do →" dưới dòng "Không có bài nào thất
          bại" dẫn tới danh sách rỗng; một link luôn hiện dạy người dùng rằng bấm
          vào cũng chẳng để làm gì, rồi họ bỏ qua cả lúc nó thật sự cần bấm. */}
      {calm.length > 0 ? (
        <section className={styles.calmStrip} aria-label="Đang bình thường">
          {calm.map((tile) => (
            <div key={tile.key} className={styles.calmRow}>
              <span className={styles.calmMark} aria-hidden="true">✓</span>
              <span className={styles.calmText}>
                {tile.count === 0
                  ? tile.calm
                  : tile.busy.replace("{n}", String(tile.count))}
              </span>
            </div>
          ))}
        </section>
      ) : null}

    </>
  );
}
