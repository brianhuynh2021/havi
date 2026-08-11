# Havi — Configuration and Deployment

> Operational documentation: what must run, which variables matter, and which
> failures are silent.
>
> This file records details that are not obvious from code. The complete
> environment variable list lives in `apps/backend/.env.example`; local setup is
> in `README.md`.

## 1. Local-Only Modes

The following variables make Havi simulate work instead of doing real external
work. Validators reject these modes when `HAVI_ENV != local`, so they cannot be
left on silently in staging or production.

| Variable | Default | When true / value | Failure mode |
|---|---|---|---|
| `HAVI_USE_MOCK_LLM` | `true` | Drafts are canned mock output; no model call | Users may publish mock copy while thinking AI wrote it |
| `HAVI_USE_FAKE_PUBLISHER` | `true` | No post is sent to Facebook | Everything looks published in Havi while the real Page is empty |
| `HAVI_DISABLE_RATE_LIMIT` | `false` | No rate limits apply | Brute force and runaway scripts are not throttled |
| `HAVI_EMAIL_PROVIDER=debug` | `debug` | Password reset returns `debug_code`; no real email | Staging/production users never receive reset codes |

The first two defaults are intentionally `true` for local development. If someone
copies `.env.example` directly to staging, the backend should fail fast instead
of running fake behavior.

After deploy, check startup logs. Any staging log that says publishing is fake or
LLM is mock is a deployment error.

For staging/production password reset, configure SMTP:

```bash
HAVI_EMAIL_PROVIDER=smtp
HAVI_EMAIL_FROM=no-reply@your-domain.com
HAVI_SMTP_HOST=smtp.your-domain.com
HAVI_SMTP_PORT=465
HAVI_SMTP_USERNAME=...
HAVI_SMTP_PASSWORD=...
HAVI_SMTP_USE_TLS=true
```

In staging/production, `/auth/password-reset/request` must never return
`debug_code`.

## 2. Facebook Setup

Facebook setup is the slowest first-deploy step because different missing fields
fail in different ways. Configure these in order.

### 2.1. App Domains

In App settings -> Basic, enter only the domain name. Do not include protocol or
path:

```text
your-domain.com
```

- Missing domain: Facebook fails before the permission screen loads.
- Facebook blocks App Domains until Privacy Policy URL is set. Configure the
  privacy URL first, then add App Domains.
- App Domains cannot be changed through Graph API; use the dashboard.

### 2.2. Valid OAuth Redirect URIs

In Facebook Login -> Settings, enter the full URL. It must match
`HAVI_FACEBOOK_REDIRECT_URI` exactly:

```text
https://api.your-domain.com/connections/facebook/callback
```

- This is not the same field as App Domains.
- The "Redirect URI to check" input is only a validation helper; it does not save
  anything.
- Meta now enforces HTTPS. `http://localhost` is not a valid redirect URI for
  this flow. For local OAuth testing, use a tunnel:

```bash
brew install cloudflared
cloudflared tunnel --url http://localhost:8000
```

The `trycloudflare.com` URL changes on each tunnel run, so update
`HAVI_FACEBOOK_REDIRECT_URI`, App Domains, and Valid OAuth Redirect URIs together.

### 2.3. Use Cases and Permissions

Under Use cases -> Manage everything on your Page, the following permissions must
be "Ready for testing":

| Permission | Purpose |
|---|---|
| `pages_show_list` | Read Pages the user manages |
| `pages_read_engagement` | Read Page metadata and retrieve Page tokens |
| `pages_manage_posts` | Publish posts |

If these permissions are not enabled here, they cannot be selected in the
Configuration step.

### 2.4. Facebook Login for Business Configuration

New apps often use Facebook Login for Business. In that mode, permissions live in
a Configuration and the OAuth URL sends `config_id`, not `scope`. Sending `scope`
can show a permission screen and fail later with `Invalid Scopes`.

Create a Configuration with:

- Login variation: General
- Access token: User access token
- Permissions: exactly `pages_show_list`, `pages_read_engagement`,
  `pages_manage_posts`
- Do not add `business_management` or `pages_manage_engagement`

Copy the Configuration ID to `HAVI_FACEBOOK_CONFIG_ID`.

If the app uses classic Facebook Login, leave `HAVI_FACEBOOK_CONFIG_ID` empty.

### 2.5. Development Mode Access

Before App Review, only app roles can use the app in Development mode. Add closed
beta users manually as Administrator, Developer, or Tester.

App Review and Business Verification are required before public signup, but they
do not block a small closed beta where each tester is added manually.

## 3. Token Quota and Rate Limits

### Quota Is Measured in Tokens

Plan limits are defined in `domain/policies/quota.py`:

| Plan | Monthly limit | Rough estimate |
|---|---:|---|
| `trial` | 100,000 tokens | ~25 posts |
| `tiem_nho` | 500,000 tokens | ~125 posts |
| `toan_dien` | 2,000,000 tokens | ~500 posts |

Havi tracks tokens instead of money because providers and pricing change. Token
usage in `event_log` is the durable source of truth; price conversion belongs in
pricing/billing logic.

Quota resets on the calendar-month boundary in Vietnam time. Exceeding quota
returns `429` with `Retry-After` and real usage numbers.

These limits must be recalibrated after pilot usage.

### Internal Operations UI

The internal route `/noi-bo/van-hanh` debugs the active workspace during pilot.
It calls `/analytics/operations` and shows only aggregate metrics: event/error
rate, latency, token totals, provider breakdown, publish success, and dead-letter
rate.

Do not use this page as a customer dashboard. It is internal debug tooling and
does not display request bodies, token secrets, raw provider errors, post
content, or PII. Use Dashboard/Reports for customer-facing views.

### Rate Limits Need Redis and Fail Open

Rate limits are defined in `domain/policies/rate_limits.py`. Auth is IP-based;
upload/content generation are workspace-based.

Two staging requirements:

1. Redis failures fail open. This avoids turning a Redis issue into a full
   outage, but means traffic is unthrottled while Redis is down. Alerting on
   Redis failure is mandatory.
2. Run behind a controlled reverse proxy. IP rate limiting reads
   `X-Forwarded-For`; that header is only trustworthy if your proxy overwrites
   it.

## 4. Required Processes

All four processes are required. Missing processes can look like partial product
bugs rather than deployment failures.

| Process | Command | If missing |
|---|---|---|
| API | `uvicorn api.main:app --host 0.0.0.0 --port 8000` | Nothing works |
| Celery worker | `celery -A worker.celery_app:celery_app worker -l info` | Content jobs stay queued; approved posts never publish |
| Celery beat | `celery -A scheduler.beat:celery_app beat -l info` | Scheduled posts stay scheduled with no visible error |
| Web | `next start` | Users cannot access the app |

Worker and beat need the `queue` extra:

```bash
uv sync --extra queue
```

Some beat schedules are still placeholders for later product areas. Known
`NotImplementedError` traces for unfinished refresh/CRM/engagement jobs are not
regressions unless the roadmap says those areas are complete.

## 5. Staging Deployment Runbook

This is the minimum runbook for a staging deploy. Production should use the same
order with stronger access control, monitored backups, and an explicit approver.

### 5.1. Pre-Deploy Checks

Run from a clean working tree or a tagged build artifact:

```bash
npm run lint:web
npm run test:web
npm run build:web
cd apps/backend && uv run ruff check . && uv run pytest
cd apps/backend && uv run alembic check
```

Confirm environment guardrails before starting processes:

```bash
test "$HAVI_ENV" = "staging" -o "$HAVI_ENV" = "production"
test "$HAVI_USE_MOCK_LLM" = "false"
test "$HAVI_USE_FAKE_PUBLISHER" = "false"
test "$HAVI_DISABLE_RATE_LIMIT" = "false"
test "$HAVI_EMAIL_PROVIDER" != "debug"
test -n "$HAVI_TOKEN_ENCRYPTION_KEY"
```

For a closed Facebook beta, confirm every tester is added to the Facebook app
roles before asking them to connect a Page.

### 5.2. Deploy Order

Use this order to avoid workers running code against an old schema:

1. Put worker and beat in drain/paused mode if the platform supports it.
2. Create a pre-deploy Postgres backup.
3. Deploy and run database migrations.
4. Deploy API.
5. Deploy worker.
6. Deploy beat.
7. Deploy web.
8. Run smoke checks.

If the platform cannot pause workers, scale worker and beat to zero before
running migrations, then scale them back up after API deploy.

### 5.3. Required Process Checks

All four processes must be alive after deploy:

```bash
# API
curl -fsS https://api.example.com/health

# Web
curl -fsS https://app.example.com/

# Worker and beat
# Use your platform process list/log command. Required evidence:
# - one worker process is running
# - one beat process is running
# - worker logs show it received registered tasks
# - beat logs show scheduled task emission
```

Functional smoke test:

1. Sign in with an internal test account.
2. Create one content job.
3. Confirm drafts are created.
4. Approve one Facebook draft for a near-future time.
5. Confirm beat dispatches a publish job.
6. Confirm worker publishes or records a clear fake-mode-blocked/config error.
7. Open `/noi-bo/van-hanh` and confirm event/publish metrics changed.

For staging with real Facebook Development mode, use a draft/test Page.

### 5.4. Migration Forward and Rollback Strategy

Forward migration:

```bash
cd apps/backend
uv run alembic upgrade head
uv run alembic check
```

Rollback rule:

- Prefer forward fixes for application bugs.
- Use Alembic downgrade only for a migration that has just been deployed, has not
  been used by new code for long, and is known to be reversible.
- Never downgrade after destructive migrations unless a restore rehearsal proves
  the path.
- Do not edit production data by hand as a rollback.

Before any risky migration, record:

```bash
cd apps/backend
uv run alembic current
uv run alembic history --verbose -n 5
```

If rollback is chosen:

```bash
cd apps/backend
uv run alembic downgrade -1
uv run alembic current
```

Then redeploy the previous API/worker/beat/web version that matches the schema.

### 5.5. Incident Checklist

For every staging incident, capture:

- time detected
- affected workspace/user
- request id or job id
- current deploy version/commit
- process affected: web, API, worker, beat, Postgres, Redis, object storage,
  Facebook, LLM provider, email
- whether fake/mock guardrails are involved
- whether data restore is needed
- owner for follow-up

Fast triage commands:

```bash
curl -fsS https://api.example.com/health
curl -fsS https://app.example.com/
cd apps/backend && uv run alembic current
```

Use `/analytics/events` and `/noi-bo/van-hanh` for workspace-scoped job/debug
evidence. Do not paste raw tokens, request bodies, or customer content into
incident notes.

## 6. Migrations

Run migrations before starting a new API version:

```bash
uv run alembic upgrade head
uv run alembic check
```

Run `alembic check` after migrations to confirm models and migration state still
match.

## 7. Backup and Restore Rehearsal

Backups are not proven until restore has been rehearsed. Run this once before
founder beta and after any infrastructure migration.

### 7.1. Postgres Backup

Local rehearsal with Docker Compose:

```bash
mkdir -p backups
docker compose exec -T postgres pg_dump -U havi -d havi \
  --format=custom --no-owner --no-acl > backups/havi-$(date +%Y%m%d-%H%M%S).dump
```

Staging should use the managed database provider's backup/export facility when
available. Keep at least:

- daily backups for 7 days
- one weekly backup for 4 weeks during beta
- a pre-deploy backup before every migration

### 7.2. Postgres Restore Rehearsal

Restore only into a throwaway database or local rehearsal stack:

```bash
docker compose exec -T postgres createdb -U havi havi_restore
docker compose exec -T postgres pg_restore -U havi -d havi_restore \
  --clean --if-exists --no-owner --no-acl < backups/<backup-file>.dump
docker compose exec -T postgres psql -U havi -d havi_restore \
  -c "select count(*) from workspaces;"
```

Validation checklist:

- restore command completes without errors
- core tables are queryable
- `alembic_version` matches expected deploy version
- a test API instance can point to the restored database and pass `/health`
- one internal login/workspace read works against restored data

Clean up the rehearsal database:

```bash
docker compose exec -T postgres dropdb -U havi havi_restore
```

### 7.3. Object Storage Backup

For local MinIO, mirror the media bucket:

```bash
mkdir -p backups/minio-havi-media
docker run --rm --network havi_default -v "$PWD/backups:/backup" minio/mc:latest \
  sh -c "mc alias set local http://minio:9000 minioadmin minioadmin && \
         mc mirror --overwrite local/havi-media /backup/minio-havi-media"
```

For staging/production object storage, prefer bucket versioning or provider
backup/replication. If provider backup is unavailable, schedule a regular bucket
mirror to a separate bucket/account.

Metadata and blobs must be restored together:

- Postgres `media_assets` rows point to object URLs/keys.
- Restoring the database without matching object data leaves broken media.
- Restoring object data without matching database rows leaves orphaned blobs.

### 7.4. Object Storage Restore Rehearsal

Rehearse by copying a small sample prefix into a throwaway bucket:

```bash
docker run --rm --network havi_default -v "$PWD/backups:/backup" minio/mc:latest \
  sh -c "mc alias set local http://minio:9000 minioadmin minioadmin && \
         mc mb --ignore-existing local/havi-media-restore-test && \
         mc mirror --overwrite /backup/minio-havi-media local/havi-media-restore-test && \
         mc ls local/havi-media-restore-test && \
         mc rb --force local/havi-media-restore-test"
```

Validation checklist:

- sample media objects exist in restored bucket
- public/media URL policy matches the original bucket policy
- a browser can load a restored object URL
- restored database rows reference available object keys

## 8. Secrets

| Secret | Rotation impact |
|---|---|
| `HAVI_JWT_SECRET` | Existing sessions are invalidated |
| `HAVI_TOKEN_ENCRYPTION_KEY` | Stored platform tokens become unreadable; users must reconnect channels |
| LLM API keys | Can rotate without data impact |
| Facebook client secret | Can rotate; issued Page tokens continue until expiry |

`HAVI_TOKEN_ENCRYPTION_KEY` is currently a single key without versioning. Do not
rotate it casually; add a migration plan first.

## 9. Pre-Beta Checklist

Do not invite customer beta users while any critical item remains unchecked:

- [ ] `HAVI_ENV=staging|production`
- [ ] `alembic upgrade head` complete and `alembic check` clean
- [ ] API, worker, beat, and web processes are all running
- [ ] Beat verified by approving a post and seeing it publish
- [ ] Facebook App Domains, Redirect URI, permissions, and Configuration ID set
- [ ] Reverse proxy overwrites `X-Forwarded-For`
- [ ] Real email provider configured for password reset
- [ ] Redis failure alerting configured
- [ ] Automated backup exists and restore has been rehearsed for Postgres and
      object storage
- [ ] Tenant isolation tests pass in CI
- [ ] A real post has been published to a draft/test Page
