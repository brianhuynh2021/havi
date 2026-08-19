"use client";

import { useState } from "react";
import Link from "next/link";
import { Logo } from "@/components/ui/logo";
import { LanguageSwitcher } from "@/components/ui/language-switcher";
import {
  faqs,
  heroStats,
  principles,
  testimonials,
} from "./landing.content";
import { HeroCinematicShowcase } from "./hero-cinematic-showcase";
import { VideoDemoModal } from "./video-demo-modal";
import styles from "./landing.module.css";
import { useLanguage } from "@/lib/i18n/language-context";

export function LandingScreen() {
  const [billingCycle, setBillingCycle] = useState<"monthly" | "yearly">("monthly");
  const [isB2BModalOpen, setIsB2BModalOpen] = useState(false);
  const [isVideoModalOpen, setIsVideoModalOpen] = useState(false);
  const [b2bSubmitted, setB2bSubmitted] = useState(false);
  const [openFaqIdx, setOpenFaqIdx] = useState<number | null>(0);
  const [b2bForm, setB2bForm] = useState({
    company: "",
    name: "",
    phone: "",
    branches: "5-10 chi nhánh",
    notes: "",
  });
  const { lang } = useLanguage();

  const handleB2BSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setB2bSubmitted(true);
  };

  return (
    <div className={styles.page}>
      {/* Header */}
      <header className={styles.header}>
        <div className={styles.headerInner}>
          <Link href="/" className={styles.brand}>
            <Logo size={36} />
            <span className={styles.brandText}>Havi</span>
          </Link>

          <nav className={styles.nav}>
            <a href="#demo-studio" className={styles.navLink}>
              {lang === "VN" ? "Dùng thử Demo" : "Interactive Demo"}
            </a>
            <a href="#bang-gia" className={styles.navLink}>
              {lang === "VN" ? "Bảng giá" : "Pricing"}
            </a>
            <a href="#khach-hang" className={styles.navLink}>
              {lang === "VN" ? "Đánh giá" : "Reviews"}
            </a>
            <a href="#faq" className={styles.navLink}>
              {lang === "VN" ? "Hỏi đáp" : "FAQ"}
            </a>
          </nav>

          <div className={styles.headerActions}>
            <LanguageSwitcher />
            <Link href="/login" className={styles.loginBtn}>
              {lang === "VN" ? "Đăng nhập" : "Login"}
            </Link>
            <Link href="/signup" className={styles.ctaButton}>
              {lang === "VN" ? "Dùng thử 7 ngày" : "Get Started"}
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className={styles.hero}>
        <div>
          <div className={styles.eyebrow}>
            <span style={{ fontSize: "14px" }}>✨</span> NHÂN VIÊN AI MARKETING ĐA KÊNH • TRỰC TIỆM &amp; CHỐT ĐƠN 24/7
          </div>
          <h1 className={styles.heroTitle}>
            {lang === "VN" ? (
              <>
                <span style={{ display: "block" }}>Chỉ 1 chạm</span>
                <span className={styles.purpleGradient} style={{ display: "inline-block" }}>
                  tiếp cận khách hàng đa nền tảng
                </span>
              </>
            ) : (
              <>
                <span style={{ display: "block" }}>With 1 Touch</span>
                <span className={styles.purpleGradient} style={{ display: "inline-block" }}>
                  Reach Customers Across Platforms
                </span>
              </>
            )}
          </h1>
          <p className={styles.heroBody}>
            {lang === "VN"
              ? "Không còn mất hàng giờ nghĩ ý tưởng. Chỉ cần gửi ảnh, Havi tự động sinh bài, dựng video bắt trend và trực inbox kéo khách."
              : "No more spending hours brainstorming. Just send a photo, Havi automatically generates posts, creates trending videos, and engages inbox leads 24/7."}
          </p>

          <div className={styles.heroActions}>
            <Link href="/signup" className={styles.heroPrimaryBtn}>
              Bắt đầu dùng thử 7 ngày miễn phí
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path d="M5 12h14M12 5l7 7-7 7" />
              </svg>
            </Link>
            <button
              type="button"
              className={styles.heroSecondaryBtn}
              onClick={() => setIsVideoModalOpen(true)}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#00d2ff" strokeWidth="2.5">
                <polygon points="5 3 19 12 5 21 5 3" />
              </svg>
              {lang === "VN" ? "Xem Video Thực Chiến 60s" : "Watch 60s Demo"}
            </button>
          </div>

          <div className={styles.heroTrustLine}>
            <span>⭐️ Được tin dùng bởi các chủ tiệm Spa, Salon, F&amp;B, BĐS &amp; Dạy Nghề</span>
            <span>•</span>
            <span style={{ color: "#34d399", fontWeight: 700 }}>✓ Kích hoạt 7 ngày không cần thẻ tín dụng</span>
          </div>

          {/* Hero 3D Cinematic Showcase (Unified Demo Hub) */}
          <div id="demo-studio" style={{ scrollMarginTop: "100px" }}>
            <HeroCinematicShowcase
              onOpenVideoModal={() => setIsVideoModalOpen(true)}
              lang={lang}
            />
          </div>

          {/* Stats Section */}
          <div className={styles.heroStats}>
            {heroStats.map((st, idx) => (
              <div key={st.v} style={{ display: "flex", alignItems: "center", gap: "36px" }}>
                {idx > 0 && <div className={styles.statDivider} />}
                <div className={styles.statItem}>
                  <div className={styles.statVal}>
                    <span style={{ fontSize: "20px" }}>{st.icon}</span>
                    {st.v}
                  </div>
                  <div className={styles.statLbl}>{st.l}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Bảng Giá Thương Mại & So Sánh ROI (Chiến thuật FAANG) */}
      <section id="bang-gia" className={styles.hero} style={{ paddingTop: "40px" }}>
        <div className={styles.sectionHeader}>
          <div className={styles.sectionTag} style={{ color: "#34d399" }}>
            {lang === "VN" ? "BẢNG GIÁ DỊCH VỤ" : "TRANSPARENT PRICING"}
          </div>
          <h2 className={styles.sectionTitle}>
            {lang === "VN" ? "Bảng Giá Minh Bạch & Tiết Kiệm" : "Flexible & Transparent Pricing"}
          </h2>
          <p className={styles.sectionSubtitle}>
            {lang === "VN"
              ? "Dùng thử 7 ngày không cần thẻ · Kích hoạt VietQR trong 3 giây · Hủy hoặc đổi gói bất kỳ lúc nào."
              : "7-day free trial without credit card · Instant 3-second VietQR activation · Cancel or switch plans anytime."}
          </p>
        </div>

        {/* Annual Discount Toggle */}
        <div style={{ textAlign: "center" }}>
          <div className={styles.pricingToggleWrapper}>
            <button
              type="button"
              className={`${styles.pricingToggleBtn} ${billingCycle === "monthly" ? styles.pricingToggleBtnActive : ""}`}
              onClick={() => setBillingCycle("monthly")}
            >
              Thanh toán theo Tháng
            </button>
            <button
              type="button"
              className={`${styles.pricingToggleBtn} ${billingCycle === "yearly" ? styles.pricingToggleBtnActive : ""}`}
              onClick={() => setBillingCycle("yearly")}
            >
              Thanh toán theo Năm
              <span style={{ fontSize: "11px", fontWeight: 800, background: "#10b981", color: "#fff", padding: "2px 7px", borderRadius: "99px" }}>
                🎁 TẶNG 3 THÁNG
              </span>
            </button>
          </div>
        </div>

        <div className={styles.pricingGrid}>
          {/* Free Trial */}
          <div className={styles.pricingCard}>
            <div>
              <span style={{ fontSize: "11.5px", fontWeight: 800, color: "#94a3b8", background: "rgba(255,255,255,0.06)", padding: "3px 9px", borderRadius: "99px" }}>
                TRẢI NGHIỆM MIỄN PHÍ
              </span>
              <h3 style={{ fontSize: "20px", fontWeight: 800, color: "#fff", margin: "12px 0 4px" }}>Gói Dùng Thử</h3>
              
              <div className={styles.pricingPriceBox}>
                <div className={styles.pricingPriceRow}>
                  <span className={styles.pricingAmount} style={{ color: "#fff" }}>0 đ</span>
                  <span className={styles.pricingPeriod}>/ 7 ngày</span>
                </div>
                <div className={`${styles.pricingDailyBadge} ${styles.pricingDailyBadgeGreen}`}>
                  ✨ Trải nghiệm trọn vẹn · Không cần thẻ
                </div>
              </div>

              <p style={{ fontSize: "13px", color: "#94a3b8", lineHeight: 1.45, marginBottom: "16px" }}>
                Dùng thử đầy đủ tính năng tạo bài &amp; trực inbox 24/7 để thấy rõ hiệu quả trước khi trả phí.
              </p>
              <ul className={styles.pricingFeaturesList}>
                <li>
                  <span className={styles.pricingCheck}>✓</span>
                  <span className={styles.pricingFeatureText}>Dùng thử 7 ngày không rủi ro</span>
                </li>
                <li>
                  <span className={styles.pricingCheck}>✓</span>
                  <span className={styles.pricingFeatureText}>Kết nối 1 Fanpage Facebook an toàn</span>
                </li>
                <li>
                  <span className={styles.pricingCheck}>✓</span>
                  <span className={styles.pricingFeatureText}>Trực Inbox &amp; Trả lời Bảng giá 24/7</span>
                </li>
                <li>
                  <span className={styles.pricingCheck}>✓</span>
                  <span className={styles.pricingFeatureText}>Lên lịch đăng bài tự động giờ vàng</span>
                </li>
              </ul>
            </div>
            <Link href="/signup" className={styles.btnSecondary} style={{ width: "100%", justifyContent: "center" }}>
              Dùng thử miễn phí
            </Link>
          </div>

          {/* Gói Khởi Nghiệp (189.000 đ/tháng hoặc 1.890.000 đ/năm) */}
          <div className={styles.pricingCard}>
            <div>
              <span style={{ fontSize: "11.5px", fontWeight: 800, color: "#38bdf8", background: "rgba(56,189,248,0.15)", padding: "3px 9px", borderRadius: "99px" }}>
                TIẾT KIỆM NHẤT
              </span>
              <h3 style={{ fontSize: "20px", fontWeight: 800, color: "#fff", margin: "12px 0 4px" }}>Gói Khởi Nghiệp</h3>
              
              <div className={styles.pricingPriceBox}>
                <div className={styles.pricingPriceRow}>
                  <span className={styles.pricingAmount} style={{ color: "#38bdf8" }}>
                    {billingCycle === "yearly" ? "1.890.000 đ" : "189.000 đ"}
                  </span>
                  <span className={styles.pricingPeriod}>
                    {billingCycle === "yearly" ? "/ năm" : "/ tháng"}
                  </span>
                </div>
                <div className={styles.pricingDailyBadge}>
                  {billingCycle === "yearly" ? "⚡ Tiết kiệm: ~157k/tháng · Tặng 3 tháng" : "⚡ Chỉ ~6.000 đ/ngày"}
                </div>
              </div>

              <p style={{ fontSize: "13px", color: "#94a3b8", lineHeight: 1.45, marginBottom: "16px" }}>
                Giải pháp tối ưu chi phí cho chủ tiệm đơn lẻ duy trì tương tác và bắt lead tự động.
              </p>
              <ul className={styles.pricingFeaturesList}>
                <li>
                  <span className={styles.pricingCheck}>✓</span>
                  <span className={styles.pricingFeatureText}><strong>1 Fanpage Facebook</strong> chính thức</span>
                </li>
                <li>
                  <span className={styles.pricingCheck}>✓</span>
                  <span className={styles.pricingFeatureText}><strong>30 bài viết chuẩn ngành/tháng</strong> từ ảnh tiệm</span>
                </li>
                <li>
                  <span className={styles.pricingCheck}>✓</span>
                  <span className={styles.pricingFeatureText}><strong>Trực Inbox 24/7</strong> &amp; Bắt SĐT khách tự động</span>
                </li>
                <li>
                  <span className={styles.pricingCheck}>✓</span>
                  <span className={styles.pricingFeatureText}>Báo cáo tương tác &amp; Hiệu quả bài viết</span>
                </li>
                <li>
                  <span className={styles.pricingCheck}>✓</span>
                  <span className={styles.pricingFeatureText}>Hỗ trợ kỹ thuật chu đáo 24/7</span>
                </li>
              </ul>
            </div>
            <Link href="/signup" className={styles.btnSecondary} style={{ width: "100%", justifyContent: "center" }}>
              Nâng cấp Khởi Nghiệp
            </Link>
          </div>

          {/* Gói Chuyên Nghiệp (369.000 đ/tháng hoặc 3.690.000 đ/năm - Best Seller) */}
          <div className={`${styles.pricingCard} ${styles.pricingCardFeatured} ${styles.pricingCardPopular}`}>
            <div className={styles.pricingBadgeTop}>
              BÁN CHẠY NHẤT ★
            </div>
            <div>
              <span style={{ fontSize: "11.5px", fontWeight: 800, color: "#c084fc", background: "rgba(139,92,246,0.18)", padding: "3px 9px", borderRadius: "99px" }}>
                TĂNG TRƯỞNG ĐA KÊNH
              </span>
              <h3 style={{ fontSize: "20px", fontWeight: 800, color: "#fff", margin: "12px 0 4px" }}>Gói Chuyên Nghiệp</h3>
              
              <div className={styles.pricingPriceBox}>
                <div className={styles.pricingPriceRow}>
                  <span className={styles.pricingAmount} style={{ color: "#c084fc" }}>
                    {billingCycle === "yearly" ? "3.690.000 đ" : "369.000 đ"}
                  </span>
                  <span className={styles.pricingPeriod}>
                    {billingCycle === "yearly" ? "/ năm" : "/ tháng"}
                  </span>
                </div>
                <div className={`${styles.pricingDailyBadge} ${styles.pricingDailyBadgePurple}`}>
                  {billingCycle === "yearly" ? "🔥 Tiết kiệm: ~307k/tháng · Tặng 3 tháng" : "🔥 Chỉ ~12.000 đ/ngày"}
                </div>
              </div>

              <p style={{ fontSize: "13px", color: "#94a3b8", lineHeight: 1.45, marginBottom: "16px" }}>
                Bộ công cụ toàn diện tăng trưởng doanh thu cho Spa, Môi giới BĐS, F&amp;B, Salon và Dạy nghề.
              </p>
              <ul className={styles.pricingFeaturesList}>
                <li>
                  <span className={styles.pricingCheck}>✓</span>
                  <span className={styles.pricingFeatureText}><strong>Đa kênh:</strong> Facebook + Google Maps + TikTok Video</span>
                </li>
                <li>
                  <span className={styles.pricingCheck}>✓</span>
                  <span className={styles.pricingFeatureText}><strong>90 bài viết &amp; Kịch bản Video 9:16</strong> (Hook 3s)</span>
                </li>
                <li>
                  <span className={styles.pricingCheck}>✓</span>
                  <span className={styles.pricingFeatureText}><strong>Tự động bắt SĐT &amp; Tên khách hàng</strong> về app</span>
                </li>
                <li>
                  <span className={styles.pricingCheck}>✓</span>
                  <span className={styles.pricingFeatureText}><strong>Chăm sóc khách cũ (CRM Nudge):</strong> Kéo khách quay lại</span>
                </li>
                <li>
                  <span className={styles.pricingCheck}>✓</span>
                  <span className={styles.pricingFeatureText}>Báo cáo doanh thu &amp; Đối soát đơn hàng</span>
                </li>
              </ul>
            </div>
            <Link href="/signup" className={styles.heroPrimaryBtn} style={{ width: "100%", justifyContent: "center" }}>
              Nâng cấp Chuyên Nghiệp
            </Link>
          </div>

          {/* Gói Chuỗi Doanh Nghiệp (799.000 đ/tháng hoặc 7.990.000 đ/năm - Multi-Store VIP) */}
          <div className={`${styles.pricingCard} ${styles.pricingCardEnterprise}`}>
            <div className={`${styles.pricingBadgeTop} ${styles.pricingBadgeGold}`}>
              QUY MÔ CHUỖI 👑
            </div>
            <div>
              <span style={{ fontSize: "11.5px", fontWeight: 800, color: "#fbbf24", background: "rgba(245,158,11,0.18)", padding: "3px 9px", borderRadius: "99px" }}>
                DOANH NGHIỆP &amp; CHUỖI
              </span>
              <h3 style={{ fontSize: "20px", fontWeight: 800, color: "#fff", margin: "12px 0 4px" }}>Chuỗi Doanh Nghiệp</h3>
              
              <div className={styles.pricingPriceBox}>
                <div className={styles.pricingPriceRow}>
                  <span className={styles.pricingAmount} style={{ color: "#fbbf24" }}>
                    {billingCycle === "yearly" ? "7.990.000 đ" : "799.000 đ"}
                  </span>
                  <span className={styles.pricingPeriod}>
                    {billingCycle === "yearly" ? "/ năm" : "/ tháng"}
                  </span>
                </div>
                <div className={`${styles.pricingDailyBadge} ${styles.pricingDailyBadgeAmber}`}>
                  {billingCycle === "yearly" ? "💎 Tiết kiệm: ~665k/tháng · Tặng 3 tháng" : "💎 Chỉ ~26.000 đ/ngày"}
                </div>
              </div>

              <p style={{ fontSize: "13px", color: "#94a3b8", lineHeight: 1.45, marginBottom: "16px" }}>
                Quản lý tập trung 2–5 chi nhánh / Fanpage cho hệ thống chuỗi và Agency truyền thông.
              </p>
              <ul className={styles.pricingFeaturesList}>
                <li>
                  <span className={styles.pricingCheck}>✓</span>
                  <span className={styles.pricingFeatureText}><strong>Quản lý tối đa 5 Chi nhánh / Fanpage</strong></span>
                </li>
                <li>
                  <span className={styles.pricingCheck}>✓</span>
                  <span className={styles.pricingFeatureText}><strong>Không giới hạn</strong> bài viết AI &amp; kịch bản Video</span>
                </li>
                <li>
                  <span className={styles.pricingCheck}>✓</span>
                  <span className={styles.pricingFeatureText}><strong>Phân quyền tài khoản:</strong> Chủ tiệm, Quản lý, Nhân viên tư vấn</span>
                </li>
                <li>
                  <span className={styles.pricingCheck}>✓</span>
                  <span className={styles.pricingFeatureText}><strong>Đối soát POS KiotViet / Sapo</strong> tự động</span>
                </li>
                <li>
                  <span className={styles.pricingCheck}>✓</span>
                  <span className={styles.pricingFeatureText}><strong>Kỹ sư Havi hỗ trợ VIP 1-1</strong> riêng biệt</span>
                </li>
              </ul>
            </div>
            <Link href="/signup" className={styles.btnSecondary} style={{ width: "100%", justifyContent: "center" }}>
              Nâng cấp Gói Chuỗi
            </Link>
          </div>
        </div>

        {/* B2B Custom Setup Banner */}
        <div style={{
          maxWidth: "1200px",
          margin: "40px auto 0",
          background: "linear-gradient(135deg, rgba(30, 27, 75, 0.6) 0%, rgba(15, 23, 42, 0.8) 100%)",
          border: "1px solid rgba(99, 102, 241, 0.3)",
          borderRadius: "20px",
          padding: "24px 32px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "24px",
          flexWrap: "wrap",
        }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <span style={{ fontSize: "20px" }}>🏢</span>
              <span style={{ fontSize: "16px", fontWeight: 800, color: "#fff" }}>
                Cần Quản Lý &gt; 5 Cơ Sở Hoặc Hợp Đồng &amp; Xuất Hóa Đơn VAT Doanh Nghiệp?
              </span>
              <span style={{ fontSize: "11px", fontWeight: 800, background: "#3b82f6", color: "#fff", padding: "2px 8px", borderRadius: "6px" }}>
                B2B CUSTOM
              </span>
            </div>
            <p style={{ fontSize: "14px", color: "#cbd5e1", margin: "6px 0 0 0" }}>
              Havi cung cấp giải pháp Private Setup, đào tạo AI chuyên sâu và tích hợp API riêng cho các chuỗi lớn và Agency.
            </p>
          </div>
          <button
            type="button"
            onClick={() => {
              setIsB2BModalOpen(true);
              setB2bSubmitted(false);
            }}
            className={styles.b2bCtaBtn}
          >
            Liên hệ Chuyên viên B2B
          </button>
        </div>
      </section>

      {/* Testimonials Section */}
      <section id="khach-hang" className={styles.testimonialSection}>
        <div className={styles.sectionHeader}>
          <div className={styles.sectionTag} style={{ color: "#38bdf8" }}>THỰC CHIẾN &amp; HIỆU QUẢ</div>
          <h2 className={styles.sectionTitle}>Chủ Tiệm Nói Gì Về Havi?</h2>
          <p className={styles.sectionSubtitle}>
            Hàng trăm chủ tiệm Spa, Quán cafe, Môi giới BĐS &amp; Cơ sở đào tạo đã tiết kiệm hàng triệu đồng mỗi tháng nhờ Havi.
          </p>
        </div>

        <div className={styles.testimonialGrid}>
          {testimonials.map((t) => (
            <div key={t.name} className={styles.testimonialCard}>
              <div>
                <div className={styles.testimonialHeader}>
                  <div style={{ color: "#fbbf24", fontSize: "14px" }}>{"★".repeat(t.rating)}</div>
                  <span className={styles.testimonialBadge}>{t.badge}</span>
                </div>
                <div className={styles.testimonialHighlight}>&ldquo;{t.highlight}&rdquo;</div>
                <p className={styles.testimonialQuote}>&ldquo;{t.quote}&rdquo;</p>
              </div>
              <div className={styles.testimonialAuthor}>
                <div className={styles.testimonialAvatar}>{t.avatar}</div>
                <div>
                  <h4 className={styles.authorName}>{t.name}</h4>
                  <p className={styles.authorRole}>{t.role}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Nguyên Tắc Vận Hành */}
      <section id="nguyen-tac" className={styles.hero} style={{ paddingTop: "20px" }}>
        <div className={styles.sectionHeader}>
          <div className={styles.sectionTag} style={{ color: "#10b981" }}>CAM KẾT AN TOÀN</div>
          <h2 className={styles.sectionTitle}>Nguyên Tắc Xây Dựng Thương Hiệu Của Havi</h2>
          <p className={styles.sectionSubtitle}>Bảo vệ trọn vẹn uy tín của tiệm: Không bao giờ phát hành nội dung khi chưa được bạn duyệt.</p>
        </div>

        <div className={styles.bentoGrid} style={{ gridTemplateColumns: "repeat(3, 1fr)", marginBottom: "60px" }}>
          {principles.map((pr) => (
            <div key={pr.title} className={styles.glassCard} style={{ padding: "32px", textAlign: "left" }}>
              <div style={{ width: "40px", height: "40px", borderRadius: "10px", background: "rgba(16,185,129,0.15)", color: "#10b981", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 800, fontSize: "18px", marginBottom: "16px" }}>
                ✓
              </div>
              <h3 style={{ fontSize: "20px", fontWeight: 800, color: "#fff", margin: "0 0 10px" }}>{pr.title}</h3>
              <p style={{ fontSize: "14.5px", color: "#b8c0d0", lineHeight: 1.6, margin: 0 }}>{pr.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* FAQ Accordion Section */}
      <section id="faq" className={styles.faqSection}>
        <div className={styles.sectionHeader}>
          <div className={styles.sectionTag} style={{ color: "#c084fc" }}>GIẢI ĐÁP THẮC MẮC</div>
          <h2 className={styles.sectionTitle}>Câu Hỏi Thường Gặp</h2>
          <p className={styles.sectionSubtitle}>Mọi điều bạn cần biết trước khi bắt đầu dùng thử Havi 7 ngày miễn phí.</p>
        </div>

        <div className={styles.faqList}>
          {faqs.map((faq, idx) => {
            const isOpen = openFaqIdx === idx;
            return (
              <div key={faq.question} className={`${styles.faqItem} ${isOpen ? styles.faqItemOpen : ""}`}>
                <button
                  type="button"
                  className={styles.faqQuestion}
                  onClick={() => setOpenFaqIdx(isOpen ? null : idx)}
                  aria-expanded={isOpen}
                >
                  <span>{faq.question}</span>
                  <span className={styles.faqToggleIcon}>{isOpen ? "−" : "+"}</span>
                </button>
                {isOpen && <div className={styles.faqAnswer}>{faq.answer}</div>}
              </div>
            );
          })}
        </div>
      </section>

      {/* Rich 4-Column Antigravity Footer */}
      <footer className={styles.footer}>
        <div className={styles.footerInner}>
          <div className={styles.footerGrid}>
            {/* Brand Column */}
            <div className={styles.footerBrandCol}>
              <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                <Logo size={36} />
                <span style={{ fontWeight: 800, fontSize: "22px", color: "#fff" }}>Havi</span>
              </div>
              <p className={styles.footerDesc}>
                Nhân viên AI Marketing Đa Kênh tự động cho mọi chủ tiệm &amp; doanh nghiệp. Tự động hóa bài viết Facebook, kịch bản TikTok Shorts, Google Maps SEO và trực Inbox 24/7.
              </p>
              <div className={styles.trustBadges}>
                <span className={styles.trustBadge}>🛡️ Bảo Vệ Kênh 100%</span>
                <span className={styles.trustBadge}>🇻🇳 Giọng Văn Thuần Việt</span>
                <span className={styles.trustBadge}>⚡ 100% Duyệt Trước</span>
              </div>
            </div>

            {/* Product Links */}
            <div>
              <div className={styles.footerColTitle}>SẢN PHẨM</div>
              <ul className={styles.footerLinkList}>
                <li><a href="#demo-studio">Studio Demo</a></li>
                <li><a href="#cach-hoat-dong">Cách hoạt động</a></li>
                <li><a href="#bang-gia">Bảng giá 6k/ngày</a></li>
                <li><a href="#nguyen-tac">Nguyên tắc an toàn</a></li>
              </ul>
            </div>

            {/* Industries */}
            <div>
              <div className={styles.footerColTitle}>NGÀNH NGHỀ</div>
              <ul className={styles.footerLinkList}>
                <li>
                  <a
                    href="#demo-studio"
                    onClick={(e) => {
                      e.preventDefault();
                      setActiveIndustryIdx(0);
                      document.getElementById("demo-studio")?.scrollIntoView({ behavior: "smooth" });
                    }}
                  >
                    Spa &amp; Làm Đẹp
                  </a>
                </li>
                <li>
                  <a
                    href="#demo-studio"
                    onClick={(e) => {
                      e.preventDefault();
                      setActiveIndustryIdx(1);
                      document.getElementById("demo-studio")?.scrollIntoView({ behavior: "smooth" });
                    }}
                  >
                    Bất Động Sản
                  </a>
                </li>
                <li>
                  <a
                    href="#demo-studio"
                    onClick={(e) => {
                      e.preventDefault();
                      setActiveIndustryIdx(2);
                      document.getElementById("demo-studio")?.scrollIntoView({ behavior: "smooth" });
                    }}
                  >
                    Quán Ăn &amp; Cafe
                  </a>
                </li>
                <li>
                  <a
                    href="#demo-studio"
                    onClick={(e) => {
                      e.preventDefault();
                      setActiveIndustryIdx(3);
                      document.getElementById("demo-studio")?.scrollIntoView({ behavior: "smooth" });
                    }}
                  >
                    Đào Tạo &amp; Dạy Nghề
                  </a>
                </li>
              </ul>
            </div>

            {/* Legal & Account */}
            <div>
              <div className={styles.footerColTitle}>PHÁP LÝ &amp; TÀI KHOẢN</div>
              <ul className={styles.footerLinkList}>
                <li><Link href="/about">Về Havi</Link></li>
                <li><Link href="/terms">Điều khoản sử dụng</Link></li>
                <li><Link href="/privacy">Chính sách bảo mật</Link></li>
                <li><Link href="/login">Đăng nhập</Link></li>
                <li><Link href="/signup">Tạo tài khoản</Link></li>
              </ul>
            </div>

            {/* Contact & Support */}
            <div>
              <div className={styles.footerColTitle}>HỖ TRỢ &amp; HỆ THỐNG</div>
              <div style={{ fontSize: "13.5px", color: "#b8c0d0", lineHeight: 1.6 }}>
                <div>Hotline / Zalo: <a href="tel:0984883750" style={{ color: "#38bdf8", fontWeight: 700 }}>0984 883 750</a></div>
                <div style={{ marginTop: "4px" }}>Email: <a href="mailto:hotro@havi.vn" style={{ color: "#38bdf8" }}>hotro@havi.vn</a></div>
                <div style={{ marginTop: "4px" }}>Hạ tầng: <strong>Havi Cloud Vietnam &amp; AI Nodes</strong></div>
              </div>

              <div className={styles.statusIndicator}>
                <span style={{ width: "8px", height: "8px", borderRadius: "99px", background: "#10b981", boxShadow: "0 0 10px #10b981" }} />
                Dịch vụ AI sẵn sàng
              </div>
            </div>
          </div>

          {/* Footer Bottom Bar */}
          <div className={styles.footerBottom}>
            <div className={styles.copyright}>
              © 2026 Havi Platform. All rights reserved. Designed for Small Business Growth.
            </div>

            <div className={styles.socialRow}>
              <a href="https://facebook.com" target="_blank" rel="noreferrer" className={styles.socialBtn} aria-label="Facebook">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M24 12a12 12 0 1 0-13.9 11.9v-8.4H7.1V12h3V9.4c0-3 1.8-4.6 4.5-4.6 1.3 0 2.6.23 2.6.23v2.9h-1.5c-1.4 0-1.9.9-1.9 1.8V12h3.3l-.5 3.5h-2.8v8.4A12 12 0 0 0 24 12Z" /></svg>
              </a>
              <a href="https://tiktok.com" target="_blank" rel="noreferrer" className={styles.socialBtn} aria-label="TikTok">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M19.59 6.69a4.83 4.83 0 0 1-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 0 1-5.2 1.74 2.89 2.89 0 0 1 2.31-4.64c.298-.002.595.042.88.13V9.4a6.33 6.33 0 0 0-1-.08A6.34 6.34 0 0 0 3 15.66a6.34 6.34 0 0 0 10.81 4.47c1.66-1.57 2.01-4.08 2.01-6.19v-4.3a8.16 8.16 0 0 0 4.77 1.52v-3.4a4.85 4.85 0 0 1-1-.07z" /></svg>
              </a>
              <a href="https://youtube.com" target="_blank" rel="noreferrer" className={styles.socialBtn} aria-label="YouTube">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z" /></svg>
              </a>
            </div>
          </div>
        </div>
      </footer>

      {/* B2B Consultation Modal */}
      {isB2BModalOpen && (
        <div className={styles.modalOverlay} onClick={() => setIsB2BModalOpen(false)}>
          <div
            className={styles.b2bModal}
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-labelledby="b2b-modal-title"
          >
            <div className={styles.modalHeader}>
              <div>
                <h2 id="b2b-modal-title" className={styles.modalTitle}>
                  🏢 Tư Vấn Giải Pháp Havi Enterprise
                </h2>
                <p className={styles.modalSubtitle}>
                  Dành cho chuỗi &gt; 5 cơ sở, Agency, hoặc doanh nghiệp cần xuất hoá đơn VAT &amp; tích hợp API riêng.
                </p>
              </div>
              <button
                type="button"
                className={styles.modalClose}
                onClick={() => setIsB2BModalOpen(false)}
                aria-label="Đóng"
              >
                ✕
              </button>
            </div>

            {b2bSubmitted ? (
              <div className={styles.b2bSuccessAlert}>
                <div style={{ fontSize: "36px", marginBottom: "8px" }}>🎉</div>
                <h3 className={styles.b2bSuccessTitle}>Gửi Yêu Cầu Thành Công!</h3>
                <p className={styles.b2bSuccessDesc}>
                  Chuyên viên giải pháp Havi Enterprise sẽ liên hệ lại với <strong>{b2bForm.name || "Quý Doanh Nghiệp"}</strong> qua số điện thoại/Zalo <strong>{b2bForm.phone || "của bạn"}</strong> trong vòng 15 phút.
                </p>
                <div style={{ marginTop: "18px" }}>
                  <button
                    type="button"
                    className={styles.ctaButton}
                    style={{ border: "none", cursor: "pointer", width: "100%" }}
                    onClick={() => setIsB2BModalOpen(false)}
                  >
                    Đã Hiểu
                  </button>
                </div>
              </div>
            ) : (
              <form onSubmit={handleB2BSubmit} className={styles.b2bForm}>
                <div className={styles.formRow}>
                  <div className={styles.formGroup}>
                    <label className={styles.formLabel}>Tên Doanh Nghiệp / Chuỗi *</label>
                    <input
                      type="text"
                      required
                      placeholder="VD: Viện Thẩm Mỹ Seoul Spa"
                      className={styles.formInput}
                      value={b2bForm.company}
                      onChange={(e) => setB2bForm({ ...b2bForm, company: e.target.value })}
                    />
                  </div>
                  <div className={styles.formGroup}>
                    <label className={styles.formLabel}>Họ và tên người liên hệ *</label>
                    <input
                      type="text"
                      required
                      placeholder="VD: Nguyễn Văn A (Giám đốc)"
                      className={styles.formInput}
                      value={b2bForm.name}
                      onChange={(e) => setB2bForm({ ...b2bForm, name: e.target.value })}
                    />
                  </div>
                </div>

                <div className={styles.formRow}>
                  <div className={styles.formGroup}>
                    <label className={styles.formLabel}>Số điện thoại / Zalo *</label>
                    <input
                      type="tel"
                      required
                      placeholder="VD: 0912 345 678"
                      className={styles.formInput}
                      value={b2bForm.phone}
                      onChange={(e) => setB2bForm({ ...b2bForm, phone: e.target.value })}
                    />
                  </div>
                  <div className={styles.formGroup}>
                    <label className={styles.formLabel}>Quy mô cơ sở</label>
                    <select
                      className={styles.formSelect}
                      value={b2bForm.branches}
                      onChange={(e) => setB2bForm({ ...b2bForm, branches: e.target.value })}
                    >
                      <option value="5-10 chi nhánh">Chuỗi 5 – 10 chi nhánh</option>
                      <option value="> 10 chi nhánh">Chuỗi lớn &gt; 10 chi nhánh</option>
                      <option value="Agency Marketing">Agency Marketing / Quản lý nhiều Page</option>
                      <option value="Hợp đồng & VAT">Cần hợp đồng &amp; hoá đơn VAT</option>
                    </select>
                  </div>
                </div>

                <div className={styles.formGroup}>
                  <label className={styles.formLabel}>Nhu cầu chi tiết hoặc câu hỏi</label>
                  <textarea
                    rows={3}
                    placeholder="Mô tả nhu cầu tích hợp API, đào tạo nhân viên, hoặc setup private cloud..."
                    className={styles.formTextarea}
                    value={b2bForm.notes}
                    onChange={(e) => setB2bForm({ ...b2bForm, notes: e.target.value })}
                  />
                </div>

                <button type="submit" className={styles.b2bSubmitBtn}>
                  🚀 Gửi Yêu Cầu Tư Vấn Ngay
                </button>

                <div className={styles.b2bHotlineRow}>
                  <span style={{ fontSize: "12px", color: "#64748b" }}>Hoặc liên hệ nhanh Hotline / Zalo:</span>
                  <a href="tel:0984883750" className={styles.b2bHotlineBtn}>
                    📞 0984 883 750
                  </a>
                  <a href="https://zalo.me/0984883750" target="_blank" rel="noreferrer" className={styles.b2bHotlineBtn}>
                    💬 Chat Zalo Trực Tiếp
                  </a>
                </div>
              </form>
            )}
          </div>
        </div>
      )}

      {/* Video Demo Modal (60s Tour) */}
      <VideoDemoModal
        isOpen={isVideoModalOpen}
        onClose={() => setIsVideoModalOpen(false)}
        lang={lang}
      />
    </div>
  );
}

