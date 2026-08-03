# Havi System Architecture

Tài liệu này là sơ đồ triển khai chuẩn cho MVP, được rút ra từ prototype
`Havi - Kiến Trúc Hệ Thống.dc.html`, `REPOSITORY_STRATEGY.md` và
`TECHNICAL_SPEC.md`.

## 1. Kiến trúc tổng thể

```mermaid
flowchart LR
    subgraph INPUT["Nguồn vào"]
        WEB["Web app<br/>Ảnh, ghi âm, nội dung, duyệt"]
        SALES["Webhook bán hàng"]
        LISTEN["Social listening crawler"]
    end

    subgraph EDGE["API boundary"]
        API["FastAPI<br/>Auth, workspace, CRUD, approvals"]
    end

    subgraph CORE["Lõi xử lý theo job"]
        QUEUE["Redis / Job Queue"]
        MEDIA["Ingest & Media Pipeline<br/>code thường"]
        PROFILE["Industry / Brand Profile<br/>cache theo tenant"]
        CONTENT["Content Engine<br/>LLM, một lần gọi nhiều đầu ra"]
        CLASSIFY["Listening Classifier<br/>rule + model nhỏ"]
        REPLY["Reply Drafter + CRM<br/>luôn chờ chủ duyệt"]
        SCHEDULER["Scheduler<br/>lịch đăng, retry, quota"]
        EVENT["event_log<br/>input, output, token, thời gian"]
    end

    subgraph DATA["Dữ liệu"]
        POSTGRES[("PostgreSQL<br/>tenant-scoped")]
        OBJECT[("Object Storage<br/>media assets")]
    end

    subgraph OUTPUT["Adapter kênh ra"]
        META["Facebook / Instagram"]
        ZALO["Zalo OA / ZNS"]
        GOOGLE["Google Business"]
        VIDEO["TikTok / YouTube"]
        EMAIL["Email"]
    end

    WEB -->|HTTPS / OpenAPI| API
    SALES --> API
    LISTEN --> API
    API --> POSTGRES
    API --> OBJECT
    API --> QUEUE
    QUEUE --> MEDIA
    QUEUE --> CONTENT
    QUEUE --> CLASSIFY
    QUEUE --> REPLY
    QUEUE --> SCHEDULER
    PROFILE --> CONTENT
    PROFILE --> REPLY
    MEDIA --> OBJECT
    MEDIA --> POSTGRES
    CONTENT --> POSTGRES
    CLASSIFY --> REPLY
    REPLY --> POSTGRES
    SCHEDULER --> META
    SCHEDULER --> ZALO
    SCHEDULER --> GOOGLE
    SCHEDULER --> VIDEO
    SCHEDULER --> EMAIL
    MEDIA --> EVENT
    CONTENT --> EVENT
    CLASSIFY --> EVENT
    REPLY --> EVENT
    SCHEDULER --> EVENT
    EVENT --> POSTGRES
```

## 2. Kiến trúc frontend

Frontend dùng Next.js App Router. Route chỉ ghép màn hình; business state và API
được tách theo feature để khi nối backend không phải sửa lại phần trình bày.

```mermaid
flowchart TD
    ROUTES["src/app<br/>route, layout, metadata"] --> SHELL["App Shell<br/>sidebar, workspace, responsive nav"]
    SHELL --> DASHBOARD["features/dashboard<br/>Tổng quan"]
    SHELL --> CONTENT_UI["features/content<br/>Tạo nội dung"]
    SHELL --> CALENDAR_UI["features/calendar<br/>Lịch đăng"]
    SHELL --> LEADS_UI["features/leads<br/>Khách tiềm năng"]
    SHELL --> REPORT_UI["features/analytics<br/>Báo cáo"]

    DASHBOARD --> UI["components/ui<br/>card, badge, button, empty state"]
    CONTENT_UI --> UI
    CALENDAR_UI --> UI
    LEADS_UI --> UI
    REPORT_UI --> UI

    DASHBOARD --> DATA["Feature data layer"]
    CONTENT_UI --> DATA
    CALENDAR_UI --> DATA
    LEADS_UI --> DATA
    REPORT_UI --> DATA
    DATA --> MOCK["Mock fixtures<br/>giai đoạn dựng prototype"]
    DATA --> CLIENT["Generated OpenAPI client<br/>giai đoạn nối backend"]
    CLIENT --> API["FastAPI"]
```

### Cấu trúc mục tiêu

```text
apps/web/src/
├── app/                         # Routing, layouts, metadata
├── components/
│   ├── app-shell/               # Sidebar và workspace switcher
│   └── ui/                      # Primitive dùng chung
├── features/
│   ├── dashboard/
│   ├── content/
│   ├── calendar/
│   ├── leads/
│   └── analytics/
├── lib/
│   ├── api-client/              # Chỉ gọi backend qua HTTP
│   └── config/
└── styles/                      # Design tokens toàn cục
```

## 3. Luồng trạng thái nội dung

```mermaid
stateDiagram-v2
    [*] --> draft
    draft --> pending_approval: AI tạo bản nháp
    pending_approval --> draft: Chủ tiệm sửa / từ chối
    pending_approval --> approved: Chủ tiệm duyệt
    approved --> scheduled: Chọn giờ đăng
    scheduled --> publishing: Scheduler chạy job
    publishing --> published: Adapter trả thành công
    publishing --> failed: Lỗi nền tảng
    failed --> publishing: Retry có giới hạn
```

Backend là nguồn sự thật của state machine. Frontend chỉ hiển thị trạng thái và
gửi action; không giữ token nền tảng, prompt production hoặc secret.

## 4. Thứ tự triển khai frontend

1. Khóa design tokens và App Shell theo prototype.
2. Dựng từng màn bằng fixture tĩnh, bắt đầu từ `Tổng quan`.
3. Bổ sung interaction đúng prototype trong từng feature.
4. Sinh TypeScript client từ OpenAPI rồi thay fixture bằng API data.
5. Thêm loading, empty, error và permission states trước khi tích hợp end-to-end.

