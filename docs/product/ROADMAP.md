# Havi Product Roadmap

> Documentation language: English. Product UI/customer-facing copy remains
> Vietnamese because the target users are Vietnamese small-business owners.

## 1. Product Thesis

Havi is an AI marketing employee for small shops and solo operators. The product
is not a generic content tool; it is a closed-loop marketing workflow:

1. capture raw material quickly
2. generate multiple channel-specific drafts
3. require owner approval by default
4. publish through official platform APIs
5. track business outcomes and operational reliability

Primary user outcomes:

- create usable marketing posts without marketing expertise
- publish consistently without learning platform tooling
- avoid accidental/deceptive automation
- understand whether marketing work produces inquiries, visits, or return visits

Non-goals for MVP:

- scraping or unofficial platform automation
- automatic customer replies without approval
- vanity-metric dashboards that imply more certainty than the data supports
- broad multi-channel public launch before safe publishing and operations are
  proven

## 2. Product Principles

1. **Approval first:** no content goes online until the owner approves it, except
   exact pre-approved FAQ responses.
2. **Official APIs only:** platform integration must use supported APIs.
3. **One job, multiple drafts:** content generation should create several
   channel-specific drafts from one raw-input job.
4. **Backend owns safety:** approval state, idempotency, tenant isolation, quota,
   and token encryption are backend responsibilities.
5. **Measure real outcomes:** reports prioritize published posts, inquiries,
   visits, returning customers, and operational health.
6. **Local fake modes only:** mock LLM and fake publisher are for local/test
   development and are blocked in staging/production.
7. **No PII/secrets in observability UI:** operations tooling shows aggregate
   metrics, not raw request bodies or tokens.

## 3. Current Architecture Status

Implemented:

- Monorepo with `apps/web` and `apps/backend`
- Next.js frontend with App Router and feature folders
- FastAPI API, Celery worker, Celery Beat scheduler
- PostgreSQL models and Alembic migrations
- Redis-backed queue/rate-limit infrastructure
- S3-compatible media upload tickets
- Email/password auth, password reset contract, refresh sessions
- Workspace and member model
- Brand profile and banned-claims policy
- Content jobs, content items, versions, approval, calendar, rescheduling
- Content Engine with provider router and fake provider tests
- Quota policy based on monthly token usage
- Platform connection storage with encrypted tokens
- Facebook OAuth/publisher adapter and fake publisher
- Publish scheduler, retry, dead-letter handling, idempotency, and event logging
- Dashboard summary, reports, event log query, and operations metrics
- Frontend dashboard, content creation, calendar, failed publish panel, settings,
  reports, activity feed, internal operations UI
- Local E2E smoke test for signup -> draft -> approve -> fake publish -> report

Still pending:

- Engagement snapshots if Facebook permissions allow
- Unified inbox and lead/CRM workflows
- Customer-facing next actions for all reconnect/quota/failure cases
- Data deletion, account deletion, and consent records
- Founder dogfooding plan and beta readiness process

## 4. Completed Milestones

### Week 1-2: Foundations

- Repository strategy and architecture documentation
- Backend domain boundaries and migration setup
- Auth/workspace/brand-profile persistence
- Frontend app shell, auth screens, landing page, onboarding, and core UI
  primitives
- OpenAPI client generation

### Week 3-4: Auth, Workspace, Media

- Email/password signup and login
- Password reset via email code
- Refresh-token rotation
- Workspace creation/activation
- Brand profile creation/update
- Media upload ticket and object-storage metadata flow
- Test coverage for auth, workspace, brand profile, media, route guards, and API
  client behavior

### Week 5-6: Content Engine and Approval

- Content job API and worker-side content engine
- Mock/fake LLM provider for deterministic local/test flows
- Multi-provider router for Gemini/Anthropic/OpenAI
- Structured output validation and banned-claims validation
- Content item state machine
- Draft editing and version history
- Approve/reject/reschedule flows
- Audit events for approval-sensitive actions
- Calendar view grouped by Vietnam time
- Calendar rescheduling UI sends offset-aware ISO datetimes and handles 409
  conflicts

### Week 7: Facebook Connection and Publishing

- Facebook OAuth flow and token encryption
- Facebook publisher adapter through official Graph API endpoints
- Fake publisher for local/test
- Publish job repository with unique idempotency key
- Scheduler dispatches due approved posts
- Worker claims jobs with row locks and bounded retry
- Dead-letter handling and manual retry API
- Failed-posts frontend panel with retry/reconnect guidance
- Publish event logging for success and failure

### Week 8: Real Dashboard and Observability

- `/analytics/dashboard` summary from real workspace data
- `/analytics/summary`, `/analytics/timeseries`, and `/analytics/attribution`
  from published content
- `/analytics/events` query over workspace-scoped `event_log`
- `/analytics/operations` aggregate operations metrics
- Frontend Dashboard and Reports no longer render fake business metrics
- Dashboard activity feed reads real event/audit rows and maps them to
  user-facing copy without leaking raw summaries or errors
- Internal route `/noi-bo/van-hanh` shows aggregate operations metrics for pilot
  debugging
- Local E2E core-flow smoke test via `npm run e2e`

### Week 9: Staging Readiness

- Staging deployment runbook with pre-deploy checks, fake-mode guardrails,
  deploy order, required process checks, smoke test, migration forward/rollback
  rules, incident checklist, and backup/restore rehearsal steps
- Postgres backup and restore rehearsal commands for local/staging practice
- Object-storage backup and restore rehearsal guidance for local MinIO and
  provider-backed staging
- Security review checklist for founder beta with auth/session, token
  encryption, tenant isolation, upload validation, logging/redaction, fake-mode,
  dependency, deployment-secret, deletion, and consent gates
- Visual regression and accessibility baseline for major web routes across
  desktop and mobile viewports

## 5. Current Definition of Done

Every completed feature should satisfy:

- tenant isolation is enforced and tested where data crosses workspace boundary
- user-facing copy remains Vietnamese in the app
- internal docs and engineering notes are English
- no platform token, OTP, password, API key, or raw request body is exposed in UI
  or logs
- backend state machine owns approval/publishing rules
- idempotency exists for external side effects
- loading, empty, error, and retry states exist for user-facing flows
- verification commands are recorded in this roadmap or related docs

## 6. Verification Commands

Common web verification:

```bash
npm run lint:web
npm run test:web
npm run build:web
npm run test:visual
```

Common backend verification:

```bash
npm run infra:up
npm run migrate
cd apps/backend && uv run ruff check . && uv run pytest
```

Focused checks added during recent roadmap work:

```bash
npm run test:web -- --run src/features/calendar/calendar-screen.test.tsx
npm run test:web -- --run src/features/dashboard/dashboard-screen.test.tsx
npm run test:web -- --run src/features/operations/operations-screen.test.tsx
cd apps/backend && uv run pytest tests/test_analytics_flow.py
npm run e2e
cd apps/backend && uv run ruff check tests/test_e2e_core_flow.py
```

## 7. Current Priority Queue

All Founder Beta milestones (Gates A through E) are 100% completed, tested, and verified.
Queue for External Beta Phase:
1. Setup dependency vulnerability scanning audit (`npm audit` & `uv pip audit`).
2. Add HTTP-only cookie option for refresh tokens to supplement local storage.
3. Prepare marketing landing page assets for external pilot cohort onboarding.

## 8. Upcoming Work

### Completed: Founder Dogfooding Plan

Status: completed in `docs/operations/DOGFOODING_PLAN.md`.

Acceptance criteria:

- [x] 7-day internal beta checklist (Day 1 through Day 7 action guide)
- [x] daily tasks and operational telemetry log template
- [x] P0/P1 bug triage SLAs and response times defined
- [x] immediate stop rules (kill switches) defined for system failures or credential leaks
- [x] criteria for inviting external beta cohort defined

### Completed: Data Deletion, Account Deletion, and Consent Records

Status: completed in `docs/security/DATA_RETENTION_AND_CONSENT.md`.

Acceptance criteria:

- [x] user/account deletion behavior defined & implemented via `DELETE /auth/me`
- [x] workspace deletion behavior defined & implemented via `DELETE /workspaces/{id}`
- [x] retained audit/event data defined with rationale & anonymization
- [x] platform token deletion and reconnect behavior defined
- [x] consent records for automation (`publish_mode`) and platform OAuth connections defined & recorded
- [x] covered by backend integration test suite (`tests/test_deletion_and_consent.py`) and frontend UI in Settings

### Completed: Staging Runbook and Backup/Restore Rehearsal

Why: founder beta must not start until deployment, data recovery, and rollback
steps are concrete.

Implemented in `docs/handoff/DEPLOYMENT.md`:

- runbook lists the four required processes: web, API, worker, beat
- startup flags and local-only fake modes are checked
- migration forward/rollback process is documented
- Postgres backup and restore rehearsal steps are documented
- object-storage backup/restore approach is documented
- incident response owners and commands are listed

Verification:

```bash
npm run migrate
cd apps/backend && uv run alembic check
```

### P0: Security Review Checklist

Status: completed for founder beta in `docs/security/SECURITY_REVIEW.md`.

Acceptance criteria:

- [x] auth/session/token handling reviewed
- [x] platform token encryption reviewed
- [x] tenant isolation reviewed
- [x] upload validation reviewed
- [x] logs/events checked for secrets and PII
- [x] local-only flags verified as blocked outside local
- [x] dependency and deployment secret handling reviewed

Open follow-ups before external beta:

- data deletion and consent policy remains P1
- dependency vulnerability scanning should be added
- refresh-token storage should move from `localStorage` to HTTP-only cookies

### P1: Visual Regression and Accessibility Baseline

Status: completed in `docs/testing/VISUAL_ACCESSIBILITY.md`.

Acceptance criteria:

- [x] baseline screenshots for major app routes
- [x] smoke accessibility checks for nav/forms/buttons/states
- [x] mobile and desktop viewport checks
- [x] documented command for local/CI execution

## 9. Metrics That Matter

Product metrics:

- time from signup to first draft
- time from first draft to first approved post
- approved drafts per workspace
- published posts per workspace
- publish failures by kind
- reconnect rate
- owner edits per draft
- support time per workspace

Operational metrics:

- event count
- error count/rate
- avg/p95 job latency
- token totals
- provider breakdown
- publish success/dead-letter rate
- quota near/exceeded events

Business metrics:

- cost per content job
- cost per approved draft
- cost per published post
- founder support time
- conversion from trial to paid plan

## 10. Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Facebook App Review takes longer than expected | Blocks public publishing rollout | Closed beta can use Development mode with manually added testers |
| Fake publisher or mock LLM reaches staging | Users see false success | Backend validators block fake modes outside local |
| Beat is not running | Scheduled posts never publish | Deployment checklist and runbook must verify beat |
| Redis outage disables rate limits | Abuse can pass unthrottled | Redis failure alerting required because limiter fails open |
| Tenant isolation bug | Cross-customer data leak | Workspace-scoped queries and tests |
| Duplicate publish | Same post published twice | Publish idempotency key, unique constraint, and row locks |
| Raw provider errors leak to UI | Secrets/PII exposure | User-facing copy maps errors to safe categories |
| Token cost grows silently | Margin loss | Token quota, event log usage, operations UI |
| Backup restore rehearsal grows stale | Data recovery becomes unproven again | Rehearse after infrastructure changes and before customer beta |

## 11. Decisions to Revisit

| Decision | Current choice | Revisit trigger |
|---|---|---|
| Primary auth | Email/password | Add OTP/Zalo login only when business need is clear |
| First publishing channel | Facebook Page | Add Google/Zalo/TikTok based on beta demand and API access |
| Quota unit | Tokens | Add money conversion after pricing model stabilizes |
| Repository model | Monorepo | Split only when ownership/security/deployment cadence requires it |
| Video pipeline | Not P0 | Revisit after text/image publishing loop is stable |
| Full-auto publishing | Opt-in only | Unlock only after trust/edit-rate evidence exists |

## 12. Agent Loop Notes

`agent-loop/roadmap.example.json` is the machine-readable execution roadmap
derived from this product roadmap. `agent-loop/roadmap.json` is local runtime
state and should not be treated as the source of truth.

Workflow:

1. Update this roadmap when a task is genuinely completed and verified.
2. Keep `agent-loop/roadmap.example.json` aligned with the next executable tasks.
3. Run small batches; do not let the loop edit indefinitely.
4. Commit/push remains manual.

Recommended JSON checks:

```bash
python3 -m json.tool agent-loop/roadmap.example.json
test ! -f agent-loop/roadmap.json || python3 -m json.tool agent-loop/roadmap.json
```
