"use client";

import React from "react";
import Link from "next/link";
import { Logo } from "@/components/ui/logo";
import { LanguageSwitcher } from "@/components/ui/language-switcher";
import { useLanguage } from "@/lib/i18n/language-context";
import styles from "./about.module.css";

export function AboutScreen() {
  const {
    t
  } = useLanguage();

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
              {t("← Về trang chủ")}
            </Link>
            <LanguageSwitcher />
            <Link href="/signup" className={styles.ctaButton}>
              {t("Dùng thử 7 ngày")}
            </Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className={styles.hero}>
        <div className={styles.heroGlow} />
        <div className={styles.eyebrow}>
          ✨ {t("CÂU CHUYỆN & SỨ MỆNH HAVI")}
        </div>
        <h1 className={styles.heroTitle}>
          {lang === "VN" ? (
            <>{t("Vận Hành Social Media Đa Kênh")}{" "}{" "}
              <span className={styles.highlightGradient}>{t("Trong Một Nơi")}</span>
            </>
          ) : (
            <>
              Multi-channel Social Operations{" "}
              <span className={styles.highlightGradient}>In One Place</span>
            </>
          )}
        </h1>
        <p className={styles.heroLead}>
          {t("Havi giúp doanh nghiệp, freelancer và đội ngũ social quản lý kênh, nội dung, lịch đăng, hội thoại và phân quyền mà không phải nhảy qua từng nền tảng.")}
        </p>
      </section>

      {/* Content Container */}
      <main className={styles.container}>
        {/* Brand Origin Story */}
        <section className={styles.storyCard}>
          <h2 className={styles.storyCardHeading}>{t("❤️ Linh Hồn Thương Hiệu: Havi = Harry + Vietnam")}</h2>
          <p className={styles.storyParagraph}>{t(
            "Mỗi dòng mã và mỗi tính năng trong Havi không chỉ là công nghệ thuần túy, mà được xây dựng từ một ngọn lửa tình yêu gia đình và lòng tự hào dân tộc:"
          )}</p>

          <div className={styles.brandMeaningGrid}>
            <div className={styles.meaningCard}>
              <div className={styles.meaningHeader}>
                <span className={styles.meaningLetter}>Ha</span>
                <span className={styles.meaningTitle}>{t("Harry (Tình Yêu & Tương Lai)")}</span>
              </div>
              <p className={styles.meaningDesc}>{t(
                "Được đặt theo tên cậu con trai bé bỏng của Nhà sáng lập. Harry là hiện thân của thế hệ tương lai, của ngọn lửa sưởi ấm gia đình và niềm tin bất diệt về một cuộc sống tốt đẹp hơn nhờ công nghệ tử tế."
              )}</p>
            </div>

            <div className={styles.meaningCard}>
              <div className={styles.meaningHeader}>
                <span className={styles.meaningLetter}>Vi</span>
                <span className={styles.meaningTitle}>{t("Vietnam (Khát Vọng Dân Tộc)")}</span>
              </div>
              <p className={styles.meaningDesc}>{t(
                "Đại diện cho trí tuệ, sự kiên cường và khát vọng vươn lên của hàng triệu chủ tiệm, hộ kinh doanh và doanh nghiệp vừa và nhỏ khắp các tỉnh thành Việt Nam."
              )}</p>
            </div>
          </div>

          <p className={styles.storyParagraph}>{t(
            "Chúng tôi tin rằng doanh nghiệp Việt cần một công cụ vận hành rõ ràng, nhẹ đầu và trung thực: biết kênh nào đang hoạt động, bài nào chờ duyệt, lịch nào sắp chạy và hội thoại nào chưa xử lý."
          )}</p>
        </section>

        {/* Core Values */}
        <div className={styles.valuesGrid}>
          <div className={styles.valueCard}>
            <div className={styles.valueIcon}>🛡️</div>
            <h3 className={styles.valueTitle}>{t("An Tâm & Có Quyền Kiểm Soát")}</h3>
            <p className={styles.valueDesc}>{t(
              "Nguyên tắc “Bạn duyệt trước, luôn luôn”. Havi không bao giờ tự ý đăng bài khi chưa có sự đồng ý của bạn, bảo vệ trọn vẹn uy tín thương hiệu của tiệm."
            )}</p>
          </div>

          <div className={styles.valueCard}>
            <div className={styles.valueIcon}>⚡</div>
            <h3 className={styles.valueTitle}>{t("Chuẩn Kỹ Thuật Đỉnh Cao")}</h3>
            <p className={styles.valueDesc}>{t(
              "Xây dựng theo Clean Architecture, mật khẩu Argon2id, token được mã hoá và các luồng quan trọng có kiểm thử tự động bảo vệ."
            )}</p>
          </div>

          <div className={styles.valueCard}>
            <div className={styles.valueIcon}>💎</div>
            <h3 className={styles.valueTitle}>{t("Sự Tử Tế & Phụng Sự")}</h3>
            <p className={styles.valueDesc}>{t(
              "Công bố đúng giá theo tháng, dùng API chính thức và ghi rõ tính năng nào đang ở Beta hoặc vẫn thuộc roadmap."
            )}</p>
          </div>
        </div>

        {/* Quote */}
        <div className={styles.quoteBox}>
          <p className={styles.quoteText}>{t(
            "“Công nghệ chỉ thực sự có giá trị khi nó phục vụ cuộc sống của những người bình dị nhất, giúp họ bớt đi nỗi nhọc nhằn và mỉm cười đón nhận thành quả mỗi ngày.”"
          )}</p>
          <div className={styles.quoteAuthor}>{t("— Đội Ngũ Sáng Lập Havi Platform")}</div>
        </div>

        {/* Bottom CTA */}
        <section className={styles.ctaSection}>
          <h2 className={styles.ctaHeading}>{t("Sẵn Sàng Quản Trị Social Media Nhẹ Đầu Hơn?")}</h2>
          <p className={styles.ctaSubtitle}>{t(
            "Kết nối kênh, tập trung nội dung và theo dõi công việc vận hành trong một không gian chung."
          )}</p>
          <Link href="/signup" className={styles.ctaActionBtn}>{t("Bắt đầu dùng thử 7 ngày miễn phí ➔")}</Link>
        </section>
      </main>

      {/* Footer */}
      <footer className={styles.footer}>
        <div className={styles.footerLinks}>
          <Link href="/">{t("Trang chủ")}</Link>
          <Link href="/about">{t("Về Havi")}</Link>
          <Link href="/terms">{t("Điều khoản sử dụng")}</Link>
          <Link href="/privacy">{t("Chính sách bảo mật")}</Link>
          <Link href="/data-deletion">{t("Xóa dữ liệu")}</Link>
        </div>
        <div>© 2026 Havi Platform. All rights reserved.</div>
      </footer>
    </div>
  );
}
