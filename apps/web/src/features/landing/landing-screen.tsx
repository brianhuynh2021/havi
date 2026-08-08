import Link from "next/link";
import {
  heroChannels,
  heroStats,
  industries,
  principles,
  steps,
} from "./landing.content";
import styles from "./landing.module.css";

export function LandingScreen() {
  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.headerInner}>
          <Link href="/gioi-thieu" className={styles.brand}>
            <span className={styles.brandMark} aria-hidden="true">
              Ha
            </span>
            <span className={styles.brandText}>Havi</span>
          </Link>

          <nav className={styles.nav} aria-label="Điều hướng trang">
            <a href="#cach-hoat-dong">Cách hoạt động</a>
            <a href="#nganh">Cho ngành của bạn</a>
            <a href="#nguyen-tac">Nguyên tắc</a>
          </nav>

          <div className={styles.headerActions}>
            <Link href="/dang-nhap" className={styles.loginLink}>
              Đăng nhập
            </Link>
            <Link href="/dang-ky" className={styles.ctaButton}>
              Tạo tài khoản
            </Link>
          </div>
        </div>
      </header>

      <section className={styles.hero}>
        <div>
          <p className={styles.eyebrow}>Trợ lý marketing AI cho tiệm nhỏ</p>
          <h1 className={styles.heroTitle}>
            Từ ảnh chụp vội đến bài đăng sẵn sàng — bạn chỉ cần duyệt
          </h1>
          <p className={styles.heroBody}>
            Không cần viết prompt, không cần biết công nghệ. Ném vào vài tấm ảnh
            hay ba gạch đầu dòng — Havi viết bài riêng cho từng kênh, bạn đọc
            lướt rồi bấm duyệt.
          </p>

          <div className={styles.heroActions}>
            <Link href="/dang-ky" className={styles.ctaPrimary}>
              Tạo tài khoản miễn phí
            </Link>
            <a href="#cach-hoat-dong" className={styles.ctaSecondary}>
              Xem cách hoạt động
            </a>
          </div>

          <dl className={styles.heroStats}>
            {heroStats.map((stat) => (
              <div key={stat.l}>
                <dt className={styles.statValue}>{stat.v}</dt>
                <dd className={styles.statLabel}>{stat.l}</dd>
              </div>
            ))}
          </dl>
        </div>

        {/* Ảnh mô phỏng bản nháp chờ duyệt — dựng bằng markup thật thay vì ảnh
            chụp, để không phải bảo trì file ảnh khi UI đổi. */}
        <div className={styles.previewCard} aria-hidden="true">
          <div className={styles.previewBar}>
            <span className={styles.previewDot} />
            <span className={styles.previewDot} />
            <span className={styles.previewDot} />
            <span className={styles.previewBarText}>Havi · Bản nháp chờ duyệt</span>
          </div>
          <div className={styles.previewChannels}>
            {heroChannels.map((channel) => (
              <span key={channel.n} className={styles.previewChannel}>
                <span
                  className={styles.previewChannelDot}
                  style={{ background: channel.c }}
                />
                {channel.n}
              </span>
            ))}
          </div>
          <div className={styles.previewBody}>
            <div className={styles.previewPhoto}>Ảnh bạn chụp</div>
            <div>
              <p className={styles.previewText}>
                Tuần này bên mình có <strong>ưu đãi cho 30 khách đặt sớm</strong>{" "}
                — nhắn tin để giữ chỗ trước nha cả nhà.
              </p>
              <div className={styles.previewActions}>
                <span className={styles.previewApprove}>Duyệt</span>
                <span className={styles.previewEdit}>Sửa lại</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section id="cach-hoat-dong" className={styles.sectionAlt}>
        <div className={styles.sectionInner}>
          <div className={styles.sectionHead}>
            <h2 className={styles.sectionTitle}>
              Bạn làm một việc, Havi lo phần còn lại
            </h2>
            <p className={styles.sectionSub}>
              Từ tấm ảnh chụp vội đến bài sẵn sàng đăng — mọi thứ ở giữa Havi làm
              giùm bạn.
            </p>
          </div>

          <div className={styles.stepGrid}>
            {steps.map((step) => (
              <article key={step.n} className={styles.stepCard}>
                <span className={styles.stepNumber}>{step.n}</span>
                <h3 className={styles.stepTitle}>{step.title}</h3>
                <p className={styles.stepDesc}>{step.desc}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section id="nganh" className={styles.section}>
        <div className={styles.sectionInner}>
          <div className={styles.sectionHead}>
            <h2 className={styles.sectionTitle}>Havi hiểu ngành của bạn</h2>
            <p className={styles.sectionSub}>
              Mỗi ngành một cách nói chuyện riêng. Havi viết theo giọng tiệm bạn,
              và bạn sửa lại được bất cứ lúc nào.
            </p>
          </div>

          <div className={styles.industryGrid}>
            {industries.map((industry) => (
              <article key={industry.name} className={styles.industryCard}>
                <div className={styles.industryHead}>
                  <span
                    className={styles.industryBadge}
                    style={{ background: industry.color }}
                  >
                    {industry.badge}
                  </span>
                  <h3 className={styles.industryName}>{industry.name}</h3>
                </div>
                <div className={styles.industryRows}>
                  {industry.rows.map((row) => (
                    <div key={row.k} className={styles.industryRow}>
                      <span className={styles.industryKey}>{row.k}</span>
                      <span className={styles.industryText}>{row.t}</span>
                    </div>
                  ))}
                </div>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section id="nguyen-tac" className={styles.sectionAlt}>
        <div className={styles.sectionInner}>
          <div className={styles.sectionHead}>
            <h2 className={styles.sectionTitle}>Havi làm việc có nguyên tắc</h2>
            <p className={styles.sectionSub}>
              Tiệm của bạn là uy tín của bạn — Havi không đánh đổi nó để chạy
              nhanh hơn.
            </p>
          </div>

          <div className={styles.principleGrid}>
            {principles.map((item) => (
              <article key={item.title} className={styles.principleCard}>
                <h3 className={styles.principleTitle}>{item.title}</h3>
                <p className={styles.principleDesc}>{item.desc}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className={styles.ctaBand}>
        <div className={styles.ctaInner}>
          <h2 className={styles.ctaTitle}>Havi đang trong giai đoạn thử nghiệm</h2>
          <p className={styles.ctaBody}>
            Chúng tôi đang mời một nhóm nhỏ chủ tiệm dùng thử và góp ý. Tạo tài
            khoản để bắt đầu — chưa thu phí trong giai đoạn này.
          </p>
          <Link href="/dang-ky" className={styles.ctaBandButton}>
            Tạo tài khoản miễn phí
          </Link>
          {/* Giá 299K/599K CHƯA public: §12 chốt chỉ công bố sau khi đo được
              chi phí AI/hạ tầng trên khách Việt thật. Đừng thêm bảng giá vào
              đây trước lúc đó. */}
          <p className={styles.ctaNote}>
            Bảng giá sẽ công bố sau khi kết thúc giai đoạn thử nghiệm.
          </p>
        </div>
      </section>

      <footer className={styles.footer}>
        <div className={styles.footerInner}>
          <div>
            <div className={styles.brand}>
              <span className={styles.brandMark} aria-hidden="true">
                Ha
              </span>
              <span className={styles.footerBrandText}>Havi</span>
            </div>
            <p className={styles.footerBlurb}>
              Trợ lý marketing AI cho hộ kinh doanh và doanh nghiệp nhỏ tại Việt
              Nam.
            </p>
          </div>
          <nav className={styles.footerNav} aria-label="Liên kết chân trang">
            <a href="#cach-hoat-dong">Cách hoạt động</a>
            <a href="#nganh">Cho ngành của bạn</a>
            <Link href="/dang-nhap">Đăng nhập</Link>
            <Link href="/dieu-khoan">Điều khoản sử dụng</Link>
            <Link href="/bao-mat">Chính sách bảo mật</Link>
          </nav>
        </div>
        <p className={styles.footerNote}>
          © {new Date().getFullYear()} Havi. Đang trong giai đoạn thử nghiệm.
        </p>
      </footer>
    </div>
  );
}
