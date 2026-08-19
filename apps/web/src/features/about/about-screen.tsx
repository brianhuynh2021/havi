"use client";

import React from "react";
import Link from "next/link";
import { Logo } from "@/components/ui/logo";
import { LanguageSwitcher } from "@/components/ui/language-switcher";
import { useLanguage } from "@/lib/i18n/language-context";
import styles from "./about.module.css";

export function AboutScreen() {
  const { lang } = useLanguage();

  return (
    <div className={styles.page}>
      {/* Header */}
      <header className={styles.header}>
        <div className={styles.headerInner}>
          <Link href="/" className={styles.brand}>
            <Logo size={36} />
            <span className={styles.brandText}>Havi</span>
          </Link>

          <div className={styles.headerActions}>
            <Link href="/" className={styles.backLink}>
              {lang === "VN" ? "← Về trang chủ" : "← Home"}
            </Link>
            <LanguageSwitcher />
            <Link href="/signup" className={styles.ctaButton}>
              {lang === "VN" ? "Dùng thử 7 ngày" : "Get Started"}
            </Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className={styles.hero}>
        <div className={styles.heroGlow} />
        <div className={styles.eyebrow}>
          ✨ {lang === "VN" ? "CÂU CHUYỆN & SỨ MỆNH HAVI" : "ABOUT & MISSION"}
        </div>
        <h1 className={styles.heroTitle}>
          {lang === "VN" ? (
            <>
              Nâng Tầm Hàng Triệu Chủ Tiệm Việt Nam{" "}
              <span className={styles.highlightGradient}>Bằng Trí Tuệ Nhân Tạo</span>
            </>
          ) : (
            <>
              Empowering Millions of Small Businesses with{" "}
              <span className={styles.highlightGradient}>Human-Centered AI</span>
            </>
          )}
        </h1>
        <p className={styles.heroLead}>
          {lang === "VN"
            ? "Havi được sinh ra với sứ mệnh bình dân hoá công nghệ AI marketing đỉnh cao thế giới cho từng chủ tiệm Spa, Salon, Quán Cafe, Môi giới BĐS và hộ kinh doanh tại Việt Nam."
            : "Havi democratizes cutting-edge AI marketing technology for local salon, spa, F&B and retail owners across Vietnam and beyond."}
        </p>
      </section>

      {/* Content Container */}
      <main className={styles.container}>
        {/* Brand Origin Story */}
        <section className={styles.storyCard}>
          <h2 className={styles.storyCardHeading}>
            ❤️ Linh Hồn Thương Hiệu: Havi = Harry + Vietnam
          </h2>
          <p className={styles.storyParagraph}>
            Mỗi dòng mã và mỗi tính năng trong Havi không chỉ là công nghệ thuần túy, mà được xây dựng từ một ngọn lửa tình yêu gia đình và lòng tự hào dân tộc:
          </p>

          <div className={styles.brandMeaningGrid}>
            <div className={styles.meaningCard}>
              <div className={styles.meaningHeader}>
                <span className={styles.meaningLetter}>Ha</span>
                <span className={styles.meaningTitle}>Harry (Tình Yêu &amp; Tương Lai)</span>
              </div>
              <p className={styles.meaningDesc}>
                Được đặt theo tên cậu con trai bé bỏng của Nhà sáng lập. Harry là hiện thân của thế hệ tương lai, của ngọn lửa sưởi ấm gia đình và niềm tin bất diệt về một cuộc sống tốt đẹp hơn nhờ công nghệ tử tế.
              </p>
            </div>

            <div className={styles.meaningCard}>
              <div className={styles.meaningHeader}>
                <span className={styles.meaningLetter}>Vi</span>
                <span className={styles.meaningTitle}>Vietnam (Khát Vọng Dân Tộc)</span>
              </div>
              <p className={styles.meaningDesc}>
                Đại diện cho trí tuệ, sự kiên cường và khát vọng vươn lên của hàng triệu chủ tiệm, hộ kinh doanh và doanh nghiệp vừa và nhỏ khắp các tỉnh thành Việt Nam.
              </p>
            </div>
          </div>

          <p className={styles.storyParagraph}>
            Chúng tôi tin rằng, những người thức khuya dậy sớm mở tiệm kinh doanh chính là xương sống của nền kinh tế. Họ xứng đáng được trang bị những vũ khí công nghệ AI hiện đại nhất để tự tin cạnh tranh và phát triển vững mạnh.
          </p>
        </section>

        {/* Core Values */}
        <div className={styles.valuesGrid}>
          <div className={styles.valueCard}>
            <div className={styles.valueIcon}>🛡️</div>
            <h3 className={styles.valueTitle}>An Tâm &amp; Kiểm Soát 100%</h3>
            <p className={styles.valueDesc}>
              Nguyên tắc &ldquo;Bạn duyệt trước, luôn luôn&rdquo;. Havi không bao giờ tự ý đăng bài khi chưa có sự đồng ý của bạn, bảo vệ trọn vẹn uy tín thương hiệu của tiệm.
            </p>
          </div>

          <div className={styles.valueCard}>
            <div className={styles.valueIcon}>⚡</div>
            <h3 className={styles.valueTitle}>Chuẩn Kỹ Thuật Đỉnh Cao</h3>
            <p className={styles.valueDesc}>
              Xây dựng trên nền tảng Clean Architecture, mã hóa bảo mật chuẩn ngân hàng (Argon2id, AES-128) và tối ưu độ trễ siêu tốc dưới 5 giây.
            </p>
          </div>

          <div className={styles.valueCard}>
            <div className={styles.valueIcon}>💎</div>
            <h3 className={styles.valueTitle}>Sự Tử Tế &amp; Phụng Sự</h3>
            <p className={styles.valueDesc}>
              Minh bạch 100% về giá (chỉ từ 6.000 đ/ngày, rẻ hơn 1 ly trà sữa), không phụ phí ẩn, không spam công cụ lậu và luôn đồng hành cùng khách hàng.
            </p>
          </div>
        </div>

        {/* Quote */}
        <div className={styles.quoteBox}>
          <p className={styles.quoteText}>
            &ldquo;Công nghệ chỉ thực sự có giá trị khi nó phục vụ cuộc sống của những người bình dị nhất, giúp họ bớt đi nỗi nhọc nhằn và mỉm cười đón nhận thành quả mỗi ngày.&rdquo;
          </p>
          <div className={styles.quoteAuthor}>— Đội Ngũ Sáng Lập Havi Platform</div>
        </div>

        {/* Bottom CTA */}
        <section className={styles.ctaSection}>
          <h2 className={styles.ctaHeading}>Sẵn Sàng Trải Nghiệm Đội Ngũ AI Marketing?</h2>
          <p className={styles.ctaSubtitle}>
            Đăng ký chỉ mất 30 giây. Trải nghiệm trọn vẹn sức mạnh đa kênh của Havi trong 7 ngày hoàn toàn miễn phí.
          </p>
          <Link href="/signup" className={styles.ctaActionBtn}>
            Bắt đầu dùng thử 7 ngày miễn phí ➔
          </Link>
        </section>
      </main>

      {/* Footer */}
      <footer className={styles.footer}>
        <div className={styles.footerLinks}>
          <Link href="/">Trang chủ</Link>
          <Link href="/about">Về Havi</Link>
          <Link href="/terms">Điều khoản sử dụng</Link>
          <Link href="/privacy">Chính sách bảo mật</Link>
          <Link href="/data-deletion">Xóa dữ liệu</Link>
        </div>
        <div>© 2026 Havi Platform. All rights reserved.</div>
      </footer>
    </div>
  );
}
