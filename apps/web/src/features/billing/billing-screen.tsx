"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/state-views";
import { useLanguage } from "@/lib/i18n/language-context";
import {
  checkInvoiceStatus,
  createCheckout,
  fetchInvoices,
  fetchSubscription,
  type CheckoutData,
  type Invoice,
  type Plan,
  type Subscription,
} from "./billing.api";
import styles from "./billing.module.css";

const PLAN_DETAILS: Record<
  Plan,
  {
    title: string;
    price: string;
    period: string;
    dailyNote: string;
    badge: string | null;
    badgeTone: "popular" | "featured" | "enterprise" | null;
    desc: string;
    features: string[];
  }
> = {
  trial: {
    title: "Gói Trải Nghiệm",
    price: "0 đ",
    period: "/ 7 ngày",
    dailyNote: "Miễn phí 100% · Không cần thẻ",
    badge: null,
    badgeTone: null,
    desc: "Trải nghiệm toàn diện quy trình sáng tạo, duyệt bài Fanpage và chăm sóc inbox bằng AI.",
    features: [
      "7 ngày dùng thử đầy đủ tính năng",
      "100.000 token AI (~30 bài viết & kịch bản)",
      "Tạo & lên lịch bài đăng Fanpage Facebook",
      "Máy nhắc chữ Teleprompter quay video ngắn 9:16",
      "Gợi ý phản hồi Messenger & lưu khách quan tâm",
    ],
  },
  tiem_nho: {
    title: "Gói Khởi Nghiệp",
    price: "189.000 đ",
    period: "/ tháng",
    dailyNote: "Chỉ ~6.000 đ/ngày",
    badge: "TIẾT KIỆM NHẤT",
    badgeTone: "popular",
    desc: "Giải pháp tự động hóa nội dung và chăm sóc khách hàng tiết kiệm cho tiệm đơn lẻ.",
    features: [
      "500.000 token AI mỗi tháng (~150 bài viết)",
      "Đăng bài và lên lịch Fanpage Facebook tự động",
      "AI Video Studio: Tạo hook 3s & kịch bản video ngắn",
      "Trực Inbox Messenger & tự động nhận diện SĐT",
      "Lộ trình mục tiêu 7-30 ngày dẫn dắt từng bước",
    ],
  },
  toan_dien: {
    title: "Gói Chuyên Nghiệp",
    price: "369.000 đ",
    period: "/ tháng",
    dailyNote: "Chỉ ~12.000 đ/ngày",
    badge: "PHỔ BIẾN NHẤT 💎",
    badgeTone: "featured",
    desc: "Tối ưu hóa chuyển đổi và mở rộng lượng khách địa phương đến cơ sở mỗi tuần.",
    features: [
      "2.000.000 token AI mỗi tháng (Thoải mái sáng tạo)",
      "Full tính năng AI Video Studio & Máy nhắc chữ",
      "CRM Lead Care: Quét & gợi ý tin nhắn kéo khách cũ",
      "Báo cáo tăng trưởng & phân tích hiệu quả kênh",
      "Ưu tiên tài nguyên xử lý AI & Hỗ trợ kỹ thuật 1-1",
    ],
  },
  doanh_nghiep: {
    title: "Chuỗi Doanh Nghiệp",
    price: "799.000 đ",
    period: "/ tháng",
    dailyNote: "Chỉ ~26.000 đ/ngày",
    badge: "QUY MÔ CHUỖI 👑",
    badgeTone: "enterprise",
    desc: "Dành cho cơ sở quy mô lớn hoặc chuỗi cần lưu lượng nội dung và hỗ trợ tối đa.",
    features: [
      "5.000.000 token AI mỗi tháng (Hạn mức cao nhất)",
      "Không giới hạn chiến dịch & kịch bản video",
      "Trọn bộ năng lực AI Content, Video Studio, Inbox & CRM",
      "Hỗ trợ triển khai trực tiếp cùng Founder & Đội ngũ",
      "Xuất hóa đơn VAT điện tử & Tùy biến Brand Voice",
    ],
  },
};

export function BillingScreen() {
  const { t } = useLanguage();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sub, setSub] = useState<Subscription | null>(null);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [checkoutData, setCheckoutData] = useState<CheckoutData | null>(null);
  const [isGeneratingCheckout, setIsGeneratingCheckout] = useState(false);
  const [upgrading, setUpgrading] = useState(false);
  const [paymentSuccess, setPaymentSuccess] = useState(false);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [checkoutError, setCheckoutError] = useState<string | null>(null);
  const [verifyNotice, setVerifyNotice] = useState<string | null>(null);

  const handleCopy = (key: string, value: string) => {
    try {
      void navigator.clipboard.writeText(value);
      setCopiedKey(key);
      setTimeout(() => {
        setCopiedKey((curr) => (curr === key ? null : curr));
      }, 2000);
    } catch {
      // ignore
    }
  };

  const reloadData = async () => {
    const [subRes, invRes] = await Promise.all([
      fetchSubscription(),
      fetchInvoices(),
    ]);
    if (subRes.ok) setSub(subRes.data);
    if (invRes.ok) setInvoices(invRes.data);
  };

  useEffect(() => {
    let active = true;
    async function load() {
      setLoading(true);
      const [subRes, invRes] = await Promise.all([
        fetchSubscription(),
        fetchInvoices(),
      ]);
      if (!active) return;
      if (!subRes.ok) {
        setError(subRes.message);
      } else {
        setSub(subRes.data);
        setError(null);
      }
      if (invRes.ok) {
        setInvoices(invRes.data);
      }
      setLoading(false);
    }
    void load();
    return () => {
      active = false;
    };
  }, []);

  // Polling trạng thái hoá đơn chuẩn mực khi mở modal VietQR (1.0s - 1000ms)
  useEffect(() => {
    if (!checkoutData?.invoice_id || paymentSuccess) return;

    const interval = setInterval(async () => {
      const res = await checkInvoiceStatus(checkoutData.invoice_id);
      if (res.ok && res.data.status === "paid") {
        setPaymentSuccess(true);
        clearInterval(interval);
        setTimeout(async () => {
          await reloadData();
          setCheckoutData(null);
          setPaymentSuccess(false);
        }, 1200);
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [checkoutData, paymentSuccess]);

  async function handleOpenCheckout(plan: Plan) {
    setCheckoutError(null);
    setVerifyNotice(null);
    setIsGeneratingCheckout(true);
    const res = await createCheckout(plan);
    setIsGeneratingCheckout(false);
    if (res.ok) {
      setCheckoutData(res.data);
    } else {
      setCheckoutError(res.message || "Không thể khởi tạo mã VietQR lúc này. Vui lòng thử lại sau giây lát.");
    }
  }

  async function handleManualConfirm() {
    if (!checkoutData) return;
    setVerifyNotice(null);
    setUpgrading(true);
    const res = await checkInvoiceStatus(checkoutData.invoice_id);
    setUpgrading(false);
    if (res.ok && res.data.status === "paid") {
      setPaymentSuccess(true);
      setTimeout(async () => {
        await reloadData();
        setCheckoutData(null);
        setPaymentSuccess(false);
      }, 1200);
    } else {
      setVerifyNotice(
        "Hệ thống đang chờ tín hiệu đối soát từ Ngân hàng. " +
        "Sau khi bạn chuyển khoản đúng số tiền và nội dung, gói cước sẽ tự động kích hoạt trong vòng vài giây. " +
        "Nếu đã chuyển khoản nhưng chưa thấy kích hoạt, vui lòng liên hệ Hotline/Zalo: 0984 883 750."
      );
    }
  }

  if (loading) {
    return <LoadingState title="Đang tải thông tin gói cước…" />;
  }

  if (error || !sub) {
    return (
      <ErrorState
        title={error ?? "Không thể tải gói cước"}
        action={
          <Button variant="outline" onClick={() => window.location.reload()}>
            Thử lại
          </Button>
        }
      />
    );
  }

  const quotaPercent = Math.min(
    100,
    Math.round((sub.token_quota_used / Math.max(1, sub.token_quota_limit)) * 100),
  );

  const currentPlan = sub.plan as keyof typeof PLAN_DETAILS;

  return (
    <>
      <header className={styles.header}>
        <div className={styles.titleRow}>
          <h1 className={styles.title}>{t("nav.billing", "Gói Cước & Thanh Toán")}</h1>
          <Badge tone={sub.status === "active" ? "success" : "warning"}>
            Trạng thái: {sub.status === "active" ? "Đang hoạt động" : sub.status}
          </Badge>
        </div>
        <p className={styles.subtitle}>
          Quản lý gói dịch vụ nhân viên AI marketing, theo dõi số lượt bài đăng và lịch sử thanh toán VietQR minh bạch.
        </p>
      </header>

      {checkoutError && (
        <div style={{ margin: "16px 0", padding: "12px 16px", borderRadius: "10px", background: "rgba(239, 68, 68, 0.1)", border: "1px solid rgba(239, 68, 68, 0.3)", color: "#f87171", fontSize: "14px" }}>
          ⚠️ {checkoutError}
        </div>
      )}

      {/* Quota Telemetry Card */}
      <section className={styles.currentStatusCard}>
        <div className={styles.statusTop}>
          <div className={styles.statusPlanName}>
            <span>💎 {PLAN_DETAILS[currentPlan]?.title ?? sub.plan}</span>
            <Badge tone="primary">Gói hiện tại</Badge>
          </div>
          {sub.current_period_end ? (
            <span className={styles.periodDate}>
              📅 Hạn chu kỳ: {new Date(sub.current_period_end).toLocaleDateString("vi-VN")}
            </span>
          ) : null}
        </div>

        <div className={styles.quotaBarContainer}>
          <div className={styles.quotaLabels}>
            <span>Hạn mức token AI tháng này:</span>
            <span className={styles.quotaValue}>
              {sub.token_quota_used.toLocaleString("vi-VN")} /{" "}
              {sub.token_quota_limit.toLocaleString("vi-VN")} token ({quotaPercent}%)
            </span>
          </div>
          <div className={styles.progressBarBg}>
            <div
              className={styles.progressBarFill}
              style={{ width: `${quotaPercent}%` }}
            />
          </div>
        </div>
      </section>

      {/* Pricing Grid */}
      <section className={styles.plansGrid} aria-label="Bảng giá các gói cước">
        {(Object.keys(PLAN_DETAILS) as Plan[]).map((planKey) => {
          const plan = PLAN_DETAILS[planKey as keyof typeof PLAN_DETAILS];
          if (!plan) return null;
          const isCurrent = sub.plan === planKey;
          const isFeatured = plan.badgeTone === "featured";
          const isPopular = plan.badgeTone === "popular";
          const isEnterprise = plan.badgeTone === "enterprise";

          return (
            <article
              key={planKey}
              className={`${styles.planCard} ${isEnterprise ? styles.planCardEnterprise : isFeatured ? styles.planCardFeatured : isPopular ? styles.planCardPopular : ""}`}
            >
              {plan.badge ? (
                <span
                  className={
                    isEnterprise
                      ? styles.enterpriseBadge
                      : isFeatured
                      ? styles.featuredBadge
                      : styles.popularBadge
                  }
                >
                  {plan.badge}
                </span>
              ) : null}

              <div className={styles.planHeader}>
                <h3 className={styles.planTitle}>{plan.title}</h3>
                <p className={styles.planDescription}>{plan.desc}</p>
                <div className={styles.planPrice}>
                  <span className={styles.priceAmount}>{plan.price}</span>
                  <span className={styles.pricePeriod}>{plan.period}</span>
                </div>
                {plan.dailyNote ? (
                  <div className={styles.priceDailyTag}>⚡ {plan.dailyNote}</div>
                ) : null}
              </div>

              <ul className={styles.featuresList}>
                {plan.features.map((f, idx) => (
                  <li key={idx} className={styles.featureItem}>
                    <span className={styles.featureCheck}>✓</span>
                    <span>{f}</span>
                  </li>
                ))}
              </ul>

              <div>
                {isCurrent ? (
                  <button type="button" className={`${styles.planButton} ${styles.currentPlanBtn}`} disabled>
                    ✓ Đang sử dụng
                  </button>
                ) : (
                  <button
                    type="button"
                    className={`${styles.planButton} ${styles.upgradeBtn}`}
                    disabled={isGeneratingCheckout}
                    onClick={() => handleOpenCheckout(planKey)}
                  >
                    {isGeneratingCheckout ? "Đang tạo mã VietQR…" : `Nâng cấp lên ${plan.title}`}
                  </button>
                )}
              </div>
            </article>
          );
        })}
      </section>

      <p className={styles.billingDisclaimer} style={{ textAlign: "center", color: "var(--text-secondary)", fontSize: "13px", margin: "16px 0 28px" }}>
        * Không bao gồm cam kết số bài, lead hoặc doanh thu; kết quả phụ thuộc vào hoạt động kinh doanh và dịch vụ thực tế tại cơ sở.
      </p>

      {/* Invoices History */}
      <section className={styles.invoicesSection}>
        <h2 className={styles.invoicesTitle}>📜 Lịch sử hóa đơn & Thanh toán VietQR</h2>
        {invoices.length === 0 ? (
          <EmptyState
            title="Chưa có hóa đơn nào phát sinh"
            body="Khi bạn đăng ký hoặc nâng cấp gói cước, hóa đơn điện tử và mã giao dịch sẽ hiển thị tại đây."
          />
        ) : (
          <div className={styles.invoicesCard}>
            <table className={styles.invoicesTable}>
              <thead>
                <tr>
                  <th>Mã hóa đơn</th>
                  <th>Gói cước</th>
                  <th>Số tiền</th>
                  <th>Ngày tạo</th>
                  <th>Trạng thái</th>
                </tr>
              </thead>
              <tbody>
                {invoices.map((inv) => (
                  <tr key={inv.id}>
                    <td><code>#{inv.id.slice(0, 8)}</code></td>
                    <td><strong>{PLAN_DETAILS[inv.plan as keyof typeof PLAN_DETAILS]?.title ?? inv.plan}</strong></td>
                    <td>{inv.amount_vnd.toLocaleString("vi-VN")} đ</td>
                    <td>{new Date(inv.issued_at).toLocaleDateString("vi-VN")}</td>
                    <td>
                      <Badge tone={inv.status === "paid" ? "success" : "info"}>
                        {inv.status === "paid" ? "✓ Đã thanh toán" : "Đang chờ thanh toán"}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Modal VietQR Payment */}
      {checkoutData ? (
        <div
          className={styles.modalOverlay}
          onClick={(e) => {
            if (e.target === e.currentTarget) setCheckoutData(null);
          }}
        >
          <div className={styles.modalCard} role="dialog" aria-modal="true">
            {paymentSuccess ? (
              <div style={{ textAlign: "center", padding: "24px 0" }}>
                <div style={{ fontSize: 54 }}>🎉</div>
                <h3 style={{ fontSize: 22, fontWeight: 800, color: "#10b981", marginTop: 12 }}>
                  Thanh Toán Thành Công!
                </h3>
                <p style={{ color: "#64748b", marginTop: 8 }}>
                  Tài khoản của bạn đã được tự động nâng cấp. Đang chuyển hướng…
                </p>
              </div>
            ) : (
              <>
                <h3 style={{ fontSize: 20, fontWeight: 800, color: "#0f172a" }}>
                  Quét mã VietQR để nâng cấp {PLAN_DETAILS[checkoutData.plan]?.title}
                </h3>
                <p style={{ fontSize: 13.5, color: "#64748b" }}>
                  Mở ứng dụng ngân hàng và quét mã QR. Gói chỉ được kích hoạt sau khi Havi nhận và xác minh webhook thanh toán.
                </p>

                <div className={styles.qrBox}>
                  <img
                    src={checkoutData.qr_code_url}
                    alt="VietQR Payment Code"
                    className={styles.qrImage}
                  />
                  <div className={styles.transferDetails}>
                    <div className={styles.transferRow}>
                      <span>Ngân hàng:</span>
                      <strong>{checkoutData.bank_id}</strong>
                    </div>
                    <div className={styles.transferRow}>
                      <span>Số tài khoản:</span>
                      <div className={styles.valueWithCopy}>
                        <strong>{checkoutData.account_no}</strong>
                        <button
                          type="button"
                          className={`${styles.copyBtn} ${copiedKey === "account_no" ? styles.copyBtnSuccess : ""}`}
                          onClick={() => handleCopy("account_no", checkoutData.account_no)}
                        >
                          {copiedKey === "account_no" ? "✓ Đã chép" : "Sao chép"}
                        </button>
                      </div>
                    </div>
                    <div className={styles.transferRow}>
                      <span>Chủ tài khoản:</span>
                      <span>{checkoutData.account_name}</span>
                    </div>
                    <div className={styles.transferRow}>
                      <span>Số tiền:</span>
                      <div className={styles.valueWithCopy}>
                        <strong style={{ color: "#0284c7" }}>
                          {(checkoutData.amount_vnd ?? 0).toLocaleString("vi-VN")} đ
                        </strong>
                        <button
                          type="button"
                          className={`${styles.copyBtn} ${copiedKey === "amount" ? styles.copyBtnSuccess : ""}`}
                          onClick={() => handleCopy("amount", String(checkoutData.amount_vnd ?? 0))}
                        >
                          {copiedKey === "amount" ? "✓ Đã chép" : "Sao chép"}
                        </button>
                      </div>
                    </div>
                    <div className={styles.transferRow}>
                      <span>Nội dung CK:</span>
                      <div className={styles.valueWithCopy}>
                        <strong style={{ color: "#d97706" }}>{checkoutData.transfer_content}</strong>
                        <button
                          type="button"
                          className={`${styles.copyBtn} ${copiedKey === "content" ? styles.copyBtnSuccess : ""}`}
                          onClick={() => handleCopy("content", checkoutData.transfer_content)}
                        >
                          {copiedKey === "content" ? "✓ Đã chép" : "Sao chép"}
                        </button>
                      </div>
                    </div>
                  </div>
                </div>

                {verifyNotice && (
                  <div style={{ marginTop: 12, padding: "10px 14px", borderRadius: "8px", background: "rgba(245, 158, 11, 0.1)", border: "1px solid rgba(245, 158, 11, 0.25)", color: "#b45309", fontSize: "13px", lineHeight: 1.5 }}>
                    ⏳ {verifyNotice}
                  </div>
                )}

                <div style={{ marginTop: 12, fontSize: "12.5px", color: "var(--color-muted)", textAlign: "center" }}>
                  Cần hỗ trợ thanh toán hoặc kích hoạt gấp? Hotline / Zalo Founder: <a href="tel:0984883750" style={{ color: "#0066ff", fontWeight: 700 }}>0984 883 750</a>
                </div>

                <div style={{ display: "flex", gap: 12, justifyContent: "flex-end", marginTop: 16 }}>
                  <Button variant="ghost" onClick={() => setCheckoutData(null)}>
                    Đóng
                  </Button>
                  <Button
                    variant="primary"
                    disabled={upgrading}
                    onClick={handleManualConfirm}
                  >
                    {upgrading ? "Đang kiểm tra…" : "Kiểm tra trạng thái"}
                  </Button>
                </div>
              </>
            )}
          </div>
        </div>
      ) : null}
    </>
  );
}
