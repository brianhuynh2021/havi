# Havi Design-Partner Launch Guide

> **Target Audience:** Founder, product and operations team
> **Mission:** onboard 5–10 paying design partners, verify the Facebook operating
> loop with real data, and collect evidence before a self-service launch.
>
> All claims in this guide are subordinate to
> [PRODUCT_CONTRACT.md](../product/PRODUCT_CONTRACT.md).

---

## 1. Executive Summary & GTM Strategy

Havi is a **multi-channel communications manager for small businesses**
(299k–599k VND/month). Positioning source of truth:
[ROADMAP.md §1](../product/ROADMAP.md).

What the pitch may claim, because the software does it and can prove it:

1. **Posting keeps its rhythm.** Prepare a week in one sitting; Havi publishes
   one story per day on the schedule the owner approved, tracking publish status
   and failures directly via official Graph API responses.
2. **Messages land in one inbox.** Comments and Messenger appear together;
   approved FAQs can prefill a reply, and a person decides what is sent.
3. **Clips already made get published.** Upload, Havi checks the clip fits the
   channel, posts it, then reads the page back to confirm before marking published.

What the pitch must **never** claim:

* that Havi replaces a marketer — it drafts, a person approves;
* that Havi brings customers, visits, or revenue;
* a response time Havi does not measure ("5 giây", "24/7 tự động");
* any number not taken from the customer's own workspace data.

A promise the product cannot keep costs more than the sale is worth: the
customer discovers it in week one and never trusts the rest.

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
# - HAVI_TOKEN_ENCRYPTION_KEY=<sinh bằng: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())">
# - HAVI_DATABASE_URL=postgresql+psycopg://...
# - HAVI_REDIS_URL=redis://...
# - HAVI_MEDIA_PUBLIC_URL=https://<domain_cdn_hoặc_r2>/havi-media
# - HAVI_PAYOS_CLIENT_ID, HAVI_PAYOS_API_KEY, HAVI_PAYOS_CHECKSUM_KEY
# - HAVI_FACEBOOK_CLIENT_ID, HAVI_FACEBOOK_CLIENT_SECRET
# - HAVI_META_WEBHOOK_VERIFY_TOKEN=<chuỗi_tự_đặt_khớp_với_meta_dashboard>
```

### Step 2.3: Launch Production Stack
```bash
# Khởi động cụm dịch vụ Production (FastAPI, Next.js, Celery, Postgres, Redis, Caddy SSL)
docker compose -f docker-compose.prod.yml up -d
```

### Step 2.4: Permanent Webhook & Facebook Permissions Setup
* **PayOS Webhook URL:** `https://app.havi.vn/webhooks/payos`
* **Meta Graph Webhook URL:** `https://app.havi.vn/webhooks/meta` (Verify Token: configured via `HAVI_META_WEBHOOK_VERIFY_TOKEN`)
* **Meta App Facebook Scopes (7 quyền bắt buộc trong `adapters/oauth/facebook.py`):**
  1. `pages_show_list` (Hiển thị danh sách Fanpage)
  2. `pages_read_engagement` (Đọc chỉ số & bài viết)
  3. `pages_manage_posts` (Đăng bài viết & video)
  4. `pages_messaging` (Nhận & gửi tin nhắn Messenger)
  5. `pages_read_user_content` (Đọc bình luận của khách)
  6. `pages_manage_engagement` (Trả lời bình luận của khách)
  7. `pages_manage_metadata` (Đăng ký nhận webhook sự kiện)

---

## 3. Cohort 1 target profile (5–10 design partners)

Select service businesses that already operate an active Facebook Page and have
at least two people in the social workflow: one handles content or inbox work,
and one owns or approves it. Training centres, clinics, spas and small service
chains are suitable examples. Do not recruit a business whose primary need is
orders, POS, livestream selling or ad execution; those are outside Havi's scope.

---

## 4. Honest pitch and onboarding

### 4.1 15-Second Elevator Pitch (Nói trực tiếp hoặc nhắn Zalo)
> *"Havi gom việc social cần xử lý vào một hàng đợi: bài chờ duyệt, tin nhắn
> đang chờ, bài đăng lỗi và kênh mất kết nối. Havi chuẩn bị nội dung, người có
> quyền duyệt, rồi hệ thống chỉ báo thành công sau khi Facebook xác nhận."*

### 4.2 3-Minute Onboarding Protocol
1. **Phút 1:** Mở `app.havi.vn` $\rightarrow$ Đăng ký tài khoản $\rightarrow$ Chọn ngành (Spa, F&B, BĐS...).
2. **Phút 2:** Bấm **"Kết nối Facebook"** $\rightarrow$ Chọn Fanpage của tiệm.
3. **Sau khi nối:** nhập thông tin thương hiệu, tạo một bản nháp, duyệt và xác
   nhận một bài thật hoặc xử lý một hội thoại thật trong 24 giờ.

---

## 5. Seven-day design-partner protocol

```
[Day 1: Kết nối Facebook Page thật]
  │
  ├─► Founder cùng khách hoàn thành một hành động đã được duyệt
  │
[Day 2-6: Quan sát hàng đợi, lỗi đăng và hội thoại thật]
  │
  ├─► Ghi nhận việc được xử lý, thời gian phản hồi và phản hồi của từng vai trò
  │
[Day 7: Review cùng khách]
  │
  └─► Chỉ đề nghị trả phí khi vòng vận hành thật đã hoàn tất; VietQR chỉ được
      coi là thanh toán sau khi webhook hoặc đối soát xác nhận
```

---

## 6. Daily Founder Dogfooding & Quality Monitoring

Chạy bộ kiểm tra sức khỏe hệ thống tự động:
```bash
# Kiểm thử toàn diện 608 bài test
cd apps/backend && uv run pytest
npm --prefix apps/web test

# Chạy kịch bản giả lập Dogfooding 7 ngày
# Dogfooding is done against the running app, by a person.
# The old dogfood_suite.py runner was removed: it printed a scripted
# journey with invented numbers, which looks like a passing test but
# exercises nothing.
cd apps/backend && uv run pytest
```
