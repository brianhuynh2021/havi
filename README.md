# Havi

> Multi-industry AI marketing for small shops and solo operators. Havi sells
> outcomes, not tools.

Havi is an "AI marketing employee" for non-technical users such as spas, F&B
shops, real-estate brokers, engineers, specialists, and small online sellers. The
product is built around one closed-loop workflow:

1. **Capture raw material** in under 30 seconds: quick photos, voice notes, typed
   notes, or future POS/webhook inputs.
2. **AI content engine**: detect the industry, process media context, and use one
   LLM call to generate several channel-specific drafts.
3. **Distribution hub**: publish approved content through official platform APIs
   at suitable local posting times.
4. **Lead and care loop**: draft replies for owner approval, run CRM nudges, and
   answer approved FAQ items only.

Reports should measure business outcomes: price inquiries, visits, returning
customers, and published-post reliability. Vanity metrics such as likes and reach
are secondary.

## Repository Layout

This is the `havi-platform` monorepo. Frontend and backend are separated by
runtime boundary but live in one repository.

| Path | Purpose |
|---|---|
| [`apps/web/`](apps/web/) | Next.js frontend |
| [`apps/backend/`](apps/backend/) | FastAPI API, Celery worker, scheduler, and domain core |
| [`prototypes/`](prototypes/) | High-fidelity `.dc.html` design prototypes plus `support.js` |
| [`docs/`](docs/) | Handoff, product, and architecture documentation |

## Local Development

Start services in this order: infrastructure, backend, then frontend. You need
Docker, Node 20+, and [`uv`](https://docs.astral.sh/uv/).

### 1. Infrastructure: Postgres, Redis, MinIO

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
- [docs/handoff/HANDOFF.md](docs/handoff/HANDOFF.md) — design-to-build handoff
- [docs/product/ROADMAP.md](docs/product/ROADMAP.md) — product roadmap
- [docs/architecture/SYSTEM_ARCHITECTURE.md](docs/architecture/SYSTEM_ARCHITECTURE.md)
  — architecture and process boundaries
- [docs/architecture/TECHNICAL_SPEC.md](docs/architecture/TECHNICAL_SPEC.md) —
  technical specification
- [docs/architecture/REPOSITORY_STRATEGY.md](docs/architecture/REPOSITORY_STRATEGY.md)
  — repository strategy

## Prototypes

The `.dc.html` files are high-fidelity design references. They are not production
code to copy.

| File | Screen |
|---|---|
| `Havi - MVP App.dc.html` | Main product app |
| `Havi - Onboarding.dc.html` | Three-step onboarding |
| `Havi - Dang Nhap.dc.html` | Login, signup, OTP, password reset |
| `Havi - Landing Page.dc.html` | Public landing page |
| `Havi - AI Marketing.dc.html` | Pitch/demo flow |
| `Havi - Kien Truc He Thong.dc.html` | Architecture reference |

## Tech Stack

- **Frontend:** Next.js 16, App Router, TypeScript
- **Backend:** FastAPI, Celery worker/beat, PostgreSQL, Redis
- **Contract:** OpenAPI generated from the backend and consumed by the frontend

## License

[MIT](LICENSE) © 2026 Huynh Nguyen
