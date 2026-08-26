# Havi Backend

FastAPI + Celery backend. This app owns database state, secrets, production
prompts, and the approval state machine. The frontend (`apps/web`) talks to the
backend only through HTTP and the generated OpenAPI client.

## Structure

```text
apps/backend/
├── api/            # FastAPI entrypoint and domain routers
├── worker/         # Celery worker: AI generation, future listening/replies
├── scheduler/      # Celery Beat: scheduled publishing, token refresh, CRM jobs
├── core/           # Transitional config/enums/state-machine utilities
├── domain/
│   └── models/     # SQLAlchemy models, DB schema source
├── migrations/     # Alembic migrations
└── tests/
```

API, worker, and scheduler deploy as separate processes while sharing backend
domain/application code. See
[`docs/architecture/REPOSITORY_STRATEGY.md`](../../docs/architecture/REPOSITORY_STRATEGY.md).

## Local Setup

Start Postgres, Redis, and MinIO from the repository root:

```bash
docker compose up -d
```

Install backend dependencies:

```bash
cd apps/backend
cp .env.example .env
uv sync --extra dev --extra db --extra queue --extra storage
```

Run migrations:

```bash
uv run alembic upgrade head
```

Run the API:

```bash
uv run uvicorn api.main:app --reload --port 8000
```

- Swagger UI: <http://localhost:8000/docs> when `HAVI_DEBUG=true`
- OpenAPI contract: <http://localhost:8000/openapi.json>
- Health: <http://localhost:8000/health>

Run tests and lint:

```bash
uv run pytest
uv run ruff check .
```

Tests use real Postgres and rollback each DB transaction. Object storage is not
transactional, so media tests can leave development objects in the bucket.

Run worker and scheduler:

```bash
uv run --extra queue celery -A worker.celery_app:celery_app worker -l info
uv run --extra queue celery -A scheduler.beat:celery_app beat -l info
```

## Current Implementation

Implemented with real persistence/integration boundaries:

- auth, refresh sessions, password reset contracts
- workspaces and workspace members
- brand profile
- media upload tickets and object-storage metadata
- content jobs, content engine, approval, version history, calendar
- quota and rate limits
- platform connections and Facebook publishing adapter
- fake publisher for local/test
- publish scheduler, retry, dead-letter handling, and event logging
- analytics dashboard, reports, events, and operations metrics
- local E2E smoke test for signup -> draft -> approve -> fake publish -> report

Important files:

- `core/enums.py` — public enums
- `core/content_state.py` — content item state machine
- `core/config.py` — settings and deployment guardrails
- `core/events.py` — event-log contract
- `core/security.py` — JWT, Argon2id password hashing, OTP/refresh hashing
- `core/file_signatures.py` — upload magic-byte checks
- `domain/models/` — SQLAlchemy models
- `adapters/persistence/` — repositories
- `adapters/storage/object_storage.py` — S3-compatible presigned uploads
- `adapters/llm/` — Gemini/Anthropic/OpenAI REST adapters and fake provider
- `application/services/content_engine.py` — one job creates multiple drafts
- `application/services/publish_service.py` — publish dispatch/run/retry logic
- `worker/tasks.py` — Celery task entrypoints
- `scheduler/tasks.py` / `scheduler/beat.py` — scheduled command entrypoints

## Local AI and Publishing Modes

Local defaults use mock LLM and fake publisher so development is free and does
not publish real posts. These modes are forbidden outside `HAVI_ENV=local`; the
backend refuses to start in staging/production if they are enabled.

Set `HAVI_USE_MOCK_LLM=false` and configure a provider key to call a real model.
Set `HAVI_USE_FAKE_PUBLISHER=false` only when you intend to publish through a real
connected platform account.

### Media must be reachable from the platform, not from you

Facebook, TikTok, YouTube and Google Business do not receive your image or video
bytes. They receive a **link**, and fetch it themselves from their own servers.

So `HAVI_MEDIA_PUBLIC_URL=http://localhost:9000/havi-media` — the local default —
works perfectly in your browser and means *Facebook's own machine* to Facebook.
The post is fine; only the link is unusable. What comes back says nothing about
that:

    [100] (#100) url should represent a valid URL
    [6000] There was a problem uploading your video file.

Havi now refuses to send an unreachable link and says so plainly instead, and
`HAVI_ENV=production` will not start with one. To publish real media from a dev
machine, point `HAVI_MEDIA_PUBLIC_URL` at something the outside world can open —
a tunnel (`cloudflared tunnel --url http://localhost:9000`, `ngrok http 9000`) or
a real object-storage bucket.

## Staging / Production

Read [docs/handoff/DEPLOYMENT.md](../../docs/handoff/DEPLOYMENT.md). The most
common silent failures are:

1. Beat is not running, so scheduled posts never leave `scheduled`.
2. Reverse proxy does not overwrite `X-Forwarded-For`, making IP rate limits
   meaningless.
3. Redis alerting is missing; rate limits fail open while Redis is down.

## Non-Negotiable Constraints

1. Default mode is `review_first`: no content goes online before approval.
2. Customer replies never use `full_auto` except exact pre-approved FAQ answers.
3. Production prompts live only in the backend.
4. Platform tokens are encrypted and never returned in API responses.
5. Every query is scoped by `workspace_id`.
6. Publish jobs use idempotency keys to prevent duplicate posts.
7. Outreach/reply copy must be truthful about the business identity.
