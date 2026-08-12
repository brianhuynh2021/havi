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
  { photo: string; text: string; tag: string }
> = {
  Facebook: {
    photo: "/images/hero_photo.jpg",
    text: "Tuần này Spa bên mình có ưu đãi cho 30 khách đặt sớm — nhắn tin qua Fanpage để giữ chỗ trước nha chị em!",
    tag: "Fanpage Post",
  },
  "Zalo OA": {
    photo: "/images/spa_photo.jpg",
    text: "Bản tin Zalo OA: Nhắc lịch tái khám & quà tặng serum độc quyền dành riêng cho khách hàng thân thiết trong tuần này.",
    tag: "Zalo Care",
  },
  "Google Business": {
    photo: "/images/cafe_photo.jpg",
    text: "Ghé trải nghiệm không gian và thưởng thức cà phê rang xay thơm nức tại tiệm — Đánh giá 5 sao nhận ngay voucher 20k!",
    tag: "Google Map Post",
  },
  "Bản tin Email": {
    photo: "/images/bds_photo.jpg",
    text: "[Báo giá mới nhất] Gửi anh/chị thông tin 3 căn nhà Q7 vị trí đẹp, giá đầu tư cực tốt kèm sổ hồng chính chủ.",
    tag: "Email Marketing",
  },
};

export function LandingScreen() {
  const [activeChannel, setActiveChannel] = useState("Facebook");
  const [emailInput, setEmailInput] = useState("");
  const [submittedEmail, setSubmittedEmail] = useState(false);

  const currentDraft = PREVIEW_DRAFTS[activeChannel] || PREVIEW_DRAFTS.Facebook;

  const handleEmailSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (emailInput.trim()) {
      setSubmittedEmail(true);
      setEmailInput("");
    }
  };

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.headerInner}>
          <Link href="/gioi-thieu" className={styles.brand}>
            <Logo size={38} />
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
          <p className={styles.eyebrow}>
            <span style={{ fontSize: "14px" }}>✨</span> Trợ lý AI Đa Kênh cho Tiệm & Người Thu Hút Traffic
          </p>
          <h1 className={styles.heroTitle}>
            Tải ảnh lên tiệm, bài đăng & Email sẵn sàng — bạn chỉ cần duyệt
          </h1>
          <p className={styles.heroBody}>
            Không cần giỏi văn hay am hiểu công nghệ. Chỉ cần gửi vài tấm ảnh
            hoặc 3 ý chính — Havi tự biên soạn bài viết đa kênh và email chăm
            sóc đúng giọng tiệm, bạn đọc lướt rồi bấm duyệt 1 chạm.
          </p>

          <div className={styles.heroActions}>
            <Link href="/dang-ky" className={styles.ctaPrimary}>
              Tạo tài khoản miễn phí
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path d="M5 12h14M12 5l7 7-7 7" />
              </svg>
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

        {/* Ảnh mô phỏng bản nháp chờ duyệt có chọn tab kênh & email */}
        <div className={styles.previewCard}>
          <div className={styles.previewBar}>
            <div className={styles.previewDots}>
              <span className={styles.previewDot} />
              <span className={styles.previewDot} />
              <span className={styles.previewDot} />
              <span className={styles.previewBarText}>Havi · Xem trước bài & Email</span>
            </div>
            <span className={styles.previewStatusBadge}>🟢 AI đang sẵn sàng</span>
          </div>
          <div className={styles.previewChannels}>
            {heroChannels.map((channel) => {
              const isActive = activeChannel === channel.n;
              return (
                <button
                  key={channel.n}
                  type="button"
                  onClick={() => setActiveChannel(channel.n)}
                  className={styles.previewChannel}
                  style={{
                    borderColor: isActive ? channel.c : "#e6ddd5",
                    background: isActive ? `${channel.c}10` : "#fff",
                    color: isActive ? channel.c : "#1f1b18",
                    cursor: "pointer",
                  }}
                >
                  <span
                    className={styles.previewChannelDot}
                    style={{ background: channel.c }}
                  />
                  {channel.n}
                </button>
              );
            })}
          </div>
          <div className={styles.previewBody}>
            <div className={styles.previewPhoto}>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={currentDraft.photo}
                alt="Minh hoạ xem trước nội dung"
                className={styles.previewImage}
              />
            </div>
            <div>
              <div style={{ fontSize: "11px", fontWeight: 700, color: "#c86d3b", marginBottom: "4px" }}>
                🏷️ {currentDraft.tag}
              </div>
              <p className={styles.previewText}>{currentDraft.text}</p>
              <div className={styles.previewActions}>
                <span className={styles.previewApprove}>Duyệt bài này</span>
                <span className={styles.previewEdit}>Sửa lại giọng văn</span>
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
              Từ tấm ảnh chụp vội hay ý tưởng ngắn đến bài đăng & Email hoàn chỉnh — Havi xử lý thông minh để bạn tập trung làm nghề.
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
            <h2 className={styles.sectionTitle}>Havi thiết kế cho đa dạng ngành & Traffic Builder</h2>
            <p className={styles.sectionSub}>
              Từ tiệm làm đẹp, bất động sản, nhà hàng cà phê đến người bán hàng online — Havi tự động chuyển đổi hình ảnh & ý tưởng thành bài viết chuẩn vị & email hấp dẫn.
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
                {industry.image && (
                  <div className={styles.industryThumb}>
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={industry.image}
                      alt={industry.name}
                      className={styles.industryImg}
                    />
                  </div>
                )}
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

          {/* Form nhận tin tức & Mẹo Traffic qua Email */}
          <div className={styles.emailCaptureSection}>
            <h3 className={styles.emailCaptureTitle}>
              📬 Nhận bộ Mẫu Content & Kinh nghiệm kéo Traffic qua Email
            </h3>
            <p className={styles.emailCaptureSub}>
              Đăng ký email để nhận bộ 30 mẫu bài đăng & email chào hàng cho từng ngành, kèm thông báo sớm nhất khi Havi mở đợt dùng thử tiếp theo.
            </p>
            {submittedEmail ? (
              <div className={styles.emailSuccessMsg}>
                🎉 Cảm ơn bạn! Havi đã ghi nhận email và sẽ gửi tài liệu qua hòm thư cho bạn nhé.
              </div>
            ) : (
              <form onSubmit={handleEmailSubmit} className={styles.emailCaptureForm}>
                <input
                  type="email"
                  placeholder="Nhập email của bạn (ví dụ: chu-tiem@gmail.com)"
                  value={emailInput}
                  onChange={(e) => setEmailInput(e.target.value)}
                  className={styles.emailCaptureInput}
                  required
                />
                <button type="submit" className={styles.emailCaptureBtn}>
                  Nhận qua Email
                </button>
              </form>
            )}
          </div>
        </div>
      </section>

      <section id="nguyen-tac" className={styles.sectionAlt}>
        <div className={styles.sectionInner}>
          <div className={styles.sectionHead}>
            <h2 className={styles.sectionTitle}>Havi làm việc có nguyên tắc</h2>
            <p className={styles.sectionSub}>
              Uy tín kinh doanh của bạn là tài sản quý giá nhất — Havi bảo vệ nó trong từng câu chữ.
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
            Chúng tôi đang mời một nhóm nhỏ chủ tiệm, môi giới BĐS & người làm nội dung dùng thử và góp ý. Tạo tài
            khoản để bắt đầu — chưa thu phí trong giai đoạn này.
          </p>
          <Link href="/dang-ky" className={styles.ctaBandButton}>
            Tạo tài khoản miễn phí
          </Link>
          <p className={styles.ctaNote}>
            Bảng giá sẽ công bố sau khi kết thúc giai đoạn thử nghiệm.
          </p>
        </div>
      </section>

      <footer className={styles.footer}>
        <div className={styles.footerInner}>
          <div>
            <div className={styles.brand}>
              <Logo size={34} tone="dark" />
              <span className={styles.footerBrandText}>Havi</span>
            </div>
            <p className={styles.footerBlurb}>
              Trợ lý marketing AI đa kênh & email cho hộ kinh doanh, người thu hút traffic và doanh nghiệp tại Việt Nam.
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
