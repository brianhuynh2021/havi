# Havi Commercial Launch & Go-To-Market Execution Guide

> **Target Audience:** Founders, Lead Engineers, Growth Marketers  
> **Mission:** Bring Havi to market, onboard Cohort 1 (10–50 paying shops), and automate revenue collection via PayOS VietQR.

---

## 1. Executive Summary & GTM Strategy

Havi is positioned as an **"AI Marketing Employee"** ($299k–$599k/month) that replaces a part-time marketer (3–5M/month) by running 3 autonomous loops:
1. **Content & Video Publishing:** 30s mobile ingest $\rightarrow$ Multi-channel posts (Facebook, Google Maps, TikTok/Shorts hooks).
2. **24/7 Lead Care (Inbox Speed-to-Lead):** Auto-responds with verified price lists and captures customer phone numbers within 5 seconds.
3. **Automated CRM Nudge:** Re-engages past customers with 1-tap re-activation offers.

---

## 2. 4-Step Production Cloud Deployment (Hạ Tầng Sẵn Sàng)

### Step 2.1: Cloud VPS Provisioning
* **Recommended Providers:** DigitalOcean Droplet, Hetzner Cloud, AWS EC2, or Vietnix VPS.
* **Specs:** 2–4 vCPU, 4–8 GB RAM, Ubuntu 22.04 LTS (~$10–$20/month).
* **Setup Docker:**
```bash
sudo apt update && sudo apt install -y docker.io docker-compose-v2
```

### Step 2.2: Clone & Environment Configuration
```bash
git clone https://github.com/brianhuynh2021/havi.git /opt/havi
cd /opt/havi
cp .env.example .env
# Chỉnh sửa biến môi trường Production:
# - HAVI_ENV=production
# - DATABASE_URL=postgresql+asyncpg://...
# - REDIS_URL=redis://...
# - PAYOS_CLIENT_ID, PAYOS_API_KEY, PAYOS_CHECKSUM_KEY
# - META_APP_ID, META_APP_SECRET
```

### Step 2.3: Launch Production Stack
```bash
# Khởi động cụm dịch vụ Production (FastAPI, Next.js, Celery, Postgres, Redis, Caddy SSL)
docker compose -f docker-compose.prod.yml up -d
```

### Step 2.4: Permanent Webhook Registration
* **PayOS Webhook URL:** `https://app.havi.vn/webhooks/payos`
* **Meta Graph Webhook URL:** `https://app.havi.vn/webhooks/meta` (Verify Token: configured in `.env`)

---

## 3. Cohort 1 Target Profile (10–20 Pilot Shops)

| Sector | Target % | Pain Point Solved by Havi |
|---|---|---|
| **Spa / Salon / Thẩm Mỹ** | 35% | Bận làm dịch vụ dính tay $\rightarrow$ Havi trực Inbox báo giá + chốt lịch 24/7. |
| **Quán Ăn / Cafe / F&B** | 25% | Khách hỏi menu đêm $\rightarrow$ Havi gửi menu + địa chỉ Google Maps tức thì. |
| **Cò / Môi Giới Bất Động Sản** | 25% | Đi đường xem đất $\rightarrow$ Chụp 1 ảnh sổ đỏ, Havi biến thành 3 bài đăng + kịch bản TikTok. |
| **Dịch Vụ Kỹ Thuật / Đào Tạo** | 15% | Đăng bài dự án thực chiến hàng ngày lên Fanpage/Google Maps mà không tốn 1 giờ viết. |

---

## 4. 15-Second Sales Pitch & Onboarding Scripts

### 4.1 15-Second Elevator Pitch (Nói trực tiếp hoặc nhắn Zalo)
> *"Chào anh/chị, thay vì bỏ 4–5 triệu thuê người đăng bài mà nửa đêm vẫn bị sót tin nhắn của khách, Havi là nhân viên AI chỉ 10k/ngày: vừa tự làm bài đăng đa kênh chuẩn ngành, vừa trực page trả lời bảng giá và xin số điện thoại khách trong 5 giây. Em cài cho anh/chị dùng thử 7 ngày miễn phí nhé, chỉ mất 3 phút kết nối Fanpage thôi!"*

### 4.2 3-Minute Onboarding Protocol
1. **Phút 1:** Mở `app.havi.vn` $\rightarrow$ Đăng ký tài khoản $\rightarrow$ Chọn ngành (Spa, F&B, BĐS...).
2. **Phút 2:** Bấm **"Kết nối Facebook"** $\rightarrow$ Chọn Fanpage của tiệm.
3. **Phút 3:** Nhập 3–5 dịch vụ chính + bảng giá $\rightarrow$ Bấm chụp 1 ảnh để Havi tạo ngay bài đăng đầu tiên.

---

## 5. Automated 7-Day VietQR Conversion Protocol

```
[Day 1-6: Trải nghiệm 7 ngày Miễn Phí]
  │
  ├─► Havi tự đăng 1-2 bài/ngày + trực inbox trả lời khách
  │
[Day 7: Thông báo kích hoạt gói dịch vụ]
  │
  ├─► Popup hiển thị VietQR PayOS (189k Gói Khởi Nghiệp / 369k Gói Chuyên Nghiệp)
  │
[Khách hàng quét chuyển khoản]
  │
  └─► PayOS Webhook kích hoạt trong 1.0s ➔ Tự động gia hạn 30 ngày ➔ Xuất hóa đơn VAT
```

---

## 6. Daily Founder Dogfooding & Quality Monitoring

Chạy bộ kiểm tra sức khỏe hệ thống tự động:
```bash
# Kiểm thử toàn diện 608 bài test
cd apps/backend && uv run pytest
npm --prefix apps/web test

# Chạy kịch bản giả lập Dogfooding 7 ngày
cd apps/backend && python ../../scripts/dogfood_suite.py
```

