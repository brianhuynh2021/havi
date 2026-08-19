"use client";

import { useState } from "react";
import Link from "next/link";
import { Logo } from "@/components/ui/logo";
import { LanguageSwitcher } from "@/components/ui/language-switcher";
import {
  heroChannels,
  heroStats,
  industryScenarios,
  principles,
  steps,
} from "./landing.content";
import styles from "./landing.module.css";
import { useLanguage } from "@/lib/i18n/language-context";

type ChannelTabKey = "facebook" | "video" | "maps" | "inbox";

export function LandingScreen() {
  const [activeIndustryIdx, setActiveIndustryIdx] = useState(0);
  const [activeChannelKey, setActiveChannelKey] = useState<ChannelTabKey>("facebook");
  const [activeStep, setActiveStep] = useState(0);
  const { lang } = useLanguage();

  const currentScenario = industryScenarios[activeIndustryIdx] || industryScenarios[0];
  const activeTabContent = currentScenario.tabs[activeChannelKey];

  return (
    <div className={styles.page}>
      {/* Header */}
      <header className={styles.header}>
        <div className={styles.headerInner}>
          <Link href="/about" className={styles.brand}>
            <Logo size={38} />
            <span className={styles.brandText}>Havi</span>
          </Link>

          <nav className={styles.nav} aria-label="Điều hướng trang">
            <a href="#demo-studio">{lang === "VN" ? "Dùng thử Demo" : "Live Demo"}</a>
            <a href="#cach-hoat-dong">{lang === "VN" ? "Cách hoạt động" : "How it works"}</a>
            <a href="#bang-gia">{lang === "VN" ? "Bảng giá" : "Pricing"}</a>
            <a href="#nguyen-tac">{lang === "VN" ? "Nguyên tắc" : "Principles"}</a>
          </nav>

          <div className={styles.headerActions}>
            <LanguageSwitcher variant="pill" />

            <Link href="/login" className={styles.loginLink}>
              {lang === "VN" ? "Đăng nhập" : "Login"}
            </Link>
            <Link href="/signup" className={styles.ctaButton}>
              {lang === "VN" ? "Dùng thử 14 ngày" : "Get Started"}
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className={styles.hero}>
        <div>
          <div className={styles.eyebrow}>
            <span style={{ fontSize: "14px" }}>✨</span> NHÂN VIÊN AI MARKETING ĐA KÊNH — TRỰC TIỆM &amp; CHỐT ĐƠN 24/7
          </div>
          <h1 className={styles.heroTitle}>
            Tải ảnh tiệm lên, bài đăng &amp; Video sẵn sàng —{" "}
            bạn chỉ cần bấm <span className={styles.purpleGradient}>duyệt 1-chạm</span>
          </h1>
          <p className={styles.heroBody}>
            Thay thế 1 nhân viên marketing part-time 4 triệu/tháng chỉ với <strong style={{ color: "#38bdf8" }}>~6.000 đ/ngày (189k/tháng)</strong>. Chỉ cần chụp ảnh tiệm hoặc ghi âm 15s — Havi tự động sáng tạo bài viết Facebook, kịch bản Video TikTok 9:16 có Hook 3s giật tít, bài Google Maps và trực Inbox trả lời bảng giá bắt số điện thoại khách trong 5 giây.{" "}
            <strong style={{ color: "#f8fafc" }}>Bài không tự phát hành khi bạn chưa nhấn nút duyệt.</strong>
          </p>

          <div className={styles.heroActions}>
            <Link href="/signup" className={styles.ctaButton}>
              Bắt đầu dùng thử 7 ngày miễn phí
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path d="M5 12h14M12 5l7 7-7 7" />
              </svg>
            </Link>
            <a href="#demo-studio" className={styles.btnSecondary}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#10B981" strokeWidth="2.5">
                <polygon points="5 3 19 12 5 21 5 3" />
              </svg>
              Bấm Thử Demo Trực Tuyến
            </a>
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

      {/* Interactive Live Studio Demo Showcase */}
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
                Havi AI Studio • Trình Mô Phỏng 4 Trụ Cột Đa Kênh Tự Động
              </span>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
              <span style={{ fontSize: "12px", fontWeight: 700, background: "rgba(16,185,129,0.18)", color: "#34d399", border: "1px solid rgba(16,185,129,0.35)", borderRadius: "99px", padding: "4px 12px" }}>
                🟢 KẾT NỐI SẴN SÀNG
              </span>
            </div>
          </div>

          {/* Industry Selection Tabs */}
          <div style={{ padding: "16px 24px", borderBottom: "1px solid rgba(255,255,255,0.06)", display: "flex", alignItems: "center", gap: "10px", overflowX: "auto" }}>
            <span style={{ fontSize: "13px", fontWeight: 700, color: "#94a3b8", whiteSpace: "nowrap" }}>
              Chọn ngành tiệm:
            </span>
            {industryScenarios.map((sc, idx) => (
              <button
                key={sc.name}
                type="button"
                className={`${styles.channelTab} ${activeIndustryIdx === idx ? styles.channelTabActive : ""}`}
                onClick={() => setActiveIndustryIdx(idx)}
                style={{ padding: "8px 18px", fontSize: "13.5px" }}
              >
                <span style={{ marginRight: "6px" }}>{sc.badge}</span>
                {sc.name}
              </button>
            ))}
          </div>

          {/* Studio Body */}
          <div className={styles.studioBody}>
            {/* Step Controls Sidebar */}
            <div id="cach-hoat-dong" className={styles.studioSidebar}>
              <div className={styles.stepTitle}>Quy Trình 4 Bước Tự Động</div>
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
                  Xem Kết Quả Đa Kênh:
                </span>
                <button
                  type="button"
                  className={`${styles.channelTab} ${activeChannelKey === "facebook" ? styles.channelTabActive : ""}`}
                  onClick={() => setActiveChannelKey("facebook")}
                >
                  <span style={{ width: "6px", height: "6px", borderRadius: "99px", background: "#1877F2", display: "inline-block", marginRight: "6px" }} />
                  📱 Facebook Post
                </button>
                <button
                  type="button"
                  className={`${styles.channelTab} ${activeChannelKey === "video" ? styles.channelTabActive : ""}`}
                  onClick={() => setActiveChannelKey("video")}
                >
                  <span style={{ width: "6px", height: "6px", borderRadius: "99px", background: "#FE2C55", display: "inline-block", marginRight: "6px" }} />
                  🎬 TikTok Video (Hook 3s)
                </button>
                <button
                  type="button"
                  className={`${styles.channelTab} ${activeChannelKey === "maps" ? styles.channelTabActive : ""}`}
                  onClick={() => setActiveChannelKey("maps")}
                >
                  <span style={{ width: "6px", height: "6px", borderRadius: "99px", background: "#16A34A", display: "inline-block", marginRight: "6px" }} />
                  📍 Google Maps SEO
                </button>
                <button
                  type="button"
                  className={`${styles.channelTab} ${activeChannelKey === "inbox" ? styles.channelTabActive : ""}`}
                  onClick={() => setActiveChannelKey("inbox")}
                >
                  <span style={{ width: "6px", height: "6px", borderRadius: "99px", background: "#8B5CF6", display: "inline-block", marginRight: "6px" }} />
                  💬 Trực Inbox Bắt SĐT
                </button>
              </div>

              {/* Demo Content Card */}
              <div className={styles.demoFrame}>
                <div className={styles.demoCardContent}>
                  <div className={styles.demoPhoto}>
                    <img src={currentScenario.image} alt={currentScenario.name} />
                    <span className={styles.badgeRaw}>ẢNH TIỆM THẬT</span>
                  </div>

                  <div className={styles.demoTextCol}>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "8px" }}>
                      <span className={styles.aiBadge}>✨ XỬ LÝ BỞI HAVI AI</span>
                      <span style={{ fontSize: "12px", color: "#64748b" }}>{activeTabContent.badge}</span>
                    </div>

                    <div style={{ fontSize: "12px", color: "#c084fc", background: "rgba(139,92,246,0.15)", padding: "4px 10px", borderRadius: "6px", marginBottom: "10px" }}>
                      📥 Nguồn chụp/ghi âm 30s: <strong>{currentScenario.rawInput}</strong>
                    </div>

                    {/* Conditional Rendering by Active Tab */}
                    {activeChannelKey === "facebook" && (
                      <div>
                        <p className={styles.demoBody}>{currentScenario.tabs.facebook.content}</p>
                        <div className={styles.demoTags}>
                          <span className={styles.tagItem}>#HaviAI</span>
                          <span className={styles.tagItem}>#Duyet1Cham</span>
                          <span style={{ fontSize: "11px", fontWeight: 700, color: "#c084fc", background: "rgba(139,92,246,0.18)", padding: "4px 10px", borderRadius: "6px" }}>
                            ⏰ Giờ vàng đăng: 19:30 Tối nay
                          </span>
                        </div>
                      </div>
                    )}

                    {activeChannelKey === "video" && (
                      <div>
                        <div style={{ background: "rgba(254,44,85,0.12)", border: "1px solid rgba(254,44,85,0.3)", borderRadius: "8px", padding: "10px 14px", marginBottom: "10px" }}>
                          <span style={{ fontSize: "11px", fontWeight: 800, color: "#FE2C55", textTransform: "uppercase" }}>
                            ⚡ 3-Second Retention Hook (Giật Tít Giữ Chân)
                          </span>
                          <div style={{ fontSize: "13.5px", fontWeight: 700, color: "#fff", marginTop: "4px" }}>
                            {currentScenario.tabs.video.hook}
                          </div>
                        </div>
                        <p className={styles.demoBody} style={{ whiteSpace: "pre-line", fontSize: "13px" }}>
                          {currentScenario.tabs.video.script}
                        </p>
                      </div>
                    )}

                    {activeChannelKey === "maps" && (
                      <div>
                        <p className={styles.demoBody}>{currentScenario.tabs.maps.content}</p>
                        <div style={{ display: "flex", gap: "8px", marginTop: "12px" }}>
                          <span style={{ fontSize: "11.5px", fontWeight: 700, color: "#34d399", background: "rgba(16,185,129,0.15)", padding: "4px 10px", borderRadius: "6px" }}>
                            ⭐ Tối ưu xếp hạng Top 3 Google Maps
                          </span>
                          <span style={{ fontSize: "11.5px", color: "#94a3b8", background: "rgba(255,255,255,0.05)", padding: "4px 10px", borderRadius: "6px" }}>
                            📍 Geotagged Local SEO
                          </span>
                        </div>
                      </div>
                    )}

                    {activeChannelKey === "inbox" && (
                      <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                        <div style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "10px", padding: "10px 14px", alignSelf: "flex-start", maxWidth: "90%" }}>
                          <span style={{ fontSize: "11px", color: "#94a3b8" }}>👤 Khách hàng (Lúc 23:15 đêm):</span>
                          <div style={{ fontSize: "13.5px", color: "#fff", marginTop: "2px" }}>
                            {currentScenario.tabs.inbox.customerMsg}
                          </div>
                        </div>

                        <div style={{ background: "rgba(139,92,246,0.15)", border: "1px solid rgba(139,92,246,0.3)", borderRadius: "10px", padding: "10px 14px", alignSelf: "flex-end", maxWidth: "95%" }}>
                          <span style={{ fontSize: "11px", fontWeight: 700, color: "#c084fc" }}>✨ Havi Tự Trả Lời (Sau 5 giây):</span>
                          <div style={{ fontSize: "13.5px", color: "#f8fafc", marginTop: "2px" }}>
                            {currentScenario.tabs.inbox.haviReply}
                          </div>
                        </div>

                        <div style={{ background: "rgba(16,185,129,0.15)", border: "1px solid rgba(16,185,129,0.35)", borderRadius: "8px", padding: "8px 12px", display: "flex", alignItems: "center", gap: "8px" }}>
                          <span style={{ fontSize: "14px" }}>🟢</span>
                          <span style={{ fontSize: "12.5px", fontWeight: 700, color: "#34d399" }}>
                            Đã bắt SĐT về CRM: {currentScenario.tabs.inbox.capturedPhone}
                          </span>
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Action Bar */}
                <div className={styles.actionBar}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "13px", color: "#b8c0d0" }}>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#8B5CF6" strokeWidth="2.5">
                      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                      <polyline points="22 4 12 14.01 9 11.01" />
                    </svg>
                    <span>Havi tự động hoàn thiện — <strong style={{ color: "#fff" }}>Bạn chỉ cần bấm duyệt 1-chạm</strong></span>
                  </div>
                  <div style={{ display: "flex", gap: "12px" }}>
                    <Link href="/signup" className={styles.ctaButton}>
                      Duyệt &amp; kích hoạt ngay
                    </Link>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Bảng Giá Thương Mại & So Sánh ROI (Chiến thuật FAANG) */}
      <section id="bang-gia" className={styles.hero} style={{ paddingTop: "40px" }}>
        <div className={styles.sectionHeader}>
          <div className={styles.sectionTag} style={{ color: "#34d399" }}>BẢNG GIÁ ĐẦU TƯ TIẾT KIỆM</div>
          <h2 className={styles.sectionTitle}>Chỉ Từ 6.000 đ/Ngày — Rẻ Hơn 1 Ly Trà Sữa</h2>
          <p className={styles.sectionSubtitle}>Không phụ phí ẩn · Tự động kích hoạt VietQR trong 1 giây · Hoàn tiền nếu không hài lòng sau 7 ngày.</p>
        </div>

        <div className={styles.bentoGrid} style={{ gridTemplateColumns: "repeat(3, 1fr)", marginBottom: "30px" }}>
          {/* Free Trial */}
          <div className={styles.glassCard} style={{ padding: "32px", textAlign: "left", display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
            <div>
              <span style={{ fontSize: "12px", fontWeight: 800, color: "#94a3b8", background: "rgba(255,255,255,0.06)", padding: "4px 10px", borderRadius: "99px" }}>
                TRẢI NGHIỆM
              </span>
              <h3 style={{ fontSize: "22px", fontWeight: 800, color: "#fff", margin: "14px 0 6px" }}>Gói Dùng Thử</h3>
              <div style={{ fontSize: "32px", fontWeight: 900, color: "#fff", marginBottom: "14px" }}>
                0 đ <span style={{ fontSize: "14px", fontWeight: 500, color: "#94a3b8" }}>/ 7 ngày</span>
              </div>
              <p style={{ fontSize: "14px", color: "#94a3b8", lineHeight: 1.5, marginBottom: "20px" }}>
                Trải nghiệm trọn vẹn sức mạnh nhân viên AI — Không cần thẻ tín dụng.
              </p>
              <ul style={{ listStyle: "none", padding: 0, margin: "0 0 24px 0", display: "flex", flexDirection: "column", gap: "10px", fontSize: "13.5px", color: "#cbd5e1" }}>
                <li>✓ Dùng thử 7 ngày không rủi ro</li>
                <li>✓ Kết nối 1 Fanpage Facebook</li>
                <li>✓ Trực Inbox &amp; Trả lời Bảng giá/FAQ 24/7</li>
                <li>✓ Lên lịch đăng giờ vàng tự động</li>
              </ul>
            </div>
            <Link href="/signup" className={styles.btnSecondary} style={{ width: "100%", justifyContent: "center" }}>
              Dùng thử miễn phí
            </Link>
          </div>

          {/* Gói Khởi Nghiệp (189.000 đ) */}
          <div className={styles.glassCard} style={{ padding: "32px", textAlign: "left", display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
            <div>
              <span style={{ fontSize: "12px", fontWeight: 800, color: "#38bdf8", background: "rgba(56,189,248,0.15)", padding: "4px 10px", borderRadius: "99px" }}>
                GÓI PHỔ CẬP
              </span>
              <h3 style={{ fontSize: "22px", fontWeight: 800, color: "#fff", margin: "14px 0 6px" }}>Gói Khởi Nghiệp</h3>
              <div style={{ fontSize: "32px", fontWeight: 900, color: "#38bdf8", marginBottom: "14px" }}>
                189.000 đ <span style={{ fontSize: "14px", fontWeight: 500, color: "#94a3b8" }}>/ tháng (~6.000 đ/ngày)</span>
              </div>
              <p style={{ fontSize: "14px", color: "#94a3b8", lineHeight: 1.5, marginBottom: "20px" }}>
                Rẻ hơn 1 ly trà sữa mỗi tuần — Khiến mọi chủ tiệm đều có thể bắt đầu ngay.
              </p>
              <ul style={{ listStyle: "none", padding: 0, margin: "0 0 24px 0", display: "flex", flexDirection: "column", gap: "10px", fontSize: "13.5px", color: "#cbd5e1" }}>
                <li>✓ <strong>1 Fanpage Facebook</strong> kết nối</li>
                <li>✓ <strong>30 bài viết AI/tháng</strong> (Ảnh tiệm ➔ Bài chuẩn ngành)</li>
                <li>✓ <strong>Trực Inbox 24/7</strong> &amp; Bắt SĐT khách tự động</li>
                <li>✓ Báo cáo tương tác cơ bản</li>
                <li>✓ Hỗ trợ kỹ thuật 24/7</li>
              </ul>
            </div>
            <Link href="/signup" className={styles.btnSecondary} style={{ width: "100%", justifyContent: "center" }}>
              Nâng cấp Gói Khởi Nghiệp
            </Link>
          </div>

          {/* Gói Chuyên Nghiệp (369.000 đ - Best Seller) */}
          <div className={`${styles.glassCard} ${styles.glassCardGlow}`} style={{ padding: "32px", textAlign: "left", borderColor: "rgba(139,92,246,0.6)", display: "flex", flexDirection: "column", justifyContent: "space-between", position: "relative" }}>
            <div style={{ position: "absolute", top: "-12px", right: "20px", background: "linear-gradient(135deg, #8B5CF6, #00D2FF)", color: "#fff", fontSize: "11px", fontWeight: 800, padding: "4px 12px", borderRadius: "99px" }}>
              BÁN CHẠY NHẤT ★
            </div>
            <div>
              <span style={{ fontSize: "12px", fontWeight: 800, color: "#c084fc", background: "rgba(139,92,246,0.18)", padding: "4px 10px", borderRadius: "99px" }}>
                GÓI CHUYÊN NGHIỆP
              </span>
              <h3 style={{ fontSize: "22px", fontWeight: 800, color: "#fff", margin: "14px 0 6px" }}>Gói Chuyên Nghiệp</h3>
              <div style={{ fontSize: "32px", fontWeight: 900, color: "#c084fc", marginBottom: "14px" }}>
                369.000 đ <span style={{ fontSize: "14px", fontWeight: 500, color: "#94a3b8" }}>/ tháng (~12.000 đ/ngày)</span>
              </div>
              <p style={{ fontSize: "14px", color: "#94a3b8", lineHeight: 1.5, marginBottom: "20px" }}>
                Giải pháp đa kênh tăng trưởng toàn diện (Spa, Môi giới BĐS, F&B, Đào tạo nghề).
              </p>
              <ul style={{ listStyle: "none", padding: 0, margin: "0 0 24px 0", display: "flex", flexDirection: "column", gap: "10px", fontSize: "13.5px", color: "#cbd5e1" }}>
                <li>✓ <strong>Đa kênh:</strong> Facebook + Google Maps + TikTok Video</li>
                <li>✓ <strong>90 bài viết AI &amp; Video ngắn 9:16</strong> (Hook 3s giật tít)</li>
                <li>✓ <strong>AI Lead Agent:</strong> Tự động trích xuất SĐT/Tên khách hàng</li>
                <li>✓ <strong>Smart CRM Nudge:</strong> Gợi ý tin nhắn kéo khách cũ quay lại</li>
                <li>✓ Báo cáo doanh thu &amp; Đối soát POS</li>
              </ul>
            </div>
            <Link href="/signup" className={styles.ctaButton} style={{ width: "100%", justifyContent: "center" }}>
              Nâng cấp Gói Chuyên Nghiệp
            </Link>
          </div>
        </div>

        {/* Cash Flow Accelerator Banner (Đòn Bẩy Gói Năm) */}
        <div className={styles.glassCard} style={{ padding: "24px 36px", textAlign: "left", background: "linear-gradient(135deg, rgba(139,92,246,0.15), rgba(0,210,255,0.12))", borderColor: "rgba(139,92,246,0.4)", display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "20px", marginBottom: "60px" }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <span style={{ fontSize: "20px" }}>🎁</span>
              <span style={{ fontSize: "16px", fontWeight: 800, color: "#fff" }}>
                Ưu Đãi Đòn Bẩy Gói Năm (Tiết Kiệm Tối Đa)
              </span>
              <span style={{ fontSize: "11px", fontWeight: 800, background: "#10b981", color: "#fff", padding: "2px 8px", borderRadius: "6px" }}>
                TẶNG 3 THÁNG
              </span>
            </div>
            <p style={{ fontSize: "14px", color: "#cbd5e1", margin: "6px 0 0 0" }}>
              Thanh toán 1 năm: Tặng ngay 3 tháng sử dụng miễn phí + Tặng bộ 50 kịch bản Video TikTok chuyển đổi cao độc quyền từ Havi.
            </p>
          </div>
          <Link href="/signup" className={styles.ctaButton} style={{ whiteSpace: "nowrap" }}>
            Nhận Ưu Đãi Gói Năm
          </Link>
        </div>
      </section>

      {/* Nguyên Tắc Vận Hành */}
      <section id="nguyen-tac" className={styles.hero} style={{ paddingTop: "20px" }}>
        <div className={styles.sectionHeader}>
          <div className={styles.sectionTag} style={{ color: "#10b981" }}>CAM KẾT AN TOÀN</div>
          <h2 className={styles.sectionTitle}>Nguyên Tắc Xây Dựng Thương Hiệu Của Havi</h2>
          <p className={styles.sectionSubtitle}>Bảo vệ trọn vẹn uy tín của tiệm — Không bao giờ phát hành nội dung khi chưa được bạn duyệt.</p>
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
                Nhân viên AI Marketing Đa Kênh tự động cho mọi chủ tiệm &amp; doanh nghiệp. Tự động hóa bài viết Facebook, kịch bản TikTok Shorts, Google Maps SEO và trực Inbox 24/7.
              </p>
              <div className={styles.trustBadges}>
                <span className={styles.trustBadge}>🔒 Official Meta API</span>
                <span className={styles.trustBadge}>🇻🇳 Tiếng Việt Là Gốc</span>
                <span className={styles.trustBadge}>⚡ 100% Duyệt Trước</span>
              </div>
            </div>

            {/* Product Links */}
            <div>
              <div className={styles.footerColTitle}>SẢN PHẨM</div>
              <ul className={styles.footerLinkList}>
                <li><a href="#demo-studio">Studio Demo</a></li>
                <li><a href="#cach-hoat-dong">Cách hoạt động</a></li>
                <li><a href="#bang-gia">Bảng giá 10k/ngày</a></li>
                <li><a href="#nguyen-tac">Nguyên tắc cốt lõi</a></li>
              </ul>
            </div>

            {/* Industries */}
            <div>
              <div className={styles.footerColTitle}>NGÀNH NGHỀ</div>
              <ul className={styles.footerLinkList}>
                <li><a href="#demo-studio">Spa &amp; Thẩm Mỹ Viện</a></li>
                <li><a href="#demo-studio">Quán Ăn &amp; Cà Phê</a></li>
                <li><a href="#demo-studio">Môi Giới Bất Động Sản</a></li>
                <li><a href="#demo-studio">Kỹ Thuật &amp; Đào Tạo</a></li>
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
                <div>Email: <a href="mailto:hotro@havi.vn" style={{ color: "#38bdf8" }}>hotro@havi.vn</a></div>
                <div style={{ marginTop: "4px" }}>Thực chiến tại: <strong>Trung Tâm Công Nghệ Nhật Minh</strong></div>
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
    </div>
  );
}

