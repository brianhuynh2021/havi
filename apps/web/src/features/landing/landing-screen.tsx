"use client";

import { useState } from "react";
import Link from "next/link";
import { Logo } from "@/components/ui/logo";
import {
  heroChannels,
  heroStats,
  industries,
  principles,
  steps,
} from "./landing.content";
import styles from "./landing.module.css";

const PREVIEW_DRAFTS: Record<
  string,
  { photo: string; text: string; tag: string; rawInput?: string }
> = {
  Facebook: {
    photo: "/images/spa_photo_hq.jpg",
    text: "Tuần này Spa bên mình có ưu đãi đặc biệt cho 30 khách đặt lịch tái khám sớm — nhắn tin qua Fanpage để giữ chỗ trước nha chị em!",
    tag: "Fanpage Post",
    rawInput: "Chụp 1 tấm ảnh Spa liệu trình vi kim rảo mụn",
  },
  "Zalo OA": {
    photo: "/images/spa_photo_hq.jpg",
    text: "Bản tin Zalo OA: Nhắc lịch tái khám & quà tặng serum phục hồi cao cấp dành riêng cho khách hàng thân thiết trong tuần này.",
    tag: "Zalo Care",
    rawInput: "Ghi âm 15s nhắc khách tái khám đúng hẹn",
  },
  "Google Business": {
    photo: "/images/cafe_photo_hq.jpg",
    text: "Ghé trải nghiệm không gian và thưởng thức cà phê rang xay thơm nức tại tiệm — Đánh giá 5 sao nhận ngay ưu đãi quà tặng!",
    tag: "Google Business Post",
    rawInput: "Món mới cà phê dừa nướng thơm nức",
  },
  "Bản tin Email": {
    photo: "/images/bds_photo_hq.jpg",
    text: "[Báo giá mới nhất] Gửi anh/chị thông tin 3 căn nhà vị trí đẹp, giá đầu tư cực tốt kèm thông tin chính chủ nét.",
    tag: "Email Marketing",
    rawInput: "Nhà phố Q7 chính chủ 85m²",
  },
};

export function LandingScreen() {
  const [activeChannel, setActiveChannel] = useState("Facebook");
  const [activeStep, setActiveStep] = useState(0);
  const [activeIndustry, setActiveIndustry] = useState(0);
  const [lang, setLang] = useState<"VN" | "EN">("VN");

  const currentDraft = PREVIEW_DRAFTS[activeChannel] || PREVIEW_DRAFTS.Facebook;
  const currentInd = industries[activeIndustry] || industries[0];

  return (
    <div className={styles.page}>
      {/* Header */}
      <header className={styles.header}>
        <div className={styles.headerInner}>
          <Link href="/gioi-thieu" className={styles.brand}>
            <Logo size={38} />
            <span className={styles.brandText}>Havi</span>
          </Link>

          <nav className={styles.nav} aria-label="Điều hướng trang">
            <a href="#cach-hoat-dong">{lang === "VN" ? "Cách hoạt động" : "How it works"}</a>
            <a href="#nganh">{lang === "VN" ? "Cho ngành của bạn" : "Industries"}</a>
            <a href="#nguyen-tac">{lang === "VN" ? "Nguyên tắc" : "Principles"}</a>
          </nav>

          <div className={styles.headerActions}>
            {/* Language Switcher Pill */}
            <button
              type="button"
              onClick={() => setLang(lang === "VN" ? "EN" : "VN")}
              style={{
                background: "rgba(255, 255, 255, 0.06)",
                border: "1px solid rgba(255, 255, 255, 0.15)",
                borderRadius: "99px",
                padding: "6px 14px",
                color: "#f8fafc",
                fontSize: "13px",
                fontWeight: 700,
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: "6px",
                transition: "all 0.2s ease",
              }}
            >
              <span>{lang === "VN" ? "🇻🇳 VN" : "🇬🇧 EN"}</span>
              <span style={{ color: "#64748b", fontSize: "11px" }}>▼</span>
            </button>

            <Link href="/dang-nhap" className={styles.loginLink}>
              {lang === "VN" ? "Đăng nhập" : "Login"}
            </Link>
            <Link href="/dang-ky" className={styles.ctaButton}>
              {lang === "VN" ? "Tạo tài khoản" : "Get Started"}
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className={styles.hero}>
        <div>
          <div className={styles.eyebrow}>
            <span style={{ fontSize: "14px" }}>✨</span> Trợ Lý AI Marketing Đa Kênh Cho Tiệm &amp; Shop
          </div>
          <h1 className={styles.heroTitle}>
            Tải ảnh tiệm lên, bài đăng &amp; Email sẵn sàng —{" "}
            bạn chỉ cần bấm <span className={styles.purpleGradient}>duyệt 1-chạm</span>
          </h1>
          <p className={styles.heroBody}>
            Không cần giỏi văn hay am hiểu công nghệ. Chỉ cần chụp ảnh tiệm hoặc ghi âm 15s — Havi tự biên soạn bài viết chuẩn giọng tiệm cho Facebook, Zalo OA, Google Business &amp; Email.{" "}
            <strong style={{ color: "#f8fafc" }}>Bài không tự phát hành khi bạn chưa nhấn nút duyệt.</strong>
          </p>

          <div className={styles.heroActions}>
            <Link href="/dang-ky" className={styles.ctaButton}>
              Tạo tài khoản miễn phí
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path d="M5 12h14M12 5l7 7-7 7" />
              </svg>
            </Link>
            <a href="#demo-studio" className={styles.btnSecondary}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#10B981" strokeWidth="2.5">
                <polygon points="5 3 19 12 5 21 5 3" />
              </svg>
              Xem Studio Demo Trực Quan
            </a>
          </div>

          {/* Stats Section With Icons & Clear Friendly Copy */}
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

      {/* Clean Friendly Studio Demo Showcase */}
      <section id="demo-studio" className={styles.demoStudioSection}>
        <div className={`${styles.glassCard} ${styles.glassCardGlow}`}>
          {/* Studio Header Bar */}
          <div className={styles.studioHeader}>
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <div className={styles.macDots}>
                <span className={styles.dotRed} />
                <span className={styles.dotYellow} />
                <span className={styles.dotGreen} />
              </div>
              <span className={styles.studioTitle}>
                Havi AI Studio • Trình Mô Phỏng Biên Soạn Đa Kênh Tự Động
              </span>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
              <div className={styles.soundWave}>
                <div className={styles.soundBar} />
                <div className={styles.soundBar} />
                <div className={styles.soundBar} />
              </div>
              <span style={{ fontSize: "12px", fontWeight: 700, background: "rgba(139,92,246,0.18)", color: "#c084fc", border: "1px solid rgba(139,92,246,0.35)", borderRadius: "99px", padding: "4px 12px" }}>
                🟢 HỆ THỐNG DỊCH VỤ SẴN SÀNG
              </span>
            </div>
          </div>

          {/* Studio Body */}
          <div className={styles.studioBody}>
            {/* Step Controls Sidebar */}
            <div className={styles.studioSidebar}>
              <div className={styles.stepTitle}>Quy Trình 4 Bước</div>
              <div className={styles.stepList}>
                {steps.map((st, idx) => (
                  <div
                    key={st.n}
                    className={`${styles.stepItem} ${activeStep === idx ? styles.stepItemActive : ""}`}
                    onClick={() => setActiveStep(idx)}
                  >
                    <div className={styles.stepNum}>{st.n}</div>
                    <div>
                      <div className={styles.stepName}>{st.title}</div>
                      <div className={styles.stepDesc}>{st.desc}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Main Interactive Canvas */}
            <div className={styles.studioCanvas}>
              {/* Channel Tabs */}
              <div className={styles.channelTabs}>
                <span style={{ fontSize: "12.5px", fontWeight: 700, color: "#64748b", marginRight: "6px" }}>
                  Kênh Đang Xem:
                </span>
                {heroChannels.map((ch) => (
                  <button
                    key={ch.n}
                    type="button"
                    className={`${styles.channelTab} ${activeChannel === ch.n ? styles.channelTabActive : ""}`}
                    onClick={() => setActiveChannel(ch.n)}
                  >
                    <span style={{ width: "6px", height: "6px", borderRadius: "99px", background: ch.c, display: "inline-block", marginRight: "6px" }} />
                    {ch.n}
                  </button>
                ))}
              </div>

              {/* Demo Content Card */}
              <div className={styles.demoFrame}>
                <div className={styles.demoCardContent}>
                  <div className={styles.demoPhoto}>
                    <img src={currentDraft.photo} alt="Preview showcase" />
                    <span className={styles.badgeRaw}>ẢNH TIỆM THẬT</span>
                  </div>

                  <div className={styles.demoTextCol}>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "8px" }}>
                      <span className={styles.aiBadge}>✨ BÀI NHÁP BỞI HAVI AI</span>
                      <span style={{ fontSize: "12px", color: "#64748b" }}>{currentDraft.tag}</span>
                    </div>

                    {currentDraft.rawInput && (
                      <div style={{ fontSize: "12px", color: "#c084fc", background: "rgba(139,92,246,0.15)", padding: "4px 10px", borderRadius: "6px", marginBottom: "10px" }}>
                        📥 Nguồn ảnh/ghi âm: {currentDraft.rawInput}
                      </div>
                    )}

                    <p className={styles.demoBody}>{currentDraft.text}</p>

                    <div className={styles.demoTags}>
                      <span className={styles.tagItem}>#HaviAI</span>
                      <span className={styles.tagItem}>#Duyet1Cham</span>
                      <span style={{ fontSize: "11px", fontWeight: 700, color: "#c084fc", background: "rgba(139,92,246,0.18)", padding: "4px 10px", borderRadius: "6px" }}>
                        Lịch đăng: 19:30 Tối nay (Giờ Vàng Tiệm)
                      </span>
                    </div>
                  </div>
                </div>

                {/* Action Bar */}
                <div className={styles.actionBar}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "13px", color: "#b8c0d0" }}>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#8B5CF6" strokeWidth="2.5">
                      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                      <polyline points="22 4 12 14.01 9 11.01" />
                    </svg>
                    <span>Havi biên soạn sẵn — <strong style={{ color: "#fff" }}>Bạn đọc lướt rồi bấm duyệt 1-chạm</strong></span>
                  </div>
                  <div style={{ display: "flex", gap: "12px" }}>
                    <Link href="/dang-ky" className={styles.ctaButton}>
                      Duyệt bài này 1-chạm
                    </Link>
                  </div>
                </div>
              </div>

              {/* Floating Badge */}
              <div className={styles.floatingImpactBadge}>
                <div style={{ width: "36px", height: "36px", borderRadius: "99px", background: "rgba(139,92,246,0.2)", color: "#c084fc", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 800, fontSize: "16px" }}>
                  ✓
                </div>
                <div>
                  <div style={{ fontSize: "13.5px", fontWeight: 800, color: "#fff" }}>Bài đăng &amp; email sẵn sàng</div>
                  <div style={{ fontSize: "12px", color: "#c084fc", fontWeight: 600, marginTop: "2px" }}>Bấm duyệt 1-chạm để phát hành</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Cách Hoạt Động (Bento Grid) */}
      <section id="cach-hoat-dong" className={styles.hero} style={{ paddingTop: "40px" }}>
        <div className={styles.sectionHeader}>
          <div className={styles.sectionTag}>QUY TRÌNH VẬN HÀNH TIỆM</div>
          <h2 className={styles.sectionTitle}>Bốn Bước Tiết Kiệm Thời Gian Vận Hành</h2>
          <p className={styles.sectionSubtitle}>Dành cho chủ tiệm &amp; môi giới bận rộn — tiết kiệm tới 15 giờ mỗi tuần.</p>
        </div>

        <div className={styles.bentoGrid}>
          {steps.map((st, idx) => (
            <div
              key={st.n}
              className={`${styles.glassCard} ${idx === 0 || idx === 3 ? styles.bentoSpan2 : ""}`}
              style={{ padding: "36px", textAlign: "left" }}
            >
              <span style={{ fontSize: "12px", fontWeight: 800, color: "#c084fc", background: "rgba(139,92,246,0.18)", padding: "4px 12px", borderRadius: "99px" }}>
                BƯỚC 0{st.n}
              </span>
              <h3 style={{ fontSize: "24px", fontWeight: 800, color: "#fff", margin: "16px 0 12px" }}>{st.title}</h3>
              <p style={{ fontSize: "15px", color: "#b8c0d0", lineHeight: 1.6, margin: 0 }}>{st.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Cho Ngành Của Bạn */}
      <section id="nganh" className={styles.hero} style={{ paddingTop: "20px" }}>
        <div className={styles.sectionHeader}>
          <div className={styles.sectionTag} style={{ color: "#38bdf8" }}>CHO NGÀNH CỦA BẠN</div>
          <h2 className={styles.sectionTitle}>Tối Ưu Giọng Văn Cho Từng Mô Hình Tiệm</h2>
          <p className={styles.sectionSubtitle}>Dù bạn chạy Spa, tiệm Cà phê, BĐS hay Shop online, Havi tự điều chỉnh bộ từ vựng chính xác.</p>
        </div>

        <div className={styles.channelTabs} style={{ justifyContent: "center", marginBottom: "40px" }}>
          {industries.map((ind, idx) => (
            <button
              key={ind.name}
              type="button"
              className={`${styles.channelTab} ${activeIndustry === idx ? styles.channelTabActive : ""}`}
              onClick={() => setActiveIndustry(idx)}
              style={{ padding: "10px 22px", fontSize: "14px" }}
            >
              {ind.name}
            </button>
          ))}
        </div>

        <div className={styles.bentoGrid} style={{ gridTemplateColumns: "1fr 1.2fr", alignItems: "center" }}>
          <div className={styles.glassCard} style={{ padding: "20px", overflow: "hidden", borderRadius: "20px" }}>
            <img src={currentInd.image} alt={currentInd.name} style={{ width: "100%", height: "320px", objectFit: "cover", borderRadius: "14px", display: "block" }} />
          </div>

          <div className={styles.glassCard} style={{ padding: "36px", textAlign: "left" }}>
            <h3 style={{ fontSize: "26px", fontWeight: 800, color: "#fff", margin: "0 0 20px" }}>{currentInd.name}</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
              {currentInd.rows.map((rw) => (
                <div key={rw.k} style={{ padding: "14px 18px", background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "12px" }}>
                  <span style={{ fontSize: "12px", fontWeight: 800, color: "#38bdf8", textTransform: "uppercase" }}>{rw.k}</span>
                  <div style={{ fontSize: "14.5px", color: "#e2e8f0", marginTop: "4px", fontWeight: 500 }}>{rw.t}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Nguyên Tắc & Bảng Giá Khảo Sát */}
      <section id="nguyen-tac" className={styles.hero} style={{ paddingTop: "20px" }}>
        <div className={styles.sectionHeader}>
          <div className={styles.sectionTag} style={{ color: "#10b981" }}>NGUYÊN TẮC VẬN HÀNH</div>
          <h2 className={styles.sectionTitle}>Havi Đang Trong Giai Đoạn Thử Nghiệm</h2>
          <p className={styles.sectionSubtitle}>Bảng giá sẽ công bố sau khi hoàn tất đo lường thực tế — Bài không tự phát hành khi chưa bấm nút.</p>
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
                Giải pháp Nhân viên AI Marketing Đa Kênh tự động cho mọi thương hiệu &amp; doanh nghiệp. Tự động hóa bài viết &amp; email chăm sóc chuẩn giọng Việt, duyệt 100% trước khi đăng.
              </p>
              <div className={styles.trustBadges}>
                <span className={styles.trustBadge}>🔒 Official API</span>
                <span className={styles.trustBadge}>🇻🇳 Tiếng Việt Là Gốc</span>
                <span className={styles.trustBadge}>⚡ 100% Duyệt Trước</span>
              </div>
            </div>

            {/* Product Links */}
            <div>
              <div className={styles.footerColTitle}>SẢN PHẨM</div>
              <ul className={styles.footerLinkList}>
                <li><a href="#cach-hoat-dong">Cách hoạt động</a></li>
                <li><a href="#demo-studio">Studio Showcase</a></li>
                <li><a href="#nganh">Cho ngành của bạn</a></li>
                <li><a href="#nguyen-tac">Nguyên tắc cốt lõi</a></li>
              </ul>
            </div>

            {/* Industries */}
            <div>
              <div className={styles.footerColTitle}>NGÀNH NGHỀ</div>
              <ul className={styles.footerLinkList}>
                <li><a href="#nganh">Spa &amp; Tiệm Làm Đẹp</a></li>
                <li><a href="#nganh">Quán Ăn &amp; Cà Phê</a></li>
                <li><a href="#nganh">Môi Giới Bất Động Sản</a></li>
                <li><a href="#nganh">Shop Online &amp; Traffic</a></li>
              </ul>
            </div>

            {/* Legal & Account */}
            <div>
              <div className={styles.footerColTitle}>PHÁP LÝ &amp; TÀI KHOẢN</div>
              <ul className={styles.footerLinkList}>
                <li><Link href="/gioi-thieu">Về Havi</Link></li>
                <li><Link href="/dieu-khoan">Điều khoản sử dụng</Link></li>
                <li><Link href="/bao-mat">Chính sách bảo mật</Link></li>
                <li><Link href="/dang-nhap">Đăng nhập</Link></li>
                <li><Link href="/dang-ky">Tạo tài khoản</Link></li>
              </ul>
            </div>

            {/* Contact & Support */}
            <div>
              <div className={styles.footerColTitle}>HỖ TRỢ &amp; HỆ THỐNG</div>
              <div style={{ fontSize: "13.5px", color: "#b8c0d0", lineHeight: 1.6 }}>
                <div>Email: <a href="mailto:hotro@havi.vn" style={{ color: "#38bdf8" }}>hotro@havi.vn</a></div>
                <div style={{ marginTop: "4px" }}>Khu vực: TP. Hồ Chí Minh, Việt Nam</div>
              </div>

              {/* Language Switcher Footer Pill */}
              <div style={{ marginTop: "16px" }}>
                <button
                  type="button"
                  onClick={() => setLang(lang === "VN" ? "EN" : "VN")}
                  style={{
                    background: "rgba(255, 255, 255, 0.06)",
                    border: "1px solid rgba(255, 255, 255, 0.15)",
                    borderRadius: "8px",
                    padding: "6px 12px",
                    color: "#34d399",
                    fontSize: "12px",
                    fontWeight: 700,
                    cursor: "pointer",
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "6px",
                  }}
                >
                  <span>{lang === "VN" ? "🇻🇳 Tiếng Việt (VN)" : "🇬🇧 English (EN)"}</span>
                </button>
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
              <a href="https://zalo.me" target="_blank" rel="noreferrer" className={styles.socialBtn} aria-label="Zalo">
                <span style={{ fontWeight: 800, fontSize: "12px" }}>Zalo</span>
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
