# Havi Backend

FastAPI + Celery. Chủ sở hữu database, secret, prompt production và approval state machine.
Frontend (`apps/web`) chỉ nói chuyện với backend qua HTTP + OpenAPI client.

## Cấu trúc

```text
apps/backend/
├── api/            # FastAPI entrypoint — routers theo domain
├── worker/         # Celery worker — chế bản AI, listening, soạn reply
├── scheduler/      # Celery Beat — đăng giờ vàng, refresh token, nhắc CRM
├── core/           # Scaffold chuyển tiếp: config, enums, state machine, event_log
├── domain/
│   └── models/     # SQLAlchemy models — nguồn sự thật của DB schema
├── migrations/     # Alembic (đã khởi tạo, xem migrations/README.md)
└── tests/
```

Ba process deploy độc lập nhưng dùng chung `core/`. Xem
[`docs/architecture/REPOSITORY_STRATEGY.md`](../../docs/architecture/REPOSITORY_STRATEGY.md).

## Chạy local

Khởi động Postgres/Redis/MinIO (từ root repo, tài liệu duy nhất — không cần biết gì thêm):

```bash
docker compose up -d
```

Cài backend:

```bash
cd apps/backend && cp .env.example .env && uv sync --extra dev --extra db --extra storage
```

Chạy migration (cần extra `db`, xem [`migrations/README.md`](migrations/README.md)):

```bash
cd apps/backend && uv run alembic upgrade head
```

```bash
cd apps/backend && uv run uvicorn api.main:app --reload --port 8000
```

- Swagger UI: <http://localhost:8000/docs> (chỉ bật khi `HAVI_DEBUG=true`)
- OpenAPI contract: <http://localhost:8000/openapi.json>
- Health: <http://localhost:8000/health>

Test và lint (`test_auth_flow.py` cần Postgres thật — `docker compose up -d` ở
root trước; mỗi test tự rollback transaction, không để lại dữ liệu):

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

`/auth/*`, `/workspaces/*`, `/brand-profile`, `/media` và `/content` (tạo/đọc job
+ list item) chạy thật (Postgres + MinIO + Redis/Celery). Phần approve/reject/
versions của `/content` và 7 router domain còn lại vẫn trả `501 Not Implemented` — có schema request/response thật
trong OpenAPI để `apps/web` sinh TypeScript client và dựng UI fixture trước.

Đã có thật:

- `core/enums.py` — public enums (kênh, trạng thái, ngành, gói cước…)
- `core/content_state.py` — state machine của content item, có test
- `core/config.py` — settings + secret boundary
- `core/events.py` — khung `event_log` (Pydantic contract; bảng thật là `domain/models/audit.py:EventLog`, chưa insert)
- `core/phone.py` — chuẩn hoá SĐT Việt Nam (0xxxxxxxxx → +84…), chỉ dùng cho Zalo OA
- `core/security.py` — JWT access token, hash password (Argon2id), hash mã 6 số/refresh token
- `core/file_signatures.py` — kiểm magic bytes; presigned POST không kiểm nội dung file
- `domain/models/` — SQLAlchemy models thật: `User`, `OtpChallenge`, `RefreshSession`,
  `Workspace`, `WorkspaceMember`, `BrandProfile`, `EventLog` — migrate được lên
  Postgres thật (`uv run alembic upgrade head`), verify bằng `alembic check`.
- `adapters/persistence/` — session async (`db.py`, commit-per-request) + repository
  cho user/OTP/refresh session/workspace/workspace member/brand profile/media.
- `adapters/storage/object_storage.py` — presigned POST lên S3-compatible; dùng POST
  thay PUT vì chỉ POST cho phép condition `content-length-range` (chặn size ở storage).
- `application/services/` — `auth_service.py` (email+mật khẩu, JWT), `workspace_service.py`
  (workspace/member), `brand_profile_service.py` (giọng văn/từ cấm/FAQ),
  `media_service.py` (upload ticket, xác nhận upload, tag). Exception thuần (không
  phụ thuộc FastAPI), router dịch sang HTTP status.
- `api/` — 12 domain router theo API surface trong `TECHNICAL_SPEC.md`; `auth.py`,
  `workspaces.py`, `brand_profile.py`, `media.py`, `content.py` (một phần) đã nối
  DB/storage/queue thật, 7 domain router khác còn `501`.
- `domain/ports/llm.py` + `domain/policies/provider_router.py` — multi-provider LLM:
  Gemini ưu tiên, fallback Anthropic/OpenAI khi lỗi/quota/output không đạt.
- `adapters/llm/` — Gemini/Anthropic/OpenAI qua REST (httpx, không SDK riêng cho
  từng provider) + `fake.py` để test không cần API key.
- `application/services/content_engine.py` — một job = một lần gọi LLM sinh nhiều
  bản theo kênh; validate schema + banned claims trước khi lưu draft.
- `worker/tasks.py:generate_drafts` — Celery job thật chạy Content Engine.
- `api/deps.py:PathWorkspaceMemberDep` — chặn 403 khi JWT hợp lệ nhưng không
  phải thành viên của `{workspace_id}` trong path (khác `WorkspaceDep`, đọc từ JWT).
- `tests/test_auth_flow.py`, `test_workspace_flow.py`, `test_brand_profile_flow.py`,
  `test_media_flow.py` — test thật trên Postgres + MinIO (không mock), mỗi test
  rollback transaction DB riêng — xem `tests/conftest.py`. Lưu ý: object đã upload
  **không** rollback (storage không có transaction), nên test media để lại object
  rác trong bucket dev.

Chưa có: OAuth nền tảng, adapter publish kênh, email provider thật (dùng
`debug_code` tạm), endpoint logout/revoke session, cache brand profile cho worker,
lifecycle/cleanup cho asset `pending` bị bỏ dở, quota LLM theo workspace, approve/
reject/version cho content item, và repository cho các domain còn lại (calendar,
inbox, leads, analytics, billing, connections).

**LLM chưa verify được với provider thật** — chưa có API key nào trong `.env`, nên
`ProviderRouter` bỏ qua cả ba provider và job sẽ `failed` với reason "không có
provider nào được cấu hình". Toàn bộ luồng đã test bằng `adapters/llm/fake.py`;
điền `HAVI_GEMINI_API_KEY` là chạy thật được.

## Ràng buộc không được phá

1. Mặc định `review_first` — không nội dung nào lên mạng khi chủ chưa duyệt.
2. Reply cho khách **không bao giờ** có `full_auto`, trừ FAQ chủ đã duyệt sẵn từng câu.
3. Prompt chế bản và prompt seeding nằm trong backend, không lộ ra frontend bundle.
4. Token nền tảng mã hoá bằng `TOKEN_ENCRYPTION_KEY`, không xuất hiện trong response.
5. Mọi query scope theo `workspace_id` — không leak chéo tenant.
6. Publish job có idempotency key — không đăng đúp.
7. Câu seeding luôn minh bạch danh tính, không giả danh khách hàng.
