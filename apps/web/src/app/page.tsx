import styles from "./page.module.css";

type NavItem = {
  label: string;
  active: boolean;
  dot: string;
  count?: number;
};

const navItems: NavItem[] = [
  { label: "Tổng quan", active: true, dot: "#D4956F" },
  { label: "Tạo nội dung", active: false, dot: "rgba(255,255,255,0.25)" },
  {
    label: "Lịch đăng",
    active: false,
    dot: "rgba(255,255,255,0.25)",
    count: 3,
  },
  {
    label: "Khách tiềm năng",
    active: false,
    dot: "rgba(255,255,255,0.25)",
    count: 2,
  },
  { label: "Báo cáo", active: false, dot: "rgba(255,255,255,0.25)" },
];

const statCards = [
  { value: "3", label: "bài chờ đăng tuần này" },
  { value: "2", label: "khách mới đang hỏi giá" },
  { value: "12", label: "khách đến tiệm nhờ kênh online tuần này" },
] as const;

const connectedChannels = ["Facebook", "TikTok", "Zalo", "Maps"] as const;

const suggestions = [
  {
    tag: "Từ kho ảnh cũ",
    text: "Ảnh gội đầu thảo dược đăng tháng trước vẫn đang có lượt lưu. Havi đã biến thành bài gọi lại khách cũ cho chiều nay.",
    done: false,
    time: "",
  },
  {
    tag: "Theo trend",
    text: "Trời mưa dễ mệt mỏi. Havi đã soạn sẵn một bài chăm sóc da mùa ẩm và lên lịch đăng lúc 19:30.",
    done: true,
    time: "19:30",
  },
] as const;

const activityItems = [
  {
    time: "14:20",
    text: "Ca chăm da của chị Hằng vừa xong — đã nhắn Zalo nhắc chị chụp 1 tấm trước/sau (khách đã đồng ý)",
    tag: "Nguyên liệu",
  },
  {
    time: "08:30",
    text: "Chị Mai hỏi giá combo trên Fanpage — Havi đã soạn sẵn câu trả lời, chờ chị bấm gửi",
    tag: "Khách",
  },
  {
    time: "21:04",
    text: "Khách hỏi giờ mở cửa lúc 21:04 — Havi trả lời ngay bằng câu FAQ đã duyệt, khách chốt lịch CN 14:00",
    tag: "Trực đêm",
  },
  {
    time: "08:00",
    text: "Đã gửi voucher giảm 20% cho chị Ngọc Anh (chị duyệt hôm qua) — khách cũ 15 ngày",
    tag: "Chăm sóc",
  },
  {
    time: "Hôm qua",
    text: "Đã mời 3 khách vừa làm xong đánh giá 5★ trên Google Maps — 2 người đã viết",
    tag: "Đánh giá",
  },
  {
    time: "Hôm qua",
    text: "Bài ảnh Before/After đạt 480 lượt tiếp cận, 12 lượt chia sẻ",
    tag: "Bài đăng",
  },
  {
    time: "Hôm qua",
    text: "Đã cập nhật giờ mở cửa mới lên Google Maps",
    tag: "Maps",
  },
] as const;

export default function Home() {
  return (
    <div className={styles.page}>
      <aside className={styles.sidebar}>
        <div className={styles.brand}>
          <div className={styles.brandMark}>Ha</div>
          <div className={styles.brandText}>Havi</div>
        </div>

        <nav className={styles.nav} aria-label="Điều hướng chính">
          {navItems.map((item) => (
            <button
              key={item.label}
              type="button"
              className={`${styles.navItem} ${
                item.active ? styles.navItemActive : ""
              }`}
            >
              <span
                className={styles.navDot}
                style={{ backgroundColor: item.dot }}
                aria-hidden="true"
              />
              <span>{item.label}</span>
              {typeof item.count === "number" ? (
                <span className={styles.navBadge}>{item.count}</span>
              ) : null}
            </button>
          ))}
        </nav>

        <div className={styles.mobileNav} aria-label="Điều hướng mobile">
          {navItems.map((item) => (
            <div
              key={item.label}
              className={`${styles.mobileNavItem} ${
                item.active ? styles.mobileNavItemActive : ""
              }`}
            >
              {item.label}
            </div>
          ))}
        </div>

        <section className={styles.workspaceCard}>
          <p className={styles.workspaceLabel}>Không gian làm việc</p>
          <p className={styles.workspaceName}>Spa An Nhiên</p>
          <div className={styles.workspaceChips}>
            {connectedChannels.map((channel) => (
              <span key={channel} className={styles.workspaceChip}>
                {channel}
              </span>
            ))}
          </div>
        </section>
      </aside>

      <main className={styles.main}>
        <header className={styles.header}>
          <h1 className={styles.title}>Chào buổi sáng, chị Hương</h1>
          <p className={styles.subtitle}>
            Thứ Bảy, 1 tháng 8 — hôm nay Havi có vài việc đã lo sẵn cho chị.
          </p>
        </header>

        <section className={styles.statsGrid} aria-label="Thống kê nhanh">
          {statCards.map((item) => (
            <button key={item.label} type="button" className={styles.cardButton}>
              <div className={styles.statValue}>{item.value}</div>
              <div className={styles.statLabel}>{item.label}</div>
            </button>
          ))}
        </section>

        <section className={styles.uploadCard}>
          <h2 className={styles.uploadTitle}>Có gì mới ở tiệm hôm nay?</h2>
          <p className={styles.uploadBody}>
            Thả vài tấm ảnh, ghi âm 1 phút, hoặc gõ vài dòng. Havi sẽ lo phần
            còn lại — viết bài, chỉnh ảnh và lên lịch đăng.
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
            {suggestions.map((item) => (
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
              Gửi ảnh vào Zalo của Havi, nhận bản nháp, nhắn &quot;OK&quot; là
              đăng. Bản nháp và câu trả lời chờ duyệt cũng được nhắn tới chị mỗi
              sáng.
            </p>
          </div>
          <span className={styles.statusPill}>Đã bật</span>
        </section>

        <section className={styles.activityCard}>
          <p className={styles.sectionEyebrow}>Havi vừa làm gì cho chị</p>
          <div className={styles.activityList}>
            {activityItems.map((item) => (
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
      </main>
    </div>
  );
}
