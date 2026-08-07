import { dashboardFixture } from "./dashboard.fixture";
import styles from "./dashboard.module.css";

export function DashboardScreen() {
  const dashboard = dashboardFixture;

  return (
    <>
      <header className={styles.header}>
        <h1 className={styles.title}>{dashboard.greeting}</h1>
        <p className={styles.subtitle}>{dashboard.dateLine}</p>
      </header>

      <section className={styles.statsGrid} aria-label="Thống kê nhanh">
        {dashboard.stats.map((item) => (
          <button key={item.label} type="button" className={styles.cardButton}>
            <div className={styles.statValue}>{item.value}</div>
            <div className={styles.statLabel}>{item.label}</div>
          </button>
        ))}
      </section>

      <section className={styles.uploadCard}>
        <h2 className={styles.uploadTitle}>Có gì mới ở tiệm hôm nay?</h2>
        <p className={styles.uploadBody}>
          Thả vài tấm ảnh, ghi âm 1 phút, hoặc gõ vài dòng. Havi sẽ lo phần còn
          lại — viết bài, chỉnh ảnh và lên lịch đăng.
        </p>
        <button type="button" className={styles.primaryButton}>
          + Tạo nội dung mới
        </button>
      </section>

      <section className={styles.darkCard}>
        <div className={styles.darkHeader}>
          <h2 className={styles.darkTitle}>
            Hôm nay chị bận? Havi vẫn có bài sẵn
          </h2>
          <p className={styles.darkMeta}>
            Tiệm không &quot;im hơi&quot; ngày nào — khách sẽ không quên chị
          </p>
        </div>

        <div className={styles.suggestionsGrid}>
          {dashboard.suggestions.map((item) => (
            <article key={item.text} className={styles.suggestionCard}>
              <p className={styles.suggestionTag}>{item.tag}</p>
              <p className={styles.suggestionText}>{item.text}</p>
              {item.done ? (
                <span className={styles.successPill}>
                  Đã lên lịch · {item.time}
                </span>
              ) : (
                <button type="button" className={styles.ghostButton}>
                  Duyệt, đăng giúp tôi
                </button>
              )}
            </article>
          ))}
        </div>
      </section>

      <section className={styles.zaloBanner}>
        <div className={styles.zaloBadge}>Zalo</div>
        <div>
          <p className={styles.zaloTitle}>
            Không cần mở app — duyệt ngay trong Zalo
          </p>
          <p className={styles.zaloBody}>
            Gửi ảnh vào Zalo của Havi, nhận bản nháp, nhắn &quot;OK&quot; là đăng.
            Bản nháp và câu trả lời chờ duyệt cũng được nhắn tới chị mỗi sáng.
          </p>
        </div>
        <span className={styles.statusPill}>Đã bật</span>
      </section>

      <section className={styles.activityCard}>
        <p className={styles.sectionEyebrow}>Havi vừa làm gì cho chị</p>
        <div className={styles.activityList}>
          {dashboard.activities.map((item) => (
            <article
              key={`${item.time}-${item.tag}`}
              className={styles.activityItem}
            >
              <p className={styles.activityTime}>{item.time}</p>
              <p className={styles.activityText}>{item.text}</p>
              <span className={styles.activityTag}>{item.tag}</span>
            </article>
          ))}
        </div>
      </section>
    </>
  );
}
