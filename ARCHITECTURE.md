# 🏛️ Havi 3.0 System Architecture & Engineering Blueprint

> **Team Persona & Standards**: MIT Distributed Systems Rigor × Stanford Product & HCI Excellence.  
> **Core Tenet**: "Làm xong $\rightarrow$ Gắn bộ kiểm thử thật (Integration/Unit Tests) đạt 100% Pass $\rightarrow$ Mới phát hành."

---

## 1. Executive Summary & Product Positioning

**Havi 3.0** is the **Local Customer-to-Visit OS** (Hệ điều hành biến hoạt động thật tại cơ sở thành khách đến và doanh thu được xác minh).

```mermaid
flowchart LR
    A["📸 Hoạt Động Thật Tại Cơ Sở<br/>(Ảnh, Video 9:16, Lớp học, Dịch vụ)"] 
    --> B["⚡ Havi 3.0 OS<br/>(AI Content, Reels, Messenger Webhook)"]
    --> C["🎯 Đúng Người Địa Phương<br/>(Bán kính 3-10km Facebook/Reels)"]
    --> D["🏆 Khách Đến & Doanh Thu<br/>(Check-in & Chuyển khoản VietQR)"]

    style A fill:#f8fafc,stroke:#94a3b8,color:#0f172a
    style B fill:#1877f2,stroke:#1565c0,color:#fff
    style C fill:#3b82f6,stroke:#1d4ed8,color:#fff
    style D fill:#10b981,stroke:#047857,color:#fff
```

* **North Star Metric**: Số lượt khách đến đã xác minh mỗi tuần trên mỗi doanh nghiệp hoạt động (*Verified Visits / active business / week*).
* **Health Metric**: Tốc độ phản hồi tin nhắn khách hàng qua Messenger < 10 giây.
* **Platform Priority Strategy**: Tập trung tối ưu hoàn hảo 100% trên **Facebook (Fanpage, Reels, Messenger)** $\rightarrow$ Mở rộng sang Google Business Profile $\rightarrow$ YouTube Shorts $\rightarrow$ TikTok.

---

## 2. High-Level C4 Container Architecture

Havi được thiết kế theo mô hình **Modular Monolith với Clean / Hexagonal Domain-Driven Design (DDD)**:

```mermaid
C4Container
    title Havi 3.0 Container Architecture Diagram

    Person(merchant, "Chủ cơ sở / Doanh nghiệp", "Quản lý bài đăng, duyệt nội dung, trả lời khách và theo dõi doanh thu.")
    Person(customer, "Khách hàng địa phương", "Tương tác với Fanpage, xem Reels, nhắn tin hỏi giá và ghé cơ sở.")

    System_Boundary(havi_platform, "Havi Platform") {
        Container(web_app, "Web App (PWA)", "Next.js 16 (App Router), React, Vanilla CSS Modules", "Giao diện người dùng: Lộ trình tăng trưởng, Duyệt bài 1-chạm, Video Studio, CRM Lead & Báo cáo doanh thu.")
        Container(api_gateway, "Backend API Gateway", "FastAPI, Python 3.14, AsyncIO, Pydantic v2", "Cung cấp REST APIs, xác thực JWT/Argon2id, kiểm soát rate limit và điều phối nghiệp vụ.")
        Container(celery_worker, "Async Job Worker", "Celery, Python Async Bridge", "Xử lý hàng đợi ngầm: Sinh kịch bản AI, Render video 9:16, Đăng bài Facebook đúng giờ, Bắn CRM Nudge.")
        Container(celery_beat, "Scheduler Daemon", "Celery Beat", "Quét lịch đăng bài (Dispatch due posts), lập lịch thông báo định kỳ.")
        
        ContainerDb(postgres, "Primary Database", "PostgreSQL 16", "Lưu trữ tập trung: Workspace, Users, Content Items, Goals, Leads, Inboxes, Payments.")
        ContainerDb(redis, "Cache & Broker", "Redis 7", "Hàng đợi Celery, Khóa phân tán (Distributed Locks), Cache token & Quota.")
        ContainerDb(storage, "Object Storage", "MinIO / Cloudflare R2 / AWS S3", "Lưu trữ hình ảnh, âm thanh ghi âm và video ngắn 9:16 đã render.")
    }

    System_Ext(meta_api, "Meta Graph API v20.0", "Facebook Pages, Reels Publishing & Messenger Webhook.")
    System_Ext(payos_api, "PayOS / VietQR Gateway", "Tạo mã thanh toán VietQR và Webhook đối soát doanh thu tự động.")
    System_Ext(gemini_api, "Google Gemini AI API", "Mô hình ngôn ngữ lớn (LLM) sinh bài viết chuẩn Brand Voice và phân loại ý định khách hàng.")

    Rel(merchant, web_app, "Sử dụng giao diện", "HTTPS")
    Rel(web_app, api_gateway, "Gửi yêu cầu API", "JSON / HTTPS / OpenAPI")
    Rel(api_gateway, postgres, "Đọc/Ghi dữ liệu nghiệp vụ", "Async SQLAlchemy 2.0")
    Rel(api_gateway, redis, "Lấy/Lưu cache & Rate limit", "aioredis")
    Rel(api_gateway, celery_worker, "Đẩy background jobs", "Redis Queue")
    Rel(celery_beat, celery_worker, "Kích hoạt định kỳ", "Celery Events")
    Rel(celery_worker, postgres, "Cập nhật trạng thái job", "Async SQLAlchemy")
    Rel(celery_worker, storage, "Lưu file media/video", "boto3 / S3 API")
    Rel(celery_worker, gemini_api, "Sinh nội dung AI", "HTTPS REST")
    Rel(celery_worker, meta_api, "Đăng bài Fanpage / Reels", "HTTPS Meta Graph API")
    Rel(customer, meta_api, "Nhắn tin Messenger / Comment bài", "Facebook App")
    Rel(meta_api, api_gateway, "Bắn Webhook tin nhắn", "HTTPS SHA-256 HMAC")
    Rel(payos_api, api_gateway, "Bắn Webhook chuyển khoản VietQR", "HTTPS HMAC-SHA256")
```

---

## 3. Core Business Dataflow & Sequence Diagrams

### Flow 1: Facebook Content Creation & Human-in-the-Loop Publishing
> **Bất biến**: Không có bài nào được đăng lên Facebook nếu chưa có hành động duyệt rõ ràng từ chủ cơ sở.

```mermaid
sequenceDiagram
    autonumber
    actor User as Chủ cơ sở (Merchant)
    participant Web as Next.js Web App
    participant API as FastAPI Backend
    participant Worker as Celery Worker
    participant Gemini as Google Gemini AI
    participant DB as PostgreSQL 16
    participant Meta as Meta Graph API

    User->>Web: Nhập ý tưởng / Ghi âm / Ảnh thật
    Web->>API: POST /content/generate (Idempotency Key)
    API->>DB: Kiểm tra Token Quota & Tạo Content Job (QUEUED)
    API->>Worker: Đẩy job sinh nội dung
    Worker->>Gemini: Prompt chuẩn Brand Voice & Industry
    Gemini-->>Worker: Trả về bài nháp (Caption, Hashtags, 3s Hook)
    Worker->>DB: Lưu ContentItem (Trạng thái: DRAFT)
    Web->>User: Hiển thị bài nháp trên màn hình "Hôm nay / Duyệt bài"
    
    User->>Web: Bấm "Duyệt & Đăng ngay" (hoặc Hẹn giờ vàng)
    Web->>API: POST /content/{id}/approve (publish_now=true)
    API->>DB: Cập nhật Trạng thái: APPROVED + Audit Log
    API->>Worker: Kích hoạt Publish Job (Idempotent Lock)
    Worker->>DB: Đọc Page Access Token (Giải mã AES-128 Fernet)
    Worker->>Meta: POST /{page-id}/feed (hoặc /{page-id}/video_reels)
    Meta-->>Worker: Trả về platform_post_id
    Worker->>DB: Cập nhật ContentItem: PUBLISHED + Lưu platform_post_id
    Worker-->>Web: Cập nhật lịch đăng & Báo cáo thời gian thực
```

---

### Flow 2: Facebook Messenger Webhook & Instant Lead Capture (<10s)
> **Bất biến**: Webhook phải xác thực chữ ký SHA-256 HMAC; Lead và số điện thoại phải được trích xuất an toàn.

```mermaid
sequenceDiagram
    autonumber
    actor Cust as Khách hàng
    participant Meta as Meta Webhook Server
    participant API as FastAPI Webhook Handler
    participant Ingest as AI Lead Ingestion Service
    participant DB as PostgreSQL 16
    participant Web as Next.js Web App

    Cust->>Meta: Nhắn tin vào Fanpage / Bình luận hỏi học phí
    Meta->>API: POST /webhooks/facebook (X-Hub-Signature-256)
    API->>API: Xác thực chữ ký HMAC-SHA256 bí mật
    API-->>Meta: HTTP 200 OK (Ngay tức thì, tránh timeout)
    API->>Ingest: Xử lý sự kiện tin nhắn trong background
    Ingest->>Ingest: Phân tích ý định & Rút trích Tên, SĐT, Nhu cầu
    Ingest->>DB: Lưu InboxItem + Tạo Lead mới (CRM)
    alt Có FAQ đã được duyệt trước (VD: Lịch học thử miễn phí)
        Ingest->>Meta: Tự động gửi câu trả lời tức thì (< 10 giây)
    else Cần tư vấn sâu
        Ingest->>DB: Lưu bản nháp gợi ý phản hồi cho tư vấn viên
        Ingest->>Web: Bắn thông báo đẩy vào tab Trực Khách (/app/inbox)
    end
```

---

### Flow 3: Verified Local Visits & Closed-Loop Revenue Attribution
> **Bất biến**: Doanh thu chỉ được xác nhận khi có giao dịch thanh toán thật (VietQR) hoặc check-in tại cơ sở.

```mermaid
sequenceDiagram
    autonumber
    actor Cust as Khách hàng / Học viên
    actor Merchant as Trung tâm / Cơ sở
    participant PayOS as Cổng Thanh Toán PayOS / VietQR
    participant API as FastAPI Backend
    participant DB as PostgreSQL 16
    participant Web as Next.js Web App

    Cust->>Merchant: Đến học thử / Trải nghiệm dịch vụ thật tại cơ sở
    Merchant->>Cust: Cung cấp mã VietQR thanh toán học phí / dịch vụ
    Cust->>PayOS: Quét mã chuyển khoản qua ứng dụng Ngân hàng
    PayOS->>API: POST /webhooks/payment/payos (Kèm chữ ký HMAC)
    API->>DB: Khóa dòng giao dịch (Row Lock), kiểm tra chống trùng lặp
    API->>DB: Cập nhật Lead: Trạng thái WON + Ghi nhận Doanh thu (VND)
    API->>DB: Gắn cờ Attribution: Khách hàng đến từ nguồn Facebook
    API-->>Web: Cập nhật Báo Cáo Doanh Thu Thực Tế (/app/reports & /app/leads)
```

---

## 4. Codebase Layout & Hexagonal DDD Layers

### Backend Directory Architecture (`apps/backend/`)
```text
apps/backend/
├── api/                         # Presentation Layer (FastAPI Routers, Dependency Injection)
│   ├── deps.py                  # Database Session, Auth, Workspace Context
│   ├── main.py                  # FastAPI Application Entrypoint & Middleware
│   ├── rate_limit.py            # Workspace Rate Limiting Policies
│   └── routers/                 # Thin HTTP Routers (content, inbox, leads, billing, webhooks...)
├── application/                 # Application Services (Use Cases & Transaction Boundaries)
│   └── services/                # ApprovalService, PublishService, LeadService, VideoRenderService...
├── domain/                      # Core Domain Layer (Pure Python, Zero Framework Dependencies)
│   ├── models/                  # Domain Entities (ContentItem, Lead, Goal, Workspace, User...)
│   ├── policies/                # Domain Invariants, Quotas, Intent Parsing, Video Safe-Zones
│   └── ports/                   # Repository & Provider Abstract Interfaces
├── adapters/                    # Infrastructure Adapters Layer
│   ├── persistence/             # SQLAlchemy Repositories (ContentRepository, LeadRepository...)
│   ├── social/                  # FacebookAdapter (Meta Graph API v20.0), Zalo, TikTok
│   ├── llm/                     # GeminiAdapter (LLM Client)
│   ├── storage/                 # S3/MinIO Storage Adapter
│   └── payment/                 # PayOS / VietQR Adapter
├── worker/                      # Celery Async Execution Layer
│   ├── celery_app.py            # Celery Configuration & Redis Broker Connection
│   └── tasks.py                 # Async Background Tasks (Generate, Publish, Render)
├── scheduler/                   # Celery Beat Scheduled Tasks (Dispatch due posts)
├── migrations/                  # Alembic Database Migrations
└── tests/                       # 100% Deterministic Test Suite (505 Pytest tests)
```

### Frontend Directory Architecture (`apps/web/`)
```text
apps/web/
├── src/
│   ├── app/                     # Next.js 16 App Router Pages & Layouts
│   │   ├── (app)/app/           # Authenticated App Shell Pages (/today, /content, /inbox, /reports...)
│   │   ├── (marketing)/         # Public Landing Page, Pricing & Legal Pages
│   │   └── globals.css          # Design System Tokens & Typography
│   ├── components/              # Shared UI Primitives & App Shell Components
│   │   ├── app-shell/           # Header, Sidebar, User Profile & Navigation
│   │   └── ui/                  # Button, Toast, State Views, Modal, OTP Input
│   ├── features/                # Feature Modules (Isolated Business Capabilities)
│   │   ├── today/               # Daily Action Center & Priority Tasks
│   │   ├── content-creation/    # AI Studio, Video Teleprompter & Caption Editor
│   │   ├── inbox/               # Messenger Instant Care & Auto FAQ Responses
│   │   ├── leads/               # CRM Lead Pipeline & Verified Visits
│   │   ├── reports/             # Facebook Performance Analytics & Revenue Attribution
│   │   ├── roadmap/             # Living Growth Roadmap & Goal Generator
│   │   ├── billing/             # Subscription Plans & Token Quotas
│   │   └── onboarding/          # Business Truth Pack Initializer
│   └── lib/                     # Client Infrastructure
│       ├── api-client/          # Auto-generated Type-Safe OpenAPI Client & Schema
│       ├── auth/                # JWT Token Store & Route Guards
│       └── i18n/                # Vietnamese / English Localization Context
└── tests/                       # Vitest Component & Integration Tests (178 tests)
```

---

## 5. Security Guardrails & Invariants

1. **Bảo Mật Khóa Truy Cập Mạng Xã Hội**: Mọi Page Access Token lưu trong cơ sở dữ liệu đều được mã hóa đối xứng qua thuật toán **AES-128 Fernet**. Token thô tuyệt đối không bao giờ được serialize ra ngoài REST API response.
2. **Xác Thực Mật Khẩu**: Sử dụng chuẩn công nghiệp **Argon2id** với thông số bộ nhớ nghiêm ngặt, chống brute-force và rainbow table.
3. **Phân Lập Đa Doanh Nghiệp (Multi-Tenant Isolation)**: Mọi câu truy vấn Database bắt buộc phải lọc theo `workspace_id`. Không có endpoint nào cho phép truy cập chéo dữ liệu tiệm khác.
4. **Chống Đăng Lặp (Idempotency)**: Đảm bảo bởi 2 lớp: Ràng buộc duy nhất `unique_post_fingerprint` ở mức PostgreSQL và khóa phân tán `aioredis` tại `PublishService`.

---

## 6. Developer Quickstart & Testing Mandate

### Chạy Môi Trường Phát Triển:
```bash
npm run dev
# Tự động khởi chạy:
# - Frontend: http://localhost:3000
# - Backend API: http://localhost:8000 (Swagger docs tại /docs)
# - PostgreSQL 16, Redis 7 & MinIO qua Docker
```

### Chạy Bộ Kiểm Thử Bắt Buộc (Mandatory Test Suite):
```bash
# 1. Kiểm tra Frontend Vitest (32 files, 178 tests)
npm --prefix apps/web test

# 2. Kiểm tra Next.js Production Build
npm --prefix apps/web run build

# 3. Kiểm tra Backend Pytest (505 tests)
uv run --directory apps/backend pytest
```
