# Havi

> **Nền tảng quản trị và vận hành mạng xã hội** dành cho doanh nghiệp và đội ngũ
> social. Quản lý kênh, nội dung, lịch đăng, hội thoại và thành viên tại một nơi.
>
> *Mọi kênh trong tầm kiểm soát. Mọi hoạt động đều có thể truy vết. Social vận
> hành nhẹ đầu hơn.*
>
> **Tầm nhìn:** trung tâm kiểm soát đáng tin cậy cho toàn bộ sự hiện diện và
> hoạt động mạng xã hội của doanh nghiệp — *the trusted control plane for
> business social media operations*. Chi tiết 5–10 năm ở
> [ROADMAP §1b](docs/product/ROADMAP.md).
> Những gì được phép giới thiệu là đã chạy nằm ở
> [PRODUCT_CONTRACT](docs/product/PRODUCT_CONTRACT.md).

## Havi là chỗ ngồi làm việc của người trực kênh

Người mở Havi mỗi ngày thường **không phải chủ**. Đó là nhân viên trực page, con
chủ tiệm, nhân viên resort được giao Facebook và TikTok. Chủ trả tiền để có quyền
kiểm soát và dấu vết; nhân viên dùng để có **một màn hình thay vì năm**.

Vì vậy màn chính của Havi là **một hàng đợi việc**: tin nhắn, bình luận, hỏi giá,
nháp chờ duyệt, bài đăng lỗi, kênh mất quyền — bốn nguồn, một danh sách, xếp theo
thiệt hại khi bỏ sót chứ không theo thời gian.

Mỗi việc có hai đường đi ra và **cả hai đều đúng**: xử lý trong Havi, hoặc bấm
sang thẳng nền tảng. Thứ tốn thời gian không phải lúc trả lời — mà là lúc đi tìm
xem có gì cần trả lời.

Havi quản trị **hệ thống social của bạn** — không quản trị mục tiêu kinh doanh
của bạn. Phạm vi đầy đủ (chín thứ) định nghĩa **một lần duy nhất** ở
[PRODUCT_CONTRACT §Product scope](docs/product/PRODUCT_CONTRACT.md): tài khoản &
kết nối, kho nội dung, lịch đăng, hội thoại, thành viên & quyền, quy trình
duyệt, audit log, sức khoẻ kênh, báo cáo vận hành.

Hết. Không kéo sang mục tiêu kinh doanh, lộ trình tăng trưởng, hay chứng minh
doanh thu.

## Vai trò của AI

Havi được định vị là **trợ lý AI điều hành social**, nhưng lời hứa phải đi theo
năng lực đang chạy. Hiện tại AI soạn nháp nội dung; hàng đợi, bản tin và phân
loại inbox dùng dữ liệu cùng luật xác định để dễ kiểm chứng. Business Memory,
phát hiện bất thường và vòng lặp agent chủ động vẫn là hướng phát triển, chưa
phải quyền lợi đang bán. Ranh giới chi tiết nằm ở
[PRODUCT_CONTRACT](docs/product/PRODUCT_CONTRACT.md).

AI **không** tự đặt mục tiêu, **không** hứa marketing, và mọi hành động ra nền
tảng đều nằm trong quyền hạn và quy trình duyệt của con người.

Đăng bài và lên lịch cũng nằm cùng nhóm này: chúng là **tính năng hỗ trợ** bên
trong một nền tảng quản trị, không phải lý do Havi tồn tại. Một công cụ chỉ biết
đẩy bài lên kênh thì Canva và CapCut đã làm rồi.

## Điều gì còn lại khi nền tảng đổi luật

Havi **không** miễn nhiễm với việc Meta hay TikTok siết quyền API. Mất quyền là
mất đường ra kênh, và Havi sẽ hiện rõ kênh đang hỏng thay vì im lặng.

Thứ **không** mất, vì nó nằm trong workspace chứ không nằm ở nền tảng:

* kho nội dung đã duyệt và lịch sử từng phiên bản;
* ai duyệt cái gì, lúc nào, kết quả ra sao;
* giọng thương hiệu và danh sách điều không được hứa;
* lịch sử hội thoại với từng khách;
* cấu trúc thương hiệu, chi nhánh và phân quyền.

Đó là **trí nhớ vận hành**. Nền tảng mới xuất hiện thì doanh nghiệp nối Havi vào
nền tảng đó và phần đã tích luỹ vẫn còn nguyên — thay ống dẫn, không xây lại từ
đầu. Công cụ nào chỉ là đường ống thì chết cùng đường ống.

Hệ quả cho việc ưu tiên: audit log, lịch sử phiên bản và khả năng xuất dữ liệu
**không phải** tính năng phụ để làm sau. Chúng chính là thứ được bán.

## Những gì Havi không làm

Mỗi mục dưới đây từng tồn tại trong sản phẩm rồi bị gỡ. Đưa lại là một quyết
định sản phẩm, không phải một lần refactor:

* **Không tự đăng khi chưa ai duyệt.** Quy trình soạn → duyệt → đăng là ràng
  buộc, không phải tuỳ chọn.
* **Không dựng hay sửa video.** Người dùng quen CapCut hơn bất cứ trình sửa nào
  chạy trong trình duyệt. Havi nhận clip đã xong và đăng.
* **Không đặt mục tiêu hộ.** Không có Goal, Roadmap, Evidence, hay "tiến độ mục
  tiêu" trên dashboard.
* **Không hứa khách đến, doanh thu, hay tăng trưởng.** Havi báo cáo việc nó đã
  làm; kết quả kinh doanh thuộc về doanh nghiệp.
* **Không chạy quảng cáo, không tiêu tiền của bạn.** Havi không tự tạo chiến
  dịch, không đổi ngân sách, không bật/tắt quảng cáo và không giữ tiền quảng
  cáo. Ranh giới đầy đủ ở [ROADMAP §1c](docs/product/ROADMAP.md).

Nếu còn dùng từ **"chiến dịch"**, nó chỉ có nghĩa là *một nhóm nội dung được tổ
chức cùng nhau* — không phải cam kết tạo ra kết quả kinh doanh.

### Bài kiểm cho mọi tính năng mới

> Nó có giúp doanh nghiệp **kiểm soát social tốt hơn**, **giảm thao tác**, hoặc
> **giảm nguy cơ bỏ sót** không?

Không trả lời được câu đó thì nó không thuộc Havi — kể cả khi nó hay.

## Chỉ số

North Star hướng người dùng là **Time Havi Saved**. Đây là số ước tính minh bạch:
màn hình phải hiện các hành động đã đếm và giả định số phút cho từng hành động,
không được trình bày như thời gian bấm đồng hồ thực tế.

Đội vận hành theo dõi các chỉ số sức khoẻ **nội bộ**: tỷ lệ đăng thành công, số
kết nối đang hoạt động, độ trễ đồng bộ, số bài đăng thất bại, số nội dung chờ
duyệt, số hội thoại chưa xử lý, thời gian xử lý lỗi, tỷ lệ tiếp tục sử dụng, số
workspace trả phí. Đây là telemetry, không phải triết lý sản phẩm.

## Repository Layout

This is the `havi-platform` monorepo. Frontend and backend are separated by
runtime boundary but live in one repository.

| Path | Purpose |
|---|---|
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | 🏛️ Master Architecture Blueprint & Mermaid Sequence Diagrams |
| [`apps/web/`](apps/web/) | Next.js frontend |
| [`apps/backend/`](apps/backend/) | FastAPI API, Celery worker, scheduler, and domain core |
| [`docs/`](docs/) | Handoff, product, and architecture documentation |

## Local Development

### One-Click Devbox (Recommended)

Run a single command to start Docker infrastructure, run DB migrations, and launch Backend API, Celery Worker, Beat, and Next.js Web:

```bash
npm run dev
# Or: npm run devbox
```

This starts:
- **Web App**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Postgres, Redis, MinIO**: Managed in background via Docker

---

### Nhắc gia hạn qua Telegram (tuỳ chọn)

Thanh toán VietQR không có auto-renew, nên mỗi tháng khách phải chủ động trả tiếp.
Banner nhắc trong app không tới được ca churn thật — người sắp rời đi chính là
người đã ngừng mở app. Kênh Telegram nhắc **đội vận hành** để gọi khách.

```bash
bash scripts/telegram-setup.sh <BOT_TOKEN>
```

Script tự lấy `chat_id`, gửi một tin thử, rồi in ra hai dòng cần dán. Token lấy
từ `@BotFather` trong Telegram (`/newbot`).

Hai biến phải nằm ở **`apps/backend/.env`**, không phải `.env` gốc: backend chạy
từ `apps/backend/` và `env_file` là đường dẫn tương đối. Để rỗng thì tính năng tự
tắt và chỉ ghi log — không lỗi.

---

### Development Test Accounts

Use these pre-configured test credentials to sign in directly at `http://localhost:3000/login`:

| Account Name | Email | Password | Industry | Workspace Status |
|---|---|---|---|---|
| **Chị Hương** | `huong@havi.vn` | `matkhau123` | Spa & Beauty | Active Workspace |
| **Chị Mai** | `testuser@havi.vn` | `matkhau123` | Spa & Beauty | Active Workspace |
| **Mai Inbox** | `mai.inbox@havi.vn` | `matkhau123` | Spa & Beauty | Active Workspace |

---

### Manual Step-by-Step Setup

If you prefer to start services individually:

#### 1. Infrastructure: Postgres, Redis, MinIO

```bash
npm run infra:up
```

This starts Postgres on `5432`, Redis on `6379`, and S3-compatible MinIO on
`9000` with console on `9001`. The `havi-media` bucket is created automatically.
Stop the stack with:

```bash
npm run infra:down
```

### 2. Backend: FastAPI and Celery

```bash
cd apps/backend
cp .env.example .env
uv sync --extra dev --extra db --extra queue --extra storage
uv run alembic upgrade head
cd ../..
npm run dev:api
```

The API runs at <http://localhost:8000>. Swagger is available at `/docs` when
`HAVI_DEBUG=true`. See [`apps/backend/README.md`](apps/backend/README.md) for
backend details.

The worker is required for content generation. `POST /content/jobs` only queues a
job; without the worker, jobs remain `queued`.

```bash
npm run dev:worker
```

The scheduler is required for scheduled publishing:

```bash
cd apps/backend && uv run celery -A scheduler.beat:celery_app beat -l info
```

Local development uses the mock LLM by default (`HAVI_USE_MOCK_LLM=true`). This
lets you test the workflow without API keys or model spend. To call a real model,
set a provider key, set `HAVI_USE_MOCK_LLM=false`, and restart the worker.

Mock LLM and fake publisher are allowed only when `HAVI_ENV=local`. The backend
refuses to start in staging or production if either fake mode is enabled.

### 3. Frontend: Next.js

```bash
npm install
npm run generate:api
npm run dev:web
```

The web app runs at <http://localhost:3000>.

#### Local Web Routes & Preview URLs

| Route | Local URL | Description |
|---|---|---|
| **Landing Page** | [http://localhost:3000/gioi-thieu](http://localhost:3000/gioi-thieu) | Public product overview and workflow showcase |
| **Onboarding** | [http://localhost:3000/onboarding](http://localhost:3000/onboarding) | Business setup and channel connection |
| **Sign Up** | [http://localhost:3000/dang-ky](http://localhost:3000/dang-ky) | Email & password registration screen |
| **Sign In** | [http://localhost:3000/dang-nhap](http://localhost:3000/dang-nhap) | Email & password login screen |
| **Content Creation** | [http://localhost:3000/noi-dung](http://localhost:3000/noi-dung) | Raw material input, AI draft generation, and 1-click approval |
| **Calendar** | [http://localhost:3000/lich-dang](http://localhost:3000/lich-dang) | Vietnam-timezone schedule grid with ISO offset rescheduling |
| **Reports** | [http://localhost:3000/bao-cao](http://localhost:3000/bao-cao) | Publishing and conversation operations from workspace data |
| **Internal Operations** | [http://localhost:3000/noi-bo/van-hanh](http://localhost:3000/noi-bo/van-hanh) | Pilot operational metrics (job latency, token usage, error rates) |

## Checks Before Commit

Backend tests need the local Postgres stack:

```bash
npm run lint:web && npm run test:web && npm run build:web
npm run infra:up
cd apps/backend && uv run ruff check . && uv run pytest
```

Local E2E core flow:

```bash
npm run infra:up
npm run migrate
npm run e2e
```

`npm run e2e` uses mock LLM output and `FakePublisher` in-process. It creates an
isolated email/workspace inside the test transaction, does not call paid model
APIs, and does not publish to Facebook.

## CI / GitHub Actions

The GitHub Actions workflow (`.github/workflows/ci.yml`) checks pull requests and
pushes to `main` / `dev`:

- **Web:** `npm run lint:web`, `npm run test:web`, `npm run build:web`
- **Backend:** `ruff check .`, `alembic upgrade head`, and `pytest` with Postgres
  and Redis service containers

## Command Reference

| Command | Purpose |
|---|---|
| `npm run infra:up` / `infra:down` | Start/stop Postgres, Redis, and MinIO |
| `npm run migrate` | Run `alembic upgrade head` |
| `npm run dev:web` / `dev:api` | Run frontend/backend in development mode |
| `npm run dev:worker` | Run the Celery worker |
| `npm run generate:api` | Regenerate the TypeScript OpenAPI client |
| `npm run lint:web` / `lint:api` | Lint frontend/backend |
| `npm run test:web` / `test:api` | Run frontend/backend tests |
| `npm run e2e` | Run the isolated signup-to-report smoke test |
| `npm run build:web` | Build the production frontend |

## Main Documentation

- [docs/README.md](docs/README.md) — documentation index
- [docs/handoff/DEPLOYMENT.md](docs/handoff/DEPLOYMENT.md) — configuration,
  deployment, Facebook setup, quota, rate limits, required processes, and beta
  checklist
- [docs/product/ROADMAP.md](docs/product/ROADMAP.md) — product roadmap
- [docs/architecture/SYSTEM_ARCHITECTURE.md](docs/architecture/SYSTEM_ARCHITECTURE.md)
  — architecture and process boundaries
- [docs/architecture/TECHNICAL_SPEC.md](docs/architecture/TECHNICAL_SPEC.md) —
  technical specification
- [docs/architecture/REPOSITORY_STRATEGY.md](docs/architecture/REPOSITORY_STRATEGY.md)
  — repository strategy

## Tech Stack

- **Frontend:** Next.js 16, App Router, TypeScript
- **Backend:** FastAPI, Celery worker/beat, PostgreSQL, Redis
- **Contract:** OpenAPI generated from the backend and consumed by the frontend

## License

[MIT](LICENSE) © 2026 Huynh Nguyen
