# Repository Strategy & Future Split Plan — Havi (Một Chạm)

Tài liệu kỹ thuật đi kèm bộ handoff thiết kế. Dành cho dev / Claude Code khi khởi tạo codebase thật.

## Quyết định mặc định của dự án (MVP)

```text
Repository model:    Monorepo
Frontend / backend:  Logically separated (tách kiến trúc, không tách repo)
Deployment:          Independent per app
Database ownership:  Backend only
Secrets ownership:   Backend + infrastructure only
API contract:        OpenAPI
Future split method: git subtree split
Manual file copying: Not allowed
```

> Tách kiến trúc từ ngày đầu, nhưng chỉ tách repository khi có nhu cầu kinh doanh, đội ngũ hoặc bảo mật thực sự.

## Cấu trúc ban đầu

```text
havi-platform/
├── apps/
│   ├── web/              # Next.js frontend
│   └── backend/
│       ├── api/          # FastAPI entrypoint
│       ├── worker/       # Celery worker entrypoint
│       ├── scheduler/    # Celery Beat entrypoint
│       ├── core/         # Domain và application services dùng chung
│       └── migrations/   # Alembic migrations
├── packages/
│   ├── generated-api-client/
│   └── frontend-config/
├── contracts/
│   ├── openapi/
│   └── events/
├── infrastructure/
├── docs/
└── docker-compose.yml
```

## 1. Nguyên tắc tách biệt ngay từ đầu

Frontend và backend là hai ứng dụng độc lập dù cùng repository. Giao tiếp duy nhất qua HTTP API:

```text
Next.js frontend
        ↓ HTTPS
FastAPI backend
```

Frontend **không được**: import Python code từ backend; truy cập PostgreSQL/Redis trực tiếp; chứa database credential, OAuth client secret, LLM API key, prompt production, encryption key; phụ thuộc đường dẫn nội bộ của backend.

Không viết:

```typescript
import something from "../../../api/internal"
```

Phải dùng API client riêng:

```typescript
import { apiClient } from "@/lib/api-client"
```

Backend xuất OpenAPI contract tại `/openapi.json`; frontend sinh TypeScript client từ đó để giảm sai lệch request/response.

## 2. Deploy độc lập dù đang dùng monorepo

```text
.github/workflows/
├── deploy-web.yml
├── deploy-api.yml
├── deploy-worker.yml
└── deploy-scheduler.yml
```

- Thay đổi `apps/web` → chỉ deploy frontend
- Thay đổi `apps/backend/api` → chỉ deploy backend
- Thay đổi `apps/backend/worker` → chỉ deploy worker
- Thay đổi `apps/backend/scheduler` → chỉ deploy scheduler
- Database migration được kiểm soát riêng

Ví dụ:

```text
apps/web        → Cloudflare Workers
apps/backend/api        → Railway hoặc AWS
apps/backend/worker     → Railway hoặc AWS
apps/backend/scheduler  → Railway hoặc AWS
```

## 3. Environment variables tách biệt

Frontend:

```env
NEXT_PUBLIC_API_URL=https://api.example.com
NEXT_PUBLIC_MEDIA_URL=https://media.example.com
```

Backend:

```env
DATABASE_URL=
REDIS_URL=
OPENAI_API_KEY=
FACEBOOK_CLIENT_SECRET=
GOOGLE_CLIENT_SECRET=
ZALO_CLIENT_SECRET=
TOKEN_ENCRYPTION_KEY=
```

Frontend không bao giờ nhận biến môi trường bí mật của backend.

## 4. Khi nào mới tách thành nhiều repository

Không tách chỉ để "trông chuyên nghiệp". Chỉ tách khi:

- Team frontend và backend hoạt động độc lập
- Release cadence rất khác nhau
- CI/CD monorepo quá chậm hoặc khó quản lý
- Quyền truy cập source code cần khác nhau (dev chỉ được xem frontend)
- Backend chứa IP cần bảo vệ cao hơn
- Background processing đã thành hệ thống lớn
- Nhiều team / nhiều owner
- Monorepo gây xung đột hoặc bottleneck rõ ràng

## 5. Cách tách repository sau này

Không copy code thủ công. Dùng `git subtree split`.

Frontend:

```bash
git subtree split --prefix=apps/web -b split-web
git remote add web-repo <NEW_FRONTEND_REPOSITORY_URL>
git push web-repo split-web:main
```

Backend:

```bash
git subtree split --prefix=apps/backend -b split-backend
git remote add backend-repo <NEW_BACKEND_REPOSITORY_URL>
git push backend-repo split-backend:main
```

Infrastructure:

```bash
git subtree split --prefix=infrastructure -b split-infrastructure
git remote add infrastructure-repo <NEW_INFRASTRUCTURE_REPOSITORY_URL>
git push infrastructure-repo split-infrastructure:main
```

Repository mới chỉ chứa code của thư mục đó + lịch sử commit liên quan, không chứa phần còn lại, không cần copy file thủ công.

## 6. Không xóa code khỏi monorepo ngay lập tức

Checklist trước khi xóa:

```text
[ ] Repository mới clone được
[ ] Application build được
[ ] Tests chạy thành công
[ ] Environment variables đã được cấu hình
[ ] CI/CD hoạt động
[ ] Deployment thành công
[ ] API contract hoạt động
[ ] Shared dependencies đã được xử lý
[ ] Secrets không bị đưa sang repository sai
```

Chỉ sau khi xong hết mới:

```bash
git rm -r apps/web
git commit -m "chore: move frontend to separate repository"
git push
```

## 7. Phải chỉnh sau khi tách

CI/CD workflow · Docker build context · Environment variables · Deployment configuration · README · API URL · CORS · Shared package dependencies · OpenAPI client generation · Versioning · Release process · Branch protection · Repository permissions · Secret configuration · Local development instructions.

## 8. Shared packages

Không tạo package chia sẻ business logic giữa frontend và backend. API, worker và scheduler được phép dùng chung domain/application code trong `apps/backend/core`. Qua ranh giới frontend–backend chỉ chia sẻ **contract**:

```text
OpenAPI schema
Generated TypeScript API client
JSON schema
Event schema
Public enums
```

```text
Backend is the source of truth.
```

Sau khi tách, với `packages/generated-api-client` chọn 1 trong 3: (1) generate client trong frontend CI từ OpenAPI URL, (2) publish private package, (3) commit generated client vào frontend repo. **MVP ưu tiên cách 1.**

## 9. Cấu trúc sau khi tách hoàn toàn

```text
havi-frontend
havi-backend
havi-infrastructure
```

Backend repo tiếp tục chứa API + worker + scheduler vì chúng dùng chung domain nghiệp vụ. Chỉ tách worker thành repository khác nếu sau này có team owner và chu kỳ phát hành thực sự độc lập.

## 10. Ánh xạ sang thiết kế Havi

| Màn thiết kế | App chịu trách nhiệm |
|---|---|
| Landing Page, Đăng Nhập, Onboarding, MVP App | `apps/web` |
| Auth/OTP, content CRUD, approval, connected accounts | `apps/backend/api` |
| Chế bản AI đa kênh, social listening, soạn reply | `apps/backend/worker` |
| Đăng bài giờ vàng, nhắc CRM Zalo/Email | `apps/backend/scheduler` |

Lưu ý bắt buộc theo triết lý Havi:

- Prompt chế bản và prompt seeding nằm **trong backend**, không bao giờ lộ ra frontend bundle.
- Approval state machine (`draft → pending_approval → approved → scheduled → publishing → published | failed`) do backend sở hữu; frontend chỉ gọi API và render trạng thái.
- Token nền tảng (Facebook/Google/Zalo) mã hoá bằng `TOKEN_ENCRYPTION_KEY`, chỉ backend giải mã.
