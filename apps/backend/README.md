# Havi Backend

FastAPI + Celery. Chủ sở hữu database, secret, prompt production và approval state machine.
Frontend (`apps/web`) chỉ nói chuyện với backend qua HTTP + OpenAPI client.

## Cấu trúc

```text
apps/backend/
├── api/            # FastAPI entrypoint — routers theo domain
├── worker/         # Celery worker — chế bản AI, listening, soạn reply
├── scheduler/      # Celery Beat — đăng giờ vàng, refresh token, nhắc CRM
├── core/           # Domain dùng chung: config, enums, state machine, event_log
├── migrations/     # Alembic (chưa khởi tạo)
└── tests/
```

Ba process deploy độc lập nhưng dùng chung `core/`. Xem
[`docs/architecture/REPOSITORY_STRATEGY.md`](../../docs/architecture/REPOSITORY_STRATEGY.md).

## Chạy local

```bash
cd apps/backend && cp .env.example .env && uv sync --extra dev
```

```bash
cd apps/backend && uv run uvicorn api.main:app --reload --port 8000
```

- Swagger UI: <http://localhost:8000/docs> (chỉ bật khi `HAVI_DEBUG=true`)
- OpenAPI contract: <http://localhost:8000/openapi.json>
- Health: <http://localhost:8000/health>

Test và lint:

```bash
cd apps/backend && uv run pytest && uv run ruff check .
```

Worker và scheduler (cần Redis, cài thêm extra `queue`):

```bash
cd apps/backend && uv run --extra queue celery -A worker.celery_app:celery_app worker -l info
```

```bash
cd apps/backend && uv run --extra queue celery -A scheduler.beat:celery_app beat -l info
```

## Trạng thái hiện tại

Đây là **scaffold khoá contract**, chưa nối DB. Mọi endpoint nghiệp vụ đã có schema
request/response thật trong OpenAPI nhưng trả `501 Not Implemented`. Mục đích: `apps/web`
sinh được TypeScript client và dựng UI bằng fixture ngay, đúng thứ tự triển khai trong
[`SYSTEM_ARCHITECTURE.md`](../../docs/architecture/SYSTEM_ARCHITECTURE.md) §4.

Đã có thật:

- `core/enums.py` — public enums (kênh, trạng thái, ngành, gói cước…)
- `core/content_state.py` — state machine của content item, có test
- `core/config.py` — settings + secret boundary
- `core/events.py` — khung `event_log`
- `api/` — 12 domain router theo API surface trong `TECHNICAL_SPEC.md`

Chưa có: persistence layer, JWT thật, OAuth nền tảng, LLM call, adapter kênh.

## Ràng buộc không được phá

1. Mặc định `review_first` — không nội dung nào lên mạng khi chủ chưa duyệt.
2. Reply cho khách **không bao giờ** có `full_auto`, trừ FAQ chủ đã duyệt sẵn từng câu.
3. Prompt chế bản và prompt seeding nằm trong backend, không lộ ra frontend bundle.
4. Token nền tảng mã hoá bằng `TOKEN_ENCRYPTION_KEY`, không xuất hiện trong response.
5. Mọi query scope theo `workspace_id` — không leak chéo tenant.
6. Publish job có idempotency key — không đăng đúp.
7. Câu seeding luôn minh bạch danh tính, không giả danh khách hàng.
