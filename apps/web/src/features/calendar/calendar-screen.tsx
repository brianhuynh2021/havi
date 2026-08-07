import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/state-views";
import { calendarFixture, type PublishStatus } from "./calendar.fixture";
import styles from "./calendar.module.css";

const statusLabel: Record<PublishStatus, string> = {
  scheduled: "Đã lên lịch",
  publishing: "Đang đăng",
  published: "Đã đăng",
  failed: "Đăng lỗi",
};

const statusTone: Record<PublishStatus, "success" | "info" | "warning" | "neutral"> = {
  scheduled: "info",
  publishing: "neutral",
  published: "success",
  failed: "warning",
};

export function CalendarScreen() {
  return (
    <>
      <header className={styles.header}>
        <h1 className={styles.title}>Lịch đăng</h1>
        <p className={styles.subtitle}>
          Bài đã duyệt tự xếp vào đúng ngày/giờ — múi giờ Asia/Ho_Chi_Minh.
        </p>
      </header>

      <section className={styles.grid} aria-label="Lịch đăng theo tuần">
        {calendarFixture.map((day) => (
          <div
            key={day.label}
            className={`${styles.dayColumn} ${day.isToday ? styles.dayColumnToday : ""}`}
          >
            <div className={styles.dayHeader}>
              <span className={styles.dayLabel}>{day.label}</span>
              <span className={styles.dayDate}>{day.dateLine}</span>
            </div>

            {day.posts.length === 0 ? (
              <p className={styles.dayEmpty}>Chưa có bài</p>
            ) : (
              <div className={styles.postList}>
                {day.posts.map((post) => (
                  <article key={post.id} className={styles.postCard}>
                    <div className={styles.postMeta}>
                      <span className={styles.postTime}>{post.time}</span>
                      <span className={styles.postChannel}>{post.channel}</span>
                    </div>
                    <p className={styles.postExcerpt}>{post.excerpt}</p>
                    <Badge tone={statusTone[post.status]}>
                      {statusLabel[post.status]}
                    </Badge>
                  </article>
                ))}
              </div>
            )}
          </div>
        ))}
      </section>

      {calendarFixture.every((day) => day.posts.length === 0) ? (
        <EmptyState
          title="Chưa có bài nào được lên lịch"
          body="Duyệt một bản nháp ở tab Tạo nội dung để thấy bài xuất hiện ở đây."
        />
      ) : null}
    </>
  );
}
