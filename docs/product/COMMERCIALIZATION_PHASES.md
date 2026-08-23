# Havi Commercialization & Scale Master Plan (5 Phases)

> **Document Type:** Strategic Product & Engineering Roadmap  
> **Target Audience:** Founders, Lead Engineers, Growth Marketers  
> **Methodology:** MIT Clean Hexagonal Systems Rigor + Stanford HCI & Product-Led Growth (PLG)

---

## Executive Summary

Havi is positioned as a **Local Customer-to-Visit OS & Continuous Digital Presence Backbone** that sells **outcomes, peace of mind, and continuous brand vitality**, not complex self-service prompt tools. While early utility frees business owners and HR teams from 2–3 hours of daily manual posting and messaging fatigue, the core enterprise value stems from:
1. **Continuous Brand Vitality & Credibility:** Keeping social channels active and professionally maintained every single day without hiring expensive marketing staff.
2. **Universal Applicability Across Segments:** Serving Local Training Centers (Customer Zero: **Nhật Minh**), Corporate HR/Recruitment Fanpages, Resorts & Hospitality, Clinics, and Professional Service SMBs.
3. **Closed-Loop Conversion & Revenue Ledger:** Transforming social interactions into verified appointments, in-person visits, candidate submissions, and attributed revenue.

This document outlines the **5 strategic evolution phases** to scale Havi from local dogfooding at **Trung Tâm Công Nghệ Nhật Minh** to a globally scalable SaaS platform.

---

## 5-Phase Strategic Evolution Matrix

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        HAVI 5-PHASE COMMERCIAL SCALE MATRIX                            │
├───────────────────┬───────────────────┬───────────────────┬───────────────────┬────────┤
│ PHASE 1 (Month 1) │ PHASE 2 (Month 2) │ PHASE 3 (Month 3) │ PHASE 4 (Month 4) │ PHASE 5│
│ Facebook Beta Core│ YouTube Shorts    │ Google Business   │ TikTok Growth     │ In-App │
│ Hoàn Thiện Meta   │ Video Bằng Chứng  │ Maps Local SEO    │ Video & Lead Ingest│ Ads OS │
│ Kiếm Tiền & Gọi Vốn│ 0 đồng           │ Chặn nhu cầu cao  │ Mở rộng tệp trẻ   │ 1-Click│
└───────────────────┴───────────────────┴───────────────────┴───────────────────┴────────┘
```

---

## Phase 1: Facebook Beta Mastery & Monetization Core (Month 1)

### 1. Objective
Hoàn thiện 100% vòng lặp chuyển đổi trên hệ sinh thái Meta (Facebook Fanpage, Reels, Messenger), đóng toàn bộ 7 lỗi P0, đạt chuẩn 100% test tự động để **đưa ra ngoài kiếm tiền thực tế từ đối tác hoặc gọi vốn (Fundraising)** dựa trên số liệu tăng trưởng và chuyển đổi thật.

### 2. Core Capabilities
* **Hoàn Thiện 100% Facebook Fanpage & Reels:** Đăng bài tự động, video Reels 9:16 có hook 3s, lưu `external_post_id`, chống đăng trùng khi timeout mạng (`PENDING_RECONCILIATION`).
* **Live Meta Outbound Reply Dispatch:** Gửi tin nhắn Messenger thật qua Meta Graph API (`POST /v21.0/me/messages`), lưu PSID `recipient_id`, cấp quyền `pages_messaging`, chuyển `SENT` chỉ khi có `external_reply_id`.
* **Lead Care & Chuỗi Nhắc Lịch 3 Chạm:** AI tự động bóc SĐT từ inbox $\rightarrow$ báo Telegram tức thì $\rightarrow$ xác nhận lịch Open Class $\rightarrow$ tự động gửi tin nhắn nhắc lịch (ngay khi đặt, trước 24h, trước 3h) để triệt tiêu no-show.
* **Xác Minh Khách Đến & Doanh Thu Thật:** Nhân viên/giảng viên bấm Check-in 1-chạm trên mobile $\rightarrow$ Học viên chuyển khoản học phí VietQR $\rightarrow$ Khép kín dòng tiền.
* **Bảo Mật Tiền Tệ PayOS/VietQR:** Chống replay attack, khóa hàng transaction (`with_for_update`), xác thực chữ ký HMAC-SHA256 chuẩn PayOS.
* **Customer Zero Dogfooding:** Vận hành thực chiến 30 ngày tại **Trung Tâm Công Nghệ Nhật Minh**.

### 3. Economics & Target KPIs (Mục tiêu thương mại & Gọi vốn)
* **Pricing Tiers:** Khởi Nghiệp (299,000 VND/tháng) | Chuyên Nghiệp (599,000 VND/tháng).
* **Mục tiêu Customer Zero & Design Partners:**
  * $\ge 30$ lead đủ điều kiện từ bài đăng Facebook organic.
  * $\ge 10$ học viên đến trải nghiệm thực tế (Verified Visits).
  * $\ge 3$ học viên đóng học phí với 100% attribution rõ nguồn.
  * 5–10 Design Partners trả phí thử nghiệm có Founder giám sát 1-1.
  * 0 false publish/reply/payment successes.
* **North Star Metric:** **Số lượt khách đến đã xác minh mỗi tuần trên mỗi doanh nghiệp hoạt động (Verified Visits / active business / week)**.

---

## Phase 2: YouTube Shorts & Video Evidence Studio (Month 2)

### 1. Objective
Mở rộng kênh video bằng chứng sang **YouTube Shorts & YouTube Video**, khai thác thuật toán đề xuất video của Google để kéo học viên/khách hàng có nhu cầu học nghề và kỹ thuật.

### 2. Core Capabilities
* **YouTube Shorts Publisher:** Đăng tải tự động video ngắn thực hành lab/lớp học lên kênh YouTube của cơ sở.
* **Gắn CTA Chuyển Đổi:** Tự động đính kèm liên kết đăng ký Open Class và hotline trong phần mô tả và bình luận ghim.
* **Video Studio Hỗ Trợ:** Hỗ trợ cắt clip, kiểm tra tỷ lệ khung hình 9:16 và safe zone trước khi xuất bản.

### 3. Economics & Target KPIs
* **Target:** 30–50 active paying workspaces.
* **Target MRR:** 15,000,000 – 30,000,000 VND.

---

## Phase 3: Google Business Profile & Local Maps SEO (Month 3)

### 1. Objective
Chặn trọn vẹn tệp khách hàng có ý định tìm kiếm cao (High-Intent Search) tại địa phương qua Google Maps SEO và Google Business Profile.

### 2. Core Capabilities
* **Google Business Profile Event/Offer Posts:** Tự động lên lịch đăng các sự kiện Open Lab và ưu đãi học phí lên Google Maps.
* **Local SEO Ranker & Review Responder:** Tự động gợi ý phản hồi đánh giá chuẩn từ khóa địa phương để tăng thứ hạng tìm kiếm tự nhiên.
* **Theo dõi tín hiệu chuyển đổi:** Đo lường lượt gọi điện, yêu cầu chỉ đường và truy cập trang đặt lịch từ Maps.

### 3. Economics & Target KPIs
* **Target:** 100–150 active paying workspaces.
* **Target MRR:** 50,000,000 – 80,000,000 VND.

---

## Phase 4: TikTok Organic Growth & Lead Ingest (Month 4)

### 1. Objective
Khai thác kênh TikTok để tiếp cận tệp học viên trẻ, học sinh, sinh viên và người muốn học nghề qua các video thực hành ngắn.

### 2. Core Capabilities
* **TikTok Direct Post:** Tự động đăng video lên kênh TikTok của cơ sở sau khi duyệt.
* **TikTok Lead Webhook:** Tiếp nhận thông tin học viên quan tâm từ Instant Form và tin nhắn TikTok về Havi CRM.

---

## Phase 5: "🚀 Đẩy Khách Đến" (1-Click In-App Ad Booster) & Scale (Month 5+)

### 1. Objective
Sau khi cỗ máy chuyển đổi tự nhiên (Organic) trên 4 kênh đã hoàn toàn trơn tru và chứng minh hiệu quả tiền thật, mở cổng **chạy quảng cáo trực tiếp trong app Havi** để nhân rộng quy mô khách đến theo nhu cầu.

### 2. Core Capabilities
* **"🚀 Đẩy Khách Đến" (1-Click Local Ad Booster):**
  * 5 câu hỏi trong 30 giây: Mục tiêu $\rightarrow$ Đối tượng $\rightarrow$ Bán kính địa phương (3–10km) $\rightarrow$ Ngân sách tối đa $\rightarrow$ Điểm đến (Messenger/Form).
  * Gọi trực tiếp Meta Marketing API (`POST /campaigns`, `/adsets`, `/ads`) và TikTok Spark Ads API.
* **Mô Hình Zero-Reseller An Toàn:**
  * Trừ tiền trực tiếp từ Ad Account của chủ tiệm (thẻ Visa/Mastercard). Havi không cầm tiền quảng cáo, không gánh rủi ro thuế/pháp lý.
* **Multi-Branch & Chuỗi Cơ Sở:** Hỗ trợ chuyển đổi chi nhánh (Branch Switcher) và quản trị nhiều Fanpage cho chuỗi 2–5 cơ sở.

### 3. Economics & Target KPIs
* **Target:** 300–500 active paying workspaces.
* **Target MRR:** 150,000,000 – 300,000,000 VND.

---

## Phase 5: Global Expansion & Multi-Location Enterprise (Months 9+)

### 1. Objective
Scale Havi internationally across English-speaking and Asian markets with global payment gateways and multi-location management.

### 2. Core Capabilities
* **Global Stripe Subscription Engine:** Automated multi-currency billing ($29/mo – $79/mo).
* **Multi-Location Franchise Management:** Single pane of glass for chains with 5–50 locations.
* **Global Product-Led Growth (PLG):** Launch on Product Hunt, AppSumo, and global affiliate partner networks (20% recurring lifetime commission).

### 3. Economics & Target KPIs
* **Target:** 3,000–5,000 international paying workspaces.
* **Target ARR:** **$1,000,000+ USD (~25+ Billion VND / year)**.

---

## Core Value Proposition Summary

$$\text{Customer Lifetime Value (LTV)} = \underbrace{\text{Time Savings (2 hrs/day)}}_{\text{Immediate Operational Relief}} + \underbrace{\text{Speed-to-Lead + Google Maps SEO}}_{\text{Direct Measurable Revenue}}$$

---

## 6. Competitive Positioning Landscape

```
                            [ TỰ ĐỘNG HÓA CAO (Autonomous Workflow) ]
                                            ▲
                                            │       ★ HAVI (AI Marketing Employee)
                                            │       (Khép kín: Tạo bài ➔ Đăng đa kênh ➔
                                            │        Chốt Inbox 24/7 ➔ Báo cáo doanh thu)
                                            │
           Pancake / Fchat / ManyChat       │
           (Mạnh về Chatbot kịch bản cũ,    │
            không tạo nội dung/video)       │
    ────────────────────────────────────────┼───────────────────────────────────────►
    [ PHỨC TẠP / CHUYÊN SÂU ]               │            [ ĐƠN GIẢN / DI ĐỘNG HÓA ]
                                            │
           KiotViet / Sapo                  │       ChatGPT / Canva / LovinBot
           (Mạnh về POS / Kho hàng,         │       (Bẫy DIY: Bắt tự viết prompt,
            Marketing & Lead Care yếu)      │        tự copy paste, rời rạc công đoạn)
                                            │
                                            ▼
                            [ THỦ CÔNG / RỜI RẠC (Manual Tools) ]
```

---

## 7. FAANG-Grade Brand Positioning & Slogan Matrix

### 7.1 Core Brand Essence
> **"Havi — Nhân viên AI nuôi dưỡng thương hiệu, chốt đơn ngày đêm cho tiệm của bạn."**  
> *(English: "Havi — Your 24/7 Autonomous AI Marketing Employee.")*

### 7.2 Vertical-Specific Value Hooks
* **Spa / Salon / Thẩm Mỹ Viện:** *"Bạn chăm sóc sắc đẹp cho khách — Havi chăm sóc khách hàng và kéo khách đến tiệm cho bạn."*
* **Môi Giới Bất Động Sản:** *"Chụp 1 tấm ảnh sổ đỏ, Havi biến thành 3 bài đăng Facebook và kịch bản video TikTok chốt khách."*
* **Quán Ăn / Cafe / F&B:** *"Đừng để khách thèm ăn lúc nửa đêm nhắn tin mà tiệm ngủ quên. Havi trực inbox, gửi menu chốt bàn 24/7."*
* **Đào Tạo & Kỹ Thuật (Nhật Minh Tech):** *"Biến mọi dự án thực chiến thành bài viết hút học viên. Hiện diện đa kênh không tốn 1 giờ mỗi ngày."*

---

## 8. 30-Day Go-To-Market Execution Blueprint (Đẩy Ra Ngoài Thực Chiến)

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        HAVI 30-DAY GO-TO-MARKET BLUEPRINT                              │
├───────────────────┬───────────────────┬───────────────────┬────────────────────────────┤
│ TUẦN 1            │ TUẦN 2            │ TUẦN 3            │ TUẦN 4                     │
│ Production Deploy │ Dogfooding Pilot  │ Onboard 5-10 Shops│ VietQR Conversion          │
│ Cloud VPS & Domain│ Nhật Minh Tech    │ Free 7-Day Pilot  │ Thu tiền & Scale           │
└───────────────────┴───────────────────┴───────────────────┴────────────────────────────┘
```

1. **Tuần 1: Triển khai Production Cloud & Tên miền chính thức**
   - Chạy Docker Compose (`docker-compose.prod.yml`) trên Cloud VPS (DigitalOcean / AWS / Hetzner / Vietnix).
   - Trỏ domain chính thức (ví dụ: `havi.vn` hoặc `app.havi.vn`) kèm SSL Let's Encrypt tự động.
   - Cấu hình Webhook PayOS Live & Meta Graph API App Live.
2. **Tuần 2: Dogfooding thực chiến tại "Trung Tâm Công Nghệ Nhật Minh"**
   - Vận hành Havi đăng bài dự án, khóa học hàng ngày lên Facebook Page + Google Business.
   - Bật bot trực inbox tư vấn khóa học và ghi nhận lead tự động.
3. **Tuần 3: Onboard Cohort 1 (5–10 Chủ Tiệm Thân Quen)**
   - Mời 5–10 chủ tiệm (1 Spa, 1 Quán ăn, 1 Môi giới BĐS, 1 Tiệm kỹ thuật) dùng thử 7 ngày miễn phí.
   - Hỗ trợ kết nối Fanpage và cấu hình bảng giá/FAQ trong 5 phút.
4. **Tuần 4: Chuyển đổi trả phí qua VietQR & Mở rộng cộng đồng**
   - Sau 7 ngày, gửi thông báo gia hạn gói cước qua VietQR tự động (189k hoặc 369k/tháng).
   - Thu thập video testimonial và feedback thực tế để nhân rộng sang 50 khách hàng tiếp theo.

---

## 9. Định Hướng Quyền Lợi Chi Tiết Từng Gói Thương Mại & Biên Lợi Nhuận

### 9.1 Gói Khởi Nghiệp (189.000 đ/tháng — "Gói Phổ Cập / No-Brainer Offer")
* **Mục tiêu:** Khiến khách hàng không thể từ chối. Rẻ hơn 1 ly trà sữa mỗi tuần.
* **Quyền lợi:**
  * 1 Fanpage Facebook kết nối.
  * 30 bài viết AI/tháng (Ảnh tiệm $\rightarrow$ Bài đăng chuẩn ngành).
  * Trực Inbox & Tự động trả lời Bảng giá/FAQ 24/7.
  * Báo cáo tương tác cơ bản.
* **Biên lợi nhuận gộp:** **92.1%** (Thu 189.000 đ, chi phí hạ tầng AI/Server chỉ tốn ~15.000 đ).

### 9.2 Gói Chuyên Nghiệp (369.000 đ/tháng — "Gói Bán Chạy Nhất / Best Seller")
* **Mục tiêu:** Tối đa hóa doanh thu trung bình trên mỗi khách hàng (ARPU). Đánh trúng đối tượng cần khách thật (Môi giới BĐS, Thẩm mỹ viện, Dạy nghề, Salon).
* **Quyền lợi:**
  * **Đa kênh:** Facebook Fanpage + Google Maps Local SEO + Kịch bản Video TikTok 3 giây.
  * **90 bài viết AI/tháng** + Tạo video ngắn 9:16 từ ảnh tiệm.
  * **AI Lead Agent:** Tự động nhận diện & trích xuất Số điện thoại / Tên khách hàng $\rightarrow$ Bắn thông báo ngay cho chủ tiệm.
  * **Smart CRM Nudge:** Tự động gợi ý tin nhắn kéo khách cũ quay lại tiệm.
* **Biên lợi nhuận gộp:** **93.2%** (Thu 369.000 đ, chi phí hạ tầng tốn ~25.000 đ).

### 9.3 Gói Chuỗi Doanh Nghiệp (799.000 đ/tháng — "Gói Doanh Nghiệp / B2B Scale")
* **Mục tiêu:** Bán cho các chuỗi 2–5 chi nhánh, các trung tâm đào tạo lớn hoặc các Agency nhận làm dịch vụ marketing cho nhiều quán.
* **Quyền lợi:**
  * Quản lý tối đa 5 cơ sở / Fanpage trong 1 tài khoản duy nhất.
  * Không giới hạn bài viết AI & kịch bản video.
  * Đối soát doanh thu bán lẻ qua Webhook POS (KiotViet/Sapo).
  * Hỗ trợ kỹ thuật VIP 1-1 riêng biệt từ đội ngũ kỹ sư Havi.
* **Biên lợi nhuận gộp:** **94.5%** (Thu 799.000 đ, chi phí tốn ~45.000 đ).

---

## 10. Chiến Thuật Bán Hàng Tăng Tốc Dòng Tiền (FAANG Growth Tactics)

### 10.1 Neo Giá Theo Ngày (Reframing to Daily Cost)
* Trên giao diện web, banner truyền thông và kịch bản tư vấn, **tuyệt đối không nhấn mạnh "189k/tháng"**, mà luôn neo:
  > **"Chỉ 6.000 đ/ngày — Thuê trọn đời 1 nhân viên AI cần mẫn đăng bài và trực page 24/7 cho tiệm của bạn."**

### 10.2 Đòn Bẩy Gói Năm (Cash Flow Accelerator)
* Tiểu thương Việt Nam có tâm lý rất thích *"mua 1 lần dùng cả năm để khỏi phải nhớ đóng tiền lắt nhắt"*.
* Đưa ra ưu đãi độc quyền: **"Thanh toán 1 năm: Tặng ngay 3 tháng sử dụng miễn phí + Tặng trọn bộ 50 kịch bản Video TikTok độc quyền."**
* Khi 10 khách hàng đầu tiên quét VietQR gói 1 năm (~3.290.000 đ), Havi có ngay **hơn 30.000.000 đ tiền mặt tươi (Cash Flow)** trong tài khoản để tái đầu tư hạ tầng GPU và marketing.

### 10.3 Phễu Dùng Thử 7 Ngày Không Rủi Ro (Zero-Risk Trial Funnel)
* Đăng ký 30 giây không cần thẻ tín dụng $\rightarrow$ Dùng thử 7 ngày thật đầy đủ tính năng.
* **Ngày thứ 6:** Havi tự động gửi thông báo SMS/Zalo/In-app:
  > *"7 ngày qua Havi đã đăng 7 bài viết chuẩn ngành và trả lời 12 khách hàng cho tiệm. Quét mã VietQR 189k (chỉ 6k/ngày) để tiếp tục giữ chân nhân viên AI của bạn!"*
* Con số **189.000 đ** và **369.000 đ** là những **"điểm ngọt" (Sweet Spots)** đã được chứng minh qua tâm lý học hành vi: vừa đủ rẻ để chủ tiệm quyết định ngay trong 30 giây, vừa mang lại biên lợi nhuận khổng lồ $\ge 92\%$ cho Havi.

