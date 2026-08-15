"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/state-views";
import { useLanguage } from "@/lib/i18n/language-context";
import {
  changePlan,
  fetchInvoices,
  fetchSubscription,
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
    desc: "Khám phá sức mạnh marketing AI cho người mới bắt đầu.",
    features: [
      "50.000 Token AI mỗi tháng",
      "Kết nối 1 Fanpage Facebook",
      "Lịch đăng bài tự động giờ vàng",
      "Hỗ trợ qua tài liệu & cộng đồng",
    ],
  },
  tiem_nho: {
    title: "Gói Tiệm Đơn",
    price: "299.000 đ",
    period: "/tháng",
    desc: "Tối ưu nhất cho các tiệm Spa, Salon, F&B độc lập.",
    features: [
      "250.000 Token AI mỗi tháng",
      "Kết nối Facebook Page, Reels, TikTok & YouTube Shorts",
      "Sinh kịch bản video dọc với Hook 3s",
      "Hộp thư hợp nhất & Trả lời FAQ tự động",
      "Báo cáo khách tiềm năng & doanh thu",
    ],
  },
  toan_dien: {
    title: "Gói Chuỗi Tiệm",
    price: "799.000 đ",
    period: "/tháng",
    desc: "Dành cho chuỗi chi nhánh và cửa hàng nhiều cơ sở.",
    features: [
      "1.000.000 Token AI tốc độ cao",
      "Không giới hạn kết nối đa kênh",
      "Ưu tiên tài nguyên AI & render video",
      "Phân quyền nhân viên chi nhánh",
      "Hỗ trợ kỹ thuật 1-1 chuyên biệt",
    ],
  },
};

export function BillingScreen() {
  const { t } = useLanguage();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sub, setSub] = useState<Subscription | null>(null);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [selectedPlanForPayment, setSelectedPlanForPayment] = useState<Plan | null>(null);
  const [upgrading, setUpgrading] = useState(false);

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

  async function handleConfirmUpgrade(plan: Plan) {
    setUpgrading(true);
    const res = await changePlan(plan);
    setUpgrading(false);
    if (res.ok) {
      setSub(res.data);
      setSelectedPlanForPayment(null);
      // Reload invoices
      const invRes = await fetchInvoices();
      if (invRes.ok) setInvoices(invRes.data);
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
          Quản lý gói dịch vụ AI marketing, theo dõi hạn mức sử dụng và lịch sử thanh toán minh bạch.
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
            <span>Hạn mức Token AI tháng này:</span>
            <span className={styles.quotaValue}>
              {sub.token_quota_used.toLocaleString("vi-VN")} /{" "}
              {sub.token_quota_limit.toLocaleString("vi-VN")} Tokens ({quotaPercent}%)
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
                    onClick={() => setSelectedPlanForPayment(planKey)}
                  >
                    Nâng cấp lên {plan.title}
                  </button>
                )}
              </div>
            </article>
          );
        })}
      </section>

      {/* Invoices History */}
      <section className={styles.invoicesSection}>
        <h2 className={styles.invoicesTitle}>📜 Lịch sử hóa đơn & Thanh toán</h2>
        {invoices.length === 0 ? (
          <EmptyState
            title="Chưa có hóa đơn nào phát sinh"
            body="Khi bạn đăng ký hoặc nâng cấp gói cước, hóa đơn điện tử sẽ hiển thị tại đây."
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
                        {inv.status === "paid" ? "Đã thanh toán" : "Đã kích hoạt"}
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
      {selectedPlanForPayment ? (
        <div
          className={styles.modalOverlay}
          onClick={(e) => {
            if (e.target === e.currentTarget) setSelectedPlanForPayment(null);
          }}
        >
          <div className={styles.modalCard} role="dialog" aria-modal="true">
            <h3 style={{ fontSize: 20, fontWeight: 800, color: "#0f172a" }}>
              Quét mã VietQR để nâng cấp {PLAN_DETAILS[selectedPlanForPayment as keyof typeof PLAN_DETAILS]?.title}
            </h3>
            <p style={{ fontSize: 13.5, color: "#64748b" }}>
              Chuyển khoản liên ngân hàng NAPAS 24/7 tự động kích hoạt gói cước ngay lập tức.
            </p>

            <div className={styles.qrBox}>
              <img
                src={`https://img.vietqr.io/image/970436-1025888888-compact2.png?amount=${
                  selectedPlanForPayment === "tiem_nho" ? 299000 : 799000
                }&addInfo=HAVI%20${sub.workspace_id.slice(0, 8)}&accountName=CONG%20TY%20HAVI%20VIETNAM`}
                alt="VietQR Payment Code"
                className={styles.qrImage}
              />
              <div className={styles.transferDetails}>
                <div className={styles.transferRow}>
                  <span>Ngân hàng:</span>
                  <span>Vietcombank (VCB)</span>
                </div>
                <div className={styles.transferRow}>
                  <span>Số tài khoản:</span>
                  <strong>1025888888</strong>
                </div>
                <div className={styles.transferRow}>
                  <span>Chủ tài khoản:</span>
                  <span>CONG TY HAVI VIETNAM</span>
                </div>
                <div className={styles.transferRow}>
                  <span>Số tiền:</span>
                  <strong>
                    {(selectedPlanForPayment === "tiem_nho" ? 299000 : 799000).toLocaleString("vi-VN")} đ
                  </strong>
                </div>
                <div className={styles.transferRow}>
                  <span>Nội dung CK:</span>
                  <strong>HAVI {sub.workspace_id.slice(0, 8)}</strong>
                </div>
              </div>
            </div>

            <div style={{ display: "flex", gap: 12, justifyContent: "flex-end" }}>
              <Button variant="ghost" onClick={() => setSelectedPlanForPayment(null)}>
                Đóng
              </Button>
              <Button
                variant="primary"
                disabled={upgrading}
                onClick={() => handleConfirmUpgrade(selectedPlanForPayment)}
              >
                {upgrading ? "Đang xử lý…" : "Tôi đã chuyển khoản thành công"}
              </Button>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}
