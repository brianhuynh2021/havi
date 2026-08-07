import { reportsFixture } from "./reports.fixture";
import styles from "./reports.module.css";

const maxWeeklyPosts = Math.max(...reportsFixture.weeklyPosts.map((d) => d.count), 1);

export function ReportsScreen() {
  return (
    <>
      <header className={styles.header}>
        <h1 className={styles.title}>Báo cáo</h1>
        <p className={styles.subtitle}>Havi tổng hợp tuần này bằng vài câu dễ hiểu.</p>
      </header>

      <section className={styles.insightCard} aria-label="Nhận xét của Havi">
        <p className={styles.insightLabel}>Havi nhận xét</p>
        <p className={styles.insightText}>{reportsFixture.insight}</p>
      </section>

      <section className={styles.statsGrid} aria-label="Thống kê tuần">
        {reportsFixture.stats.map((item) => (
          <div key={item.label} className={styles.statCard}>
            <div className={styles.statValue}>{item.value}</div>
            <div className={styles.statLabel}>{item.label}</div>
          </div>
        ))}
      </section>

      <section className={styles.chartCard} aria-label="Bài đăng theo ngày trong tuần">
        <h2 className={styles.sectionTitle}>Bài đăng theo ngày</h2>
        <div className={styles.chartBars}>
          {reportsFixture.weeklyPosts.map((day) => (
            <div key={day.day} className={styles.chartColumn}>
              <div
                className={styles.chartBar}
                style={{ height: `${(day.count / maxWeeklyPosts) * 100}%` }}
                aria-hidden="true"
              />
              <span className={styles.chartValue}>{day.count}</span>
              <span className={styles.chartLabel}>{day.day}</span>
            </div>
          ))}
        </div>
      </section>

      <section className={styles.attributionCard} aria-label="Khách đến từ đâu">
        <h2 className={styles.sectionTitle}>Khách đến từ đâu</h2>
        <div className={styles.attributionList}>
          {reportsFixture.attribution.map((item) => (
            <div key={item.source} className={styles.attributionRow}>
              <span className={styles.attributionLabel}>{item.source}</span>
              <div className={styles.attributionTrack}>
                <div
                  className={styles.attributionFill}
                  style={{ width: `${item.percent}%` }}
                />
              </div>
              <span className={styles.attributionPercent}>{item.percent}%</span>
            </div>
          ))}
        </div>
      </section>
    </>
  );
}
