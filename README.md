# Havi

> AI marketing đa ngành cho tiệm nhỏ & cá nhân kinh doanh — bán **kết quả**, không bán công cụ.

Havi là "nhân viên marketing AI" cho người dùng **không rành công nghệ** (spa, F&B, môi giới BĐS, kỹ sư/chuyên gia). Một luồng khép kín, chạy bằng 1 nút:

1. **Nạp liệu thô** (<30s) — ảnh chụp vội, ghi âm, vài dòng gõ tay, hoặc webhook từ phần mềm bán hàng
2. **Lò phản ứng AI** — tự nhận diện ngành → xử lý media → 1 lần gọi LLM sinh 4–5 bản nội dung theo kênh
3. **Tổng đài phân phối** — tự đăng đa kênh đúng khung giờ vàng qua API chính thức
4. **Săn mồi & chăm sóc** — social listening + soạn câu trả lời **chờ chủ duyệt** (không bao giờ tự gửi); CRM vòng đời khách + FAQ 24/7 (chỉ tự động với câu đã duyệt sẵn)

Mọi báo cáo đo bằng **khách hỏi giá / khách đến tiệm / khách quay lại** — không phải like/reach.

## Cấu trúc repo

Monorepo `havi-platform`, frontend và backend tách kiến trúc nhưng chung repo:

| Thư mục | Nội dung |
|---|---|
| [`apps/web/`](apps/web/) | Next.js frontend |
| [`apps/backend/`](apps/backend/) | FastAPI API + Celery worker + scheduler + domain core |
| [`prototypes/`](prototypes/) | 6 prototype high-fidelity dạng `.dc.html` (mở trực tiếp trong trình duyệt) + `support.js` |
| [`docs/`](docs/) | Tài liệu được chia theo nhóm: handoff, product, architecture |

## Chạy local

Thứ tự: hạ tầng (Docker) → backend → frontend. Cần có Docker, Node 20+, và
[`uv`](https://docs.astral.sh/uv/) cài sẵn.

### 1. Hạ tầng — Postgres, Redis, MinIO

```bash
npm run infra:up
```

Khởi động Postgres (`5432`), Redis (`6379`) và MinIO S3-compatible (`9000`,
console `9001`), tự tạo bucket `havi-media`. Dừng bằng `npm run infra:down`.

### 2. Backend — FastAPI + Celery

```bash
cd apps/backend
cp .env.example .env
uv sync --extra dev --extra db --extra queue --extra storage
uv run alembic upgrade head   # chạy migration lên Postgres vừa khởi động ở bước 1
cd ../..
npm run dev:api
```

API ở <http://localhost:8000> (Swagger tại `/docs`, chỉ bật khi `HAVI_DEBUG=true`).
Chi tiết: [`apps/backend/README.md`](apps/backend/README.md).

Worker là bắt buộc nếu muốn thử tạo nội dung — `POST /content/jobs` chỉ đẩy job
vào hàng đợi, không có worker thì job nằm mãi ở `queued`:

```bash
npm run dev:worker
```

Scheduler (chỉ cần khi làm publish theo lịch, Tuần 7):

```bash
cd apps/backend && uv run celery -A scheduler.beat:celery_app beat -l info
```

**Local mặc định dùng mock LLM** (`HAVI_USE_MOCK_LLM=true`): bấm "Để Havi viết"
bao nhiêu lần cũng không tốn tiền API, và không cần API key để chạy được app.
Draft là văn mẫu ghép từ liệu thô, đủ để test luồng và UI.

Muốn test bằng model thật: điền `HAVI_GEMINI_API_KEY` rồi đặt
`HAVI_USE_MOCK_LLM=false`, khởi động lại worker.

Mock chỉ sống ở local. Đặt `HAVI_USE_MOCK_LLM=true` khi `HAVI_ENV` là `staging`
hoặc `production` sẽ làm backend **không khởi động được** — chặn ngay ở deploy,
vì để lọt thì chủ tiệm đăng văn mẫu lên Facebook thật mà tưởng AI viết.

Nếu tắt mock mà chưa có key nào, job chuyển sang `failed` kèm lý do và UI hiện
nút thử lại — đúng thiết kế, không phải hỏng.

### 3. Frontend — Next.js

```bash
npm install
npm run generate:api   # sinh TypeScript client từ OpenAPI của backend (cần backend chạy hoặc export được schema)
npm run dev:web
```

Web ở <http://localhost:3000>.

### Kiểm tra nhanh (trước khi commit)

`uv run pytest` cần Postgres thật đang chạy (`npm run infra:up`) — test auth
tự rollback transaction, không để lại dữ liệu.

```bash
npm run lint:web && npm run test:web && npm run build:web
npm run infra:up
cd apps/backend && uv run ruff check . && uv run pytest
```

### Tổng hợp lệnh

| Lệnh | Việc gì |
|---|---|
| `npm run infra:up` / `infra:down` | Bật/tắt Postgres, Redis, MinIO |
| `npm run migrate` | `alembic upgrade head` |
| `npm run dev:web` / `dev:api` | Chạy frontend / backend (dev, reload) |
| `npm run dev:worker` | Chạy Celery worker (cần cho tạo nội dung) |
| `npm run generate:api` | Sinh lại TypeScript client từ OpenAPI |
| `npm run lint:web` / `lint:api` | Lint frontend / backend |
| `npm run test:web` / `test:api` | Test frontend (Vitest) / backend (pytest) |
| `npm run build:web` | Production build frontend |

### Tài liệu chính

- [docs/README.md](docs/README.md) — index tài liệu theo từng nhóm
- [docs/handoff/HANDOFF.md](docs/handoff/HANDOFF.md) — mô tả chi tiết từng màn hình, fidelity, luồng duyệt bài
- [docs/product/ROADMAP.md](docs/product/ROADMAP.md) — lộ trình sản phẩm
- [docs/architecture/SYSTEM_ARCHITECTURE.md](docs/architecture/SYSTEM_ARCHITECTURE.md) — sơ đồ hệ thống, frontend và state nội dung
- [docs/architecture/TECHNICAL_SPEC.md](docs/architecture/TECHNICAL_SPEC.md) — đặc tả kỹ thuật
- [docs/architecture/REPOSITORY_STRATEGY.md](docs/architecture/REPOSITORY_STRATEGY.md) — chiến lược tổ chức repo

### Prototype (`prototypes/`)

| File | Màn hình |
|---|---|
| `Havi - MVP App.dc.html` | Sản phẩm chính (sidebar + 5 tab) |
| `Havi - Onboarding.dc.html` | Onboarding 3 bước |
| `Havi - Đăng Nhập.dc.html` | Đăng nhập / Đăng ký |
| `Havi - Landing Page.dc.html` | Landing page |
| `Havi - AI Marketing.dc.html` | Trang giới thiệu AI marketing |
| `Havi - Kiến Trúc Hệ Thống.dc.html` | Sơ đồ kiến trúc hệ thống |

> Các file `.dc.html` là **design reference** thể hiện giao diện & hành vi mong muốn — không phải production code để copy. Nhiệm vụ: tái tạo pixel-perfect trong codebase thật.

## Tech stack

- **Frontend:** Next.js 16 (App Router, TypeScript)
- **Backend:** FastAPI + Celery (worker & Beat), PostgreSQL, Redis
- **Contract:** OpenAPI — backend là nguồn sự thật, frontend sinh TypeScript client từ đó

## License

[MIT](LICENSE) © 2026 Huynh Nguyen
