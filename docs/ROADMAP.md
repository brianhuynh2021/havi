# Havi — Product & Engineering Roadmap

## 1. Mục tiêu sản phẩm

Havi là nhân viên marketing AI dành cho hộ kinh doanh và doanh nghiệp nhỏ tại Việt Nam. Tên **Havi** được ghép từ **Ha** (Harry) và **Vi** (Việt Nam).

MVP cần chứng minh được một vòng giá trị hoàn chỉnh:

```text
Nạp ảnh hoặc ý tưởng
        ↓
Havi tạo nội dung đa kênh
        ↓
Chủ doanh nghiệp duyệt
        ↓
Hệ thống đăng đúng lịch
        ↓
Havi tổng hợp kết quả dễ hiểu
```

Mọi nội dung gửi ra ngoài mặc định phải được người dùng duyệt. Chỉ dùng API chính thức của các nền tảng.

## 2. Phạm vi MVP

### Phải có

- Đăng ký và đăng nhập bằng số điện thoại/OTP.
- Tạo/chọn workspace và phân quyền owner/marketer/reviewer.
- Thiết lập ngành, giọng thương hiệu và từ ngữ cấm.
- Upload ảnh, nhập nội dung thô và quản lý media cơ bản.
- Sinh một lần nhiều phiên bản nội dung theo từng kênh.
- Sửa, lưu phiên bản, duyệt và lên lịch bài.
- Kết nối và đăng Facebook Page; chuẩn bị adapter cho Google Business.
- Worker bất đồng bộ, retry, idempotency và dead-letter handling.
- Lịch nội dung và trạng thái publish.
- Dashboard tối thiểu: số bài, trạng thái đăng, tương tác thu thập được.
- Audit log cho các hành động tạo, sửa, duyệt và đăng.

### Chưa làm trong MVP

- Crawler hoặc tự động quét group không qua API chính thức.
- CRM đầy đủ, marketing automation phức tạp.
- Tự gửi câu trả lời AI chưa được duyệt.
- A/B testing tự động và tối ưu giờ đăng bằng machine learning.
- TikTok, YouTube và nhiều cổng thanh toán cùng lúc.
- Mobile app native.

## 3. Kiến trúc đích trong monorepo

```text
havi-platform/
├── apps/
│   ├── web/                  # Next.js
│   └── backend/
│       ├── api/              # FastAPI entrypoint
│       ├── worker/           # Celery worker entrypoint
│       ├── scheduler/        # Celery Beat entrypoint
│       ├── core/             # Domain và application services dùng chung
│       └── migrations/       # Alembic
├── packages/
│   ├── generated-api-client/
│   └── frontend-config/
├── contracts/
│   ├── openapi/
│   └── events/
├── infrastructure/
├── docs/
├── scripts/
├── tests/integration/
└── docker-compose.yml
```

Ranh giới phải được giữ từ đầu:

- Frontend chỉ giao tiếp với backend qua HTTP/OpenAPI.
- Backend sở hữu business logic, database, migrations và secrets.
- API, worker và scheduler dùng chung backend core nhưng có process/deployment độc lập.
- Infrastructure không chứa business logic.
- Event gửi vào queue phải có schema, version và idempotency key.

Kiến trúc này cho phép tách sau này thành `havi-frontend`, `havi-backend` và `havi-infrastructure` mà không phải thiết kế lại hệ thống.

## 4. Kế hoạch triển khai MVP — 10 tuần

Ước lượng này phù hợp với nhóm nhỏ gồm 1 frontend, 1 backend và 1 người phụ trách sản phẩm/thiết kế/QA bán thời gian. Nếu chỉ có một full-stack developer, nên dự kiến 14–18 tuần.

### Giai đoạn 0 — Chốt sản phẩm và kỹ thuật (Tuần 1)

Đầu ra:

- Chốt persona đầu tiên, khuyến nghị chọn một ngành duy nhất để pilot.
- Chốt hành trình chính và tiêu chí thành công của pilot.
- Chốt nhà cung cấp OTP, object storage, PostgreSQL, Redis và nơi deploy.
- Tạo ADR cho authentication, multi-tenancy, queue, media và deployment.
- Chốt OpenAPI conventions, error format và event envelope.
- Tạo backlog và acceptance criteria cho MVP.

Hoàn thành khi toàn đội thống nhất phạm vi “phải có” và “chưa làm”, không còn dependency chưa có owner.

### Giai đoạn 1 — Monorepo và nền tảng vận hành (Tuần 2)

Đầu ra:

- Scaffold `web`, `backend/api`, `worker`, `scheduler` và migrations.
- Local stack bằng Docker Compose: PostgreSQL, Redis, object storage và mail/SMS stub.
- CI chạy lint, type-check, unit test, migration check và build image.
- Dev/staging environment, secret management và `.env.example`.
- Logging có request/job ID; health/readiness endpoints.
- Sinh TypeScript API client từ OpenAPI trong CI.

Hoàn thành khi một commit có thể tự động test và deploy bản “hello world” của FE, API và worker lên staging.

### Giai đoạn 2 — Identity, workspace và brand profile (Tuần 3)

Đầu ra:

- OTP login/registration, refresh token và logout.
- Workspace, member roles và `active_workspace_id`.
- Middleware bắt buộc scope mọi query theo workspace.
- Onboarding ngành nghề, brand voice, banned claims và FAQ.
- Audit log ban đầu.

Hoàn thành khi test chứng minh người dùng workspace A không thể đọc hoặc sửa dữ liệu workspace B.

### Giai đoạn 3 — Media và Content Engine (Tuần 4–5)

Đầu ra:

- Upload trực tiếp lên object storage bằng signed URL.
- Media library và metadata.
- Tạo content job từ ảnh, ghi chú hoặc văn bản.
- Worker xử lý job và gọi LLM một lần để tạo các phiên bản theo kênh.
- Prompt sử dụng brand profile, có structured output và validation.
- Theo dõi token, latency, chi phí và lỗi theo job.
- UI tạo nội dung, loading/progress và draft cards.

Hoàn thành khi người dùng có thể nạp dữ liệu và nhận draft hợp lệ; job lỗi có thể retry mà không tạo nội dung trùng.

### Giai đoạn 4 — Editor, duyệt và lịch nội dung (Tuần 6)

Đầu ra:

- Content editor và version history.
- Approval queue, duyệt từng bài và duyệt hàng loạt.
- State machine được enforce ở backend.
- Lịch tuần/tháng và đổi thời gian đăng.
- Ghi `approved_by`, `approved_at` và audit event.

Hoàn thành khi không có cách nào chuyển bài chưa duyệt sang publish trong chế độ `review_first`.

### Giai đoạn 5 — Kết nối và đăng Facebook Page (Tuần 7–8)

Đầu ra:

- OAuth, mã hóa token, refresh/reconnect và connection status.
- Adapter Facebook Page theo API chính thức.
- Scheduler tạo publish job; worker thực thi publish.
- Idempotency, retry có backoff và phân loại lỗi.
- UI hiển thị `scheduled`, `publishing`, `published` và `failed` cùng hướng xử lý.
- Thu thập engagement snapshot tối thiểu nếu API cho phép.

Hoàn thành khi một bài đã duyệt được đăng đúng lịch lên tài khoản pilot và thao tác retry không đăng trùng.

### Giai đoạn 6 — Báo cáo, hardening và pilot (Tuần 9)

Đầu ra:

- Dashboard bài đăng, lỗi, tương tác và xu hướng theo tuần.
- Rate limiting, quota và chống abuse.
- Backup/restore rehearsal, alerting và runbook sự cố.
- Security review cho auth, upload, OAuth token và tenant isolation.
- E2E test cho toàn bộ happy path và các lỗi chính.
- Seed/demo workspace phục vụ onboarding khách thử nghiệm.

Hoàn thành khi staging vượt qua checklist release và có thể truy vết một request từ web tới API, queue và worker.

### Giai đoạn 7 — Closed beta (Tuần 10)

Đầu ra:

- Onboard 5–10 khách hàng thuộc cùng một nhóm ngành.
- Theo dõi funnel và phỏng vấn người dùng hàng tuần.
- Sửa lỗi P0/P1, tối ưu prompt/copy dựa trên dữ liệu thực.
- Đo chi phí trên mỗi draft và mỗi bài đăng thành công.
- Quyết định phạm vi cho phiên bản tiếp theo.

Hoàn thành khi có dữ liệu sử dụng thực đủ để quyết định tiếp tục, thay đổi ngách hoặc mở thêm kênh.

## 5. Chỉ số quyết định MVP thành công

- Ít nhất 70% người dùng pilot tạo được draft đầu tiên trong ngày onboarding.
- Thời gian từ nạp liệu đến draft sẵn sàng dưới 90 giây ở p95.
- Ít nhất 60% draft được duyệt sau khi người dùng chỉnh sửa không quá nhiều.
- Tỷ lệ publish thành công trên 95%, không có bài đăng trùng.
- Ít nhất 50% khách pilot hoạt động hàng tuần sau bốn tuần.
- Chi phí AI và hạ tầng trên mỗi workspace nằm trong biên lợi nhuận của gói dự kiến.
- Không có sự cố rò rỉ dữ liệu chéo workspace hoặc secrets ra frontend.

## 6. Sau MVP

Ưu tiên dựa trên dữ liệu pilot, không triển khai đồng thời:

1. Google Business adapter và inbox/review có người duyệt.
2. Zalo OA notification/approval và FAQ đã được chủ duyệt.
3. Lead pipeline đơn giản và attribution “khách đến từ đâu”.
4. Billing với một cổng thanh toán phù hợp thị trường Việt Nam.
5. TikTok/YouTube khi đã xác nhận nhu cầu và quyền API.
6. A/B testing và đề xuất giờ đăng sau khi có đủ dữ liệu.

## 7. Các quyết định cần chốt trước khi bắt đầu sprint đầu tiên

- Ngành pilot đầu tiên.
- Web responsive hay desktop-first cho MVP.
- Nhà cung cấp OTP và chi phí dự kiến.
- Cloud/deployment target và khu vực lưu dữ liệu.
- Tài khoản Facebook developer và quyền API có thể xin được.
- Chính sách lưu/xóa media và dữ liệu người dùng.
- Ai chịu trách nhiệm vận hành và hỗ trợ khách pilot.
