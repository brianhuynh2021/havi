"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/state-views";
import { useLanguage } from "@/lib/i18n/language-context";
import {
  changePlan,
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
  { title: string; price: string; period: string; desc: string; features: string[] }
> = {
  trial: {
    title: "Gói Trải Nghiệm",
    price: "0 đ",
    period: "14 ngày",
    desc: "Khám phá sức mạnh nhân viên AI marketing cho người mới bắt đầu.",
    features: [
      "50 bài viết AI & kịch bản video mỗi tháng",
      "Kết nối 1 Fanpage Facebook",
      "Lịch đăng bài tự động giờ vàng",
      "Hỗ trợ kỹ thuật 24/7",
    ],
  },
  tiem_nho: {
    title: "Gói Tiệm Đơn",
    price: "19.000 đ",
    period: "/tháng",
    desc: "Tối ưu nhất cho các tiệm Spa, Salon, F&B độc lập và môi giới BĐS.",
    features: [
      "250 bài viết AI & kịch bản video mỗi tháng",
      "Kết nối Facebook Page, Reels, TikTok & YouTube Shorts",
      "Sinh kịch bản video dọc với Hook 3s giật tít",
      "Hộp thư hợp nhất & Trả lời FAQ tự động",
      "Báo cáo khách tiềm năng & doanh thu POS",
    ],
  },
  toan_dien: {
    title: "Gói Chuỗi Tiệm",
    price: "29.000 đ",
    period: "/tháng",
    desc: "Dành cho chuỗi chi nhánh, salon và cửa hàng nhiều cơ sở.",
    features: [
      "1.000 bài viết AI & kịch bản video tốc độ cao",
      "Không giới hạn kết nối đa kênh mạng xã hội",
      "Ưu tiên tài nguyên AI & render video chất lượng cao",
      "Phân quyền nhân viên từng chi nhánh",
      "Chuyên viên hỗ trợ kỹ thuật 1-1 riêng biệt",
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

  // Polling trạng thái hoá đơn siêu tốc khi mở modal VietQR (1.2s phản hồi tức thì)
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
    }, 1200);

    return () => clearInterval(interval);
  }, [checkoutData, paymentSuccess]);

  async function handleOpenCheckout(plan: Plan) {
    setIsGeneratingCheckout(true);
    const res = await createCheckout(plan);
    setIsGeneratingCheckout(false);
    if (res.ok) {
      setCheckoutData(res.data);
    } else {
      // Fallback nếu API checkout local chưa cấu hình
      setUpgrading(true);
      const changeRes = await changePlan(plan);
      setUpgrading(false);
      if (changeRes.ok) {
        await reloadData();
      } else {
        alert(changeRes.message);
      }
    }
  }

  async function handleManualConfirm() {
    if (!checkoutData) return;
    setUpgrading(true);
    const res = await changePlan(checkoutData.plan);
    setUpgrading(false);
    if (res.ok) {
      await reloadData();
      setCheckoutData(null);
    } else {
      alert(res.message);
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
            <span>Hạn mức nội dung tháng này:</span>
            <span className={styles.quotaValue}>
              {sub.token_quota_used.toLocaleString("vi-VN")} /{" "}
              {sub.token_quota_limit.toLocaleString("vi-VN")} Lượt ({quotaPercent}%)
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
          const isPopular = planKey === "tiem_nho";

          return (
            <article
              key={planKey}
              className={`${styles.planCard} ${isPopular ? styles.planCardPopular : ""}`}
            >
              {isPopular ? <span className={styles.popularBadge}>Phổ biến nhất</span> : null}

              <div className={styles.planHeader}>
                <h3 className={styles.planTitle}>{plan.title}</h3>
                <p className={styles.planDescription}>{plan.desc}</p>
                <div className={styles.planPrice}>
                  <span className={styles.priceAmount}>{plan.price}</span>
                  <span className={styles.pricePeriod}>{plan.period}</span>
                </div>
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
                  Mở ứng dụng Ngân hàng (VCB, MB, Techcombank, VPBank…) quét mã QR 24/7 — Hệ thống tự động kích hoạt sau 3 giây.
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
                      <strong>{checkoutData.account_no}</strong>
                    </div>
                    <div className={styles.transferRow}>
                      <span>Chủ tài khoản:</span>
                      <span>{checkoutData.account_name}</span>
                    </div>
                    <div className={styles.transferRow}>
                      <span>Số tiền:</span>
                      <strong style={{ color: "#0284c7" }}>
                        {(checkoutData.amount_vnd ?? 0).toLocaleString("vi-VN")} đ
                      </strong>
                    </div>
                    <div className={styles.transferRow}>
                      <span>Nội dung CK:</span>
                      <strong style={{ color: "#f59e0b" }}>{checkoutData.transfer_content}</strong>
                    </div>
                  </div>
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
                    {upgrading ? "Đang kích hoạt…" : "Xác nhận đã chuyển khoản"}
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
