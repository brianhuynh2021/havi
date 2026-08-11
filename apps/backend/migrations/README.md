# Migrations

Alembic uses the async template and the local stack from the root
`docker-compose.yml`.

## Start the Local Stack

From the repository root:

```bash
docker compose up -d
```

This starts Postgres, Redis, and MinIO.

## Create and Run Migrations

```bash
cd apps/backend
uv sync --extra db
uv run alembic revision --autogenerate -m "short description"
uv run alembic upgrade head
```

`migrations/env.py` reads the connection string from `core.config.Settings`
(`HAVI_DATABASE_URL`). Do not maintain a second source of truth in
`alembic.ini`.

`target_metadata` points to `domain.models.Base.metadata`. When adding a new
model, import it in `domain/models/__init__.py` so autogenerate can see it.

Before committing a schema change, run:

```bash
uv run alembic check
```

It must report `No new upgrade operations detected.` before model and migration
state are considered aligned.

## Rules

- The backend is the only database owner.
- The frontend must never connect to the database directly.
- Business tables should be workspace-scoped where applicable.
- Queries must enforce workspace scope to prevent cross-tenant leaks.
- Migrations deploy separately from API, worker, and scheduler processes.
- Every schema change goes through Alembic; do not edit production databases by
  hand.
