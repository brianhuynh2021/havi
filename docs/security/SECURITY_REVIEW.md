# Security Review Checklist

> Documentation language: English. Product UI/customer-facing copy remains
> Vietnamese because the target users are Vietnamese small-business owners.

Review date: 2026-08-11
Last checked against `dev`: 2026-08-28

> **This review is out of date and does not gate external beta on its own.**
> The findings below were made against the 2026-08-11 tree. Since then `dev` has
> taken 86 backend commits, and four request surfaces reached the API *after*
> the review closed. They have tests, but no security pass:
>
> | Surface | Added | Why it needs its own pass |
> |---|---|---|
> | `POST /webhooks/payos`, `POST /webhooks/vietqr` | 2026-08-17 | Unauthenticated money-moving endpoints; signature verification and replay handling are the whole control. |
> | `/voice` | 2026-08-17 | New upload path with a different content type from the reviewed media flow. |
> | `/workspaces/{id}/video/posts` | 2026-08-25 | Publishes externally; needs the same idempotency and approval checks as content publishing. |
> | `/organizations`, `/queue` | 2026-08-26 | Cross-workspace reads above the workspace scope the review verified, and they query repositories directly instead of going through a service. |
>
> Re-run the checklist over those five routers before inviting external users.
> Everything below still describes the controls it names, but "Pass" means
> passed on 2026-08-11.

Scope: founder beta readiness for the `dev` branch as of 2026-08-11.

## 1. Review Summary

Status: conditionally ready for founder beta, on the 2026-08-11 tree.

The core safety controls for auth, tenant isolation, platform token encryption,
upload validation, fake-mode guardrails, and operations UI redaction are present
and covered by tests. The remaining gaps are product/data-governance decisions
that should be completed before inviting external beta users, plus the
unreviewed surfaces listed above.

## 2. Checklist

| Area | Status | Evidence | Follow-up |
|---|---|---|---|
| Auth and sessions | Pass | Email/password auth, refresh-session rotation, logout revoke, invalid-token handling, and route guards are covered by backend and frontend tests. | Move refresh tokens from `localStorage` to an HTTP-only cookie before broad launch. |
| Password reset | Pass for founder beta | Local debug reset codes are allowed only in `HAVI_ENV=local`; staging/production require a real email provider. | Verify SMTP/provider secrets in staging before external users. |
| Tenant isolation | Pass | Backend dependencies scope authenticated routes by `active_workspace_id`; workspace, brand profile, content, media, publish, quota, and analytics tests cover cross-workspace behavior. | Add deletion/retention tests after the deletion policy is implemented. |
| Platform token encryption | Pass | Platform tokens are encrypted with `HAVI_TOKEN_ENCRYPTION_KEY`; missing or invalid keys fail closed; response schemas omit plaintext tokens. | Define a key-rotation runbook and reconnect messaging for rotated keys. |
| OAuth callback safety | Pass | Signed OAuth state binds workspace, user, platform, and return target; callback rechecks membership before storing tokens. | Recheck Facebook App settings on every staging/prod environment. |
| Publishing safety | Pass | Publish jobs use idempotency keys, row locks, bounded retries, failure categories, and dead-letter handling. | Keep one manual real-Page smoke test before each beta wave. |
| Upload validation | Pass | API signs upload tickets, storage enforces size limits, completion verifies object existence and file signatures, invalid content is deleted. | Add malware scanning only if beta users upload non-image assets or higher-risk formats. |
| Rate limiting | Pass with operational caveat | Redis-backed limits cover auth and workspace actions; local-only disable flag is blocked outside local. | Redis failure is fail-open by design, so alerting must stay enabled. |
| Fake modes | Pass | Mock LLM, fake publisher, disabled rate limit, and debug email are blocked outside local by settings validators. | Keep CI and staging deploy checks aligned with these flags. |
| Logs and event data | Pass for founder beta | Operations screens show aggregate metrics only; dashboard/activity copy maps raw errors into safe categories; docs forbid raw tokens, request bodies, and customer content in incident notes. | Add automated log-redaction tests if structured logging expands. |
| Frontend token handling | Accepted risk | Token access is centralized in `apps/web/src/lib/auth/token-store.ts`; tests cover corrupted storage and refresh failure. | HTTP-only cookies are recommended before public launch because XSS can read `localStorage`. |
| Dependency handling | Partial | CI runs lint, tests, build, Alembic upgrade, and full backend pytest. | Add dependency audit or lockfile vulnerability scanning before external beta. |
| Deployment secret handling | Partial | Deployment docs list required secrets and fake-mode blockers; CI uses non-production test values. | Confirm staging secrets are stored in the hosting provider secret manager, not `.env` committed files. |
| Data deletion and consent | Pass | Defined retention rules in DATA_RETENTION_AND_CONSENT.md, implemented DELETE /workspaces/{id} and DELETE /auth/me APIs, anonymized event logs, and added test suite. | Recheck backup retention cycles prior to broad public launch. |

## 3. Verified Controls

### Auth and Session Handling

- Access tokens are attached only by the API client wrapper.
- Refresh requests retry only once after a 401 and deduplicate simultaneous
  refreshes.
- Logout revokes the refresh session server-side.
- Corrupted or incomplete browser token storage is treated as signed out.
- Unauthenticated business endpoints return 401.

Primary evidence:

- `apps/backend/tests/test_auth_flow.py`
- `apps/web/src/lib/api-client/client.test.ts`
- `apps/web/src/lib/auth/token-store.test.ts`
- `apps/web/src/lib/auth/route-guard.test.tsx`

### Tenant Isolation

- `api/deps.py` derives the active workspace from the JWT.
- Tenant-owned repository methods require `workspace_id` filters.
- Cross-tenant reads and writes are tested for workspace, brand profile, media,
  content, publish jobs, quota, and analytics flows.
- Publish-job routes return 404 for another workspace's job to avoid confirming
  resource existence.

Primary evidence:

- `apps/backend/api/deps.py`
- `apps/backend/tests/test_workspace_flow.py`
- `apps/backend/tests/test_brand_profile_flow.py`
- `apps/backend/tests/test_content_flow.py`
- `apps/backend/tests/test_publish_router.py`
- `apps/backend/tests/test_quota_flow.py`
- `apps/backend/tests/test_analytics_flow.py`

### Platform Token Storage

- Tokens are encrypted before persistence.
- Missing encryption configuration fails closed instead of storing plaintext.
- Decryption failure marks the connection unusable and asks the owner to
  reconnect.
- Connection response schemas omit token fields.
- Manual disconnect deletes the connection row and encrypted token material.

Primary evidence:

- `apps/backend/core/token_crypto.py`
- `apps/backend/adapters/persistence/connection_repository.py`
- `apps/backend/application/services/connection_service.py`
- `apps/backend/application/services/publish_service.py`
- `apps/backend/tests/test_token_crypto.py`
- `apps/backend/tests/test_connection_flow.py`
- `apps/backend/tests/test_connection_router.py`

### Upload Safety

- Upload ticket creation rejects unsupported content types and mismatched asset
  kinds.
- Object storage receives size constraints in the presigned POST.
- Completion verifies the object exists and validates file signatures.
- Invalid uploaded objects are deleted and rejected.

Primary evidence:

- `apps/backend/application/services/media_service.py`
- `apps/backend/core/file_signatures.py`
- `apps/backend/tests/test_media_flow.py`

### Publishing Safety

- Publish idempotency keys include content item, channel, and scheduled time.
- Database unique constraints block duplicate publish jobs.
- Workers claim jobs with `FOR UPDATE SKIP LOCKED`.
- Temporary failures retry with bounded backoff.
- Auth and validation failures go straight to dead-letter.
- Manual retry is scoped by workspace and only works for dead-letter jobs.

Primary evidence:

- `apps/backend/adapters/persistence/publish_repository.py`
- `apps/backend/application/services/publish_service.py`
- `apps/backend/tests/test_publish_flow.py`
- `apps/backend/tests/test_publish_router.py`
- `apps/backend/tests/test_scheduler_wiring.py`

### Observability Redaction

- Customer-facing dashboard copy does not expose raw provider errors.
- Internal operations UI shows aggregate metrics only.
- Deployment docs instruct incident responders not to paste raw tokens, request
  bodies, or customer content into support notes.

Primary evidence:

- `apps/web/src/features/dashboard/dashboard-screen.test.tsx`
- `apps/web/src/features/operations/operations-screen.test.tsx`
- `docs/handoff/DEPLOYMENT.md`

## 4. Open Risks

### Browser Token Storage

Risk: refresh tokens are stored in `localStorage`, so a successful XSS can read
them.

Current position: accepted for founder beta because the app is private, token
access is centralized, and the frontend has no platform tokens or provider
secrets.

Required before public launch:

- migrate refresh tokens to HTTP-only secure cookies
- keep access-token lifetime short
- add CSP and dependency audit checks

### Data Deletion and Consent

Status: Completed.

Implemented controls:

- Retention rules defined in `docs/security/DATA_RETENTION_AND_CONSENT.md`.
- `DELETE /workspaces/{workspace_id}` cascades deletion of brand profiles, content jobs/items, publish jobs, encrypted platform connections, and object storage files (S3/MinIO).
- `DELETE /auth/me` revokes sessions, auto-deletes sole-member workspaces, and removes user profile.
- Event logs for deleted workspaces have `workspace_id` set to NULL and inputs redacted.
- Consent audit logs recorded for publish mode changes, workspace lifecycle, and platform connections.
- Covered by unit and integration tests (`tests/test_deletion_and_consent.py`).

### Secret Rotation

Risk: rotating `HAVI_TOKEN_ENCRYPTION_KEY` makes existing platform tokens
undecryptable.

Current behavior: affected connections fail closed and require reconnect.

Required before external beta:

- document key rotation steps
- document reconnect messaging
- keep backup/restore runbook aligned with secret rotation

## 5. Verification Commands

Run before founder beta:

```bash
npm run lint:web
npm run test:web
npm run build:web
npm run migrate
cd apps/backend && uv run ruff check . && uv run pytest
```

CI on `dev` must show both jobs passing:

- Web Checks
- Backend Checks

## 6. Release Gate

Founder beta may proceed when:

- CI passes on `dev`
- staging uses `HAVI_ENV=staging`
- fake/mock/debug local flags are disabled in staging
- `HAVI_TOKEN_ENCRYPTION_KEY` is configured from a secret manager
- real email provider is configured for password reset
- Redis alerting is configured
- one Facebook test Page publish succeeds
- backup and restore rehearsal has been run after the latest infrastructure
  change

External beta remains blocked until:

- [x] data deletion and consent records are implemented
- [ ] dependency vulnerability scanning is added
- [ ] refresh-token storage is moved out of `localStorage` or the risk is explicitly
  accepted for the beta cohort
