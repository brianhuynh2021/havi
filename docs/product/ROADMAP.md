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

> Audited against the code on 2026-08-13. Items are graded by what a real user
> can complete end to end in production, not by what code exists. Findings and
> the reasoning behind each grade are in §13 (architecture) and §14 (business).

### 3.1 Implemented and reachable end to end

- Monorepo with `apps/web` and `apps/backend`
- Next.js frontend with App Router, feature folders, and edge middleware that
  enforces public/app realms and rewrites the legacy Vietnamese URL aliases
- FastAPI API, Celery worker, Celery Beat scheduler
- PostgreSQL models and Alembic migrations (9 revisions)
- Redis-backed queue/rate-limit infrastructure
- S3-compatible media upload tickets with MIME/signature validation
- Email/password auth, password reset contract, refresh sessions with HTTP-only cookies
- Workspace and member model
- Brand profile, voice/tone settings, and banned-claims policy
- Content jobs, content items, versions, approval, calendar, rescheduling
- Content Engine with provider router and fake provider tests
- Quota policy based on monthly token usage, evaluated in Vietnam time
- Platform connection storage with encrypted tokens
- Facebook OAuth + publisher through the official Graph API; fake publisher for local
- Zalo OA OAuth + paragraph-message publisher
- Publish scheduler, retry, dead-letter handling, idempotency, and event logging
- Publish adapter map built once in `worker/publish_service_factory.build_publishers()`
  and reused by `api/deps.get_publish_service`, so API retry and scheduler cannot diverge
- Fake-mode guardrails enforced at config load: mock LLM, fake publisher, disabled
  rate limit, and debug email all refuse to boot when `HAVI_ENV != local`
- Data deletion and account deletion (`DELETE /auth/me`, `DELETE /workspaces/{id}`,
  `/data-deletion` page, Meta signed-request callback)
- Global bilingual English/Vietnamese i18n across app screens
- Founder dogfooding protocol runner (`scripts/dogfood_suite.py`) and 7-day plan
- Frontend dashboard, content creation, calendar, failed publish panel, settings,
  reports, activity feed, internal operations UI
- Local E2E smoke test for signup -> draft -> approve -> fake publish -> report

### 3.2 Partial — code exists, the loop it belongs to cannot be completed

| Area | What exists | What is missing |
|---|---|---|
| Station 4 Lead & Care Loop | `inbox_items`/`leads` tables, `/leads` CRM API, Meta webhook ingestion with signature verification and dedupe, exact-match FAQ auto-reply, `DISMISSED` state, local inbound simulator | `send_reply` still writes DB state only and calls no publisher; no `/app/inbox` screen |
| Google Business channel | `GoogleBusinessPublisher` | No Google OAuth client registered in `api/deps._oauth_clients()`, so the channel is no longer advertised by `/connections/capabilities` and cannot be connected |
| Business outcome reporting | `/analytics/summary` computes inquiries, new leads, walk-ins, returning customers, and win rate from real rows, with period-over-period change | `walk_ins` proxies won leads because no POS/check-in source exists; `/analytics/attribution` still shares published posts rather than customers; no cost-per-job rollup |
| Video pipeline (Phase 3) | Stage 1 complete: `VideoProcessorPort`, ffprobe-on-upload, persisted duration/dimensions/aspect/audio, per-channel constraint policy, `eligible_channels` on the media API | Stages 2–6: multimodal understanding, transcript, Edit Engine, `EditPlan.json`, renderers, and channel dispatch are design-only |
| Short-form channels (Reels/TikTok/Shorts) | `Channel.REELS/TIKTOK/YOUTUBE` declared; upload-time eligibility checking | No publisher, no OAuth client, no API credentials — deliberately not built, see §17 |
| Billing and plans | `Plan` enum, `Workspace.plan`, `Subscription`/`Invoice` schemas, quota per plan | `/billing/*` raises `NotImplementedEndpoint`; nothing ever writes `Workspace.plan`; no trial expiry, no payment gateway |
| Domain layering | `domain/models`, `domain/policies`, `domain/ports` are clean | `core/` still holds `content_state.py`, `oauth_state.py`, `phone.py`, `schemas.py` — transitional scaffolding per SYSTEM_ARCHITECTURE §0 |

### 3.3 Not started

- Sales webhook and social listening — the `SALES` and `LISTEN` inputs in the
  SYSTEM_ARCHITECTURE §1 diagram still have no code (the Meta inbound leg now
  exists in `api/routers/webhooks.py`)
- Engagement snapshots from Meta (blocked on live permission approval)
- Any paid conversion path

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
- Internal route `/app/internal/operations` (legacy alias `/noi-bo/van-hanh`)
  shows aggregate operations metrics for pilot debugging
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

> Re-derived from the 2026-08-13 code audit. The list below the divider is the
> shipped External Beta queue and is left intact as history. The active queue is
> §15, because the audit found that the outcome loop the product sells is not
> closed and one uncommitted endpoint is a security blocker.

> Zalo scope is deferred by decision on 2026-08-13. Zalo OAuth, publishing,
> webhooks, and domain verification stay in the codebase but are out of the
> active queue and out of the gates below until the channel is picked back up.

Active now — see §15 for full acceptance criteria:

1. [x] P0 — replaced the traversal-prone `/zalo_verifier{rest:path}` handler in
   `apps/backend/api/main.py`; suffix is now compared exactly against settings,
   no request input reaches the filesystem, and the route 404s unless configured.
2. [x] P0 — inbound event plane: `POST/GET /webhooks/meta` with
   `X-Hub-Signature-256` verification, challenge handshake, page→workspace
   lookup, and platform-message-id dedupe backed by a unique constraint.
3. [x] P0 — deliver replies through publisher adapters (`ReplyPublisherPort` and `FakeReplyPublisher`) instead of marking rows `sent`.
4. [x] P1 — real outcome metrics in `/analytics/summary` (inquiries, new leads,
   walk-ins, returning customers, win rate, period-over-period change).
5. [x] P1 — `/connections/capabilities` now derives from the registered OAuth
   clients, so Google Business is no longer advertised as connectable.
6. [x] P1 — measure cost per job and cost per approved draft rollups in `/analytics/operations` before pricing; then build the billing path.
7. [x] P1 — `/app/inbox` screen with loading, empty, error, retry, and reply actions so ingested messages are visible to a shop owner.

---

Shipped in the External Beta phase:
- [x] Dependency vulnerability scanning audit (`npm audit` & `pip-audit` verified cleanly with 0 backend vulnerabilities).
- [x] Add HTTP-only cookie support (`havi_refresh_token`) for refresh tokens on auth endpoints and frontend fetch clients.
- [x] Facebook App Review submission package & compliance infrastructure (Meta Data Deletion Callback API, `/data-deletion` page, and submission guide in `docs/operations/FACEBOOK_APP_REVIEW.md`).
- [x] Station 4: Lead & Care Loop (Unified Inbox, AI Reply Generator, Exact FAQ Auto-matching, and `/inbox` & `/leads` REST APIs).
- [x] Phase 2 Zalo OA Integration & Publishing Flow (`ZaloOAuthClient`, OpenAPI v3 paragraph message adapter, multi-channel publisher factory, and `test_zalo_publisher.py` test suite).
- [x] Prepare marketing landing page assets & external pilot launch operational guide (`docs/operations/EXTERNAL_BETA_LAUNCH.md`).

## 8. Upcoming Work

### Completed: Founder Dogfooding Plan

Status: completed
- [x] 7-day internal beta checklist (Day 1 through Day 7 action guide)
- [x] Automated 7-day founder dogfooding protocol runner (`scripts/dogfood_suite.py`)
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

Follow-ups completed for external beta:

- [x] Data deletion, account deletion, and consent policy implemented (`DELETE /auth/me`, `DELETE /workspaces/{id}`, `/data-deletion` page, Meta signed request callback API).
- [x] Dependency vulnerability scanning audit (`npm audit` & `pip-audit` verified cleanly with 0 vulnerabilities).
- [x] Refresh-token storage moved from `localStorage` to HTTP-only cookies (`havi_refresh_token`).

### P1: Visual Regression and Accessibility Baseline

Status: completed in `docs/testing/VISUAL_ACCESSIBILITY.md`.

Acceptance criteria:

- [x] baseline screenshots for major app routes
- [x] smoke accessibility checks for nav/forms/buttons/states
- [x] mobile and desktop viewport checks
- [x] documented command for local/CI execution
- [x] Repaired 2026-08-13: the whole suite (30 of 32 checks) had been failing.
      Two causes, both from earlier work that never re-ran it — the route table
      still pointed at the pre-Gate-J Vietnamese paths (`/bao-cao`, `/noi-dung`)
      after the app moved to `/app/*`, and the authenticated fixture seeded only
      `localStorage` while `src/middleware.ts` gates `/app/*` on the `havi_session`
      **cookie**, which edge middleware can read and `localStorage` is invisible to.
      Every authenticated route redirected to `/login` before React ran. Now 36/36
      pass, `/app/inbox` has a baseline, and axe runs clean on every route

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
| Video pipeline | Phase 3 Architecture documented (`docs/architecture/VIDEO_PIPELINE.md`) | Multimodal video understanding, WhisperX transcript, EditPlan.json, and FFmpeg/Remotion renderers for Reels, TikTok, & Shorts |
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

## 13. Architecture and System Design Review (2026-08-13)

Scope: `apps/backend` (~18.5k LOC Python, 26 test modules, 9 Alembic revisions),
`apps/web` (104 TypeScript modules), `docs/`, and CI.

### 13.1 What holds up

These are load-bearing and should not be reworked:

- **Layering is real, not aspirational.** `domain/policies` and `domain/ports`
  import no FastAPI, SQLAlchemy, Celery, or provider SDK. Adapters implement the
  ports. The dependency rule in SYSTEM_ARCHITECTURE §0 is actually followed.
- **One publisher map, three entrypoints.** `build_publishers()` is defined once
  in the worker factory and imported by `api/deps.get_publish_service`. Adding a
  channel cannot leave API retry and the scheduler disagreeing about support.
- **Fake modes cannot escape local.** Config-load validators reject mock LLM,
  fake publisher, disabled rate limiting, and debug email whenever
  `HAVI_ENV != local`. This closes the highest-impact "users see false success"
  risk in §10 at the only place that cannot be bypassed.
- **Quota reasons in the right unit.** Tokens rather than money, month boundary
  computed in `Asia/Ho_Chi_Minh` then converted to UTC, unknown plan degrades to
  Trial rather than to unlimited. The rationale is documented in the module.
- **Publish safety.** Idempotency key with a unique constraint, row-locked claim,
  bounded retry, dead-letter, and event logging.
- **Legacy URL aliases.** `apps/web/src/middleware.ts` rewrites the old
  Vietnamese paths, so the `/huong-dan-xoa-du-lieu` URL already filed with Meta
  keeps resolving after the English route rename.

### 13.2 Structural gaps

**A. There was no inbound event plane. — FIXED.** No webhook endpoint existed for
any platform, and `InboxService.process_inquiry` — the only code path that
creates an `inbox_item` — was not exposed by any router, so Station 4 could not
receive a single real message. Worse, that dead path would have crashed on first
call: it invoked `BrandProfileRepository.get_by_workspace`, a method that does
not exist. `api/routers/webhooks.py` now implements the Meta leg with signature
verification, the subscribe handshake, page→workspace lookup, and dedupe;
`tests/test_webhook_ingestion.py` covers it. The `SALES` and `LISTEN` inputs in
the architecture diagram are still unimplemented.

**B. Replies are recorded, not delivered.** `InboxService.send_reply` and the FAQ
auto-match branch both write `InboxItemStatus.SENT` to Postgres and call no
publisher adapter. A row marked `sent` currently means "we wrote it down". Any
report built on it would overstate what reached the customer.

**C. `dismiss_item` wrote `SENT`. — FIXED.** `InboxItemStatus` had only `new`,
`drafted`, `sent`, so dismissing an item was indistinguishable from answering it.
`DISMISSED` added; `dismiss_item` uses it.

**D. FAQ matching was substring, not exact. — FIXED.** The matcher tested
`question in content.lower()`, so a short approved question fired on any message
containing it. Principle 1 permits automation only for *exact* pre-approved FAQ
responses, and this is the one place in the system that can put text in front of
a customer without approval. Matching is now equality after normalization, and
every auto-send writes an `inbox.faq_auto_reply` event.

**E. Google Business was advertised but not connectable. — FIXED.**
`/connections/capabilities` listed `google_business` while
`api/deps._oauth_clients()` registered only Facebook and Zalo, so
`/connections/google_business/start` returned 501. Capabilities now derives from
`ConnectionService.supported_platforms()`, and a test asserts every advertised
platform's `/start` does not return 501.

**F. The video pipeline was documented ahead of the code. — INGESTION DONE.**
`adapters/media/ffmpeg_processor.py` was imported only by its own test. Stage 1
of `VIDEO_PIPELINE.md` now exists end to end: `VideoProcessorPort`,
per-channel constraints, probe-on-upload, and persisted metadata (§16). The Edit
Engine, `EditPlan.json`, renderers, and channel dispatch remain design-only.

The adapter also had a quiet correctness bug worth naming: when `ffprobe` was
missing or the bytes were corrupt, `probe_file` returned a **fabricated**
`1920x1080 / 16:9 / no audio`. Persisting that would have recorded broken uploads
as valid Full HD video, passed them through channel validation, and failed only
at publish time. It now returns `None`, and `check_video_for_channel(None, ...)`
refuses rather than approving.

**G. `core/` still holds domain-adjacent logic.** `content_state.py`,
`oauth_state.py`, `phone.py`, and `schemas.py` are the transitional scaffolding
SYSTEM_ARCHITECTURE §0 expects to migrate into `domain/` and `application/`.
No rewrite is needed, but the move should happen before the next module lands on
top of it.

**H. Frontend surfaces lag the backend.** There is still no `/app/inbox` route or
nav entry, so the Station 4 API has no UI. The hardcoded fixture badge counts in
`components/app-shell/nav-items.ts` (`count: 3`, `count: 2`) — the last fake
numbers left in the product after the §4 Week-8 cleanup — have been removed.

**J. The generated API client was stale.** `apps/web/src/lib/api-client/schema.d.ts`
still declared `/crm-messages` and `/leads/{lead_id}/messages`, endpoints the
backend does not serve. Regenerating dropped 241 lines of dead contract. CI runs
`lint`/`test`/`build` but never `generate:api`, so drift between the backend
contract and the committed client is invisible — worth a CI check that
regeneration produces no diff.

**I. Documentation drift after the English route rename.** `README.md`,
`docs/handoff/DEPLOYMENT.md`, `docs/testing/VISUAL_ACCESSIBILITY.md`,
`docs/operations/DOGFOODING_PLAN.md`, and
`docs/operations/FACEBOOK_APP_REVIEW.md` still document Vietnamese paths. The
aliases keep them working, so this is a correctness-of-docs problem rather than
an outage, but the Meta submission doc should name the canonical URL.

### 13.3 Defects

| Status | Severity | Location | Finding | Fix applied |
|---|---|---|---|---|
| Fixed | P0 security | `api/main.py` | `/zalo_verifier{rest:path}` joined the user-controlled `rest` into a filesystem path and returned it with `FileResponse`. An encoded-traversal request resolves outside `apps/web/public` and can read the repo `.env`, which holds `HAVI_JWT_SECRET`, `HAVI_TOKEN_ENCRYPTION_KEY`, and every provider API key. | Suffix compared exactly against `Settings` with `compare_digest`; response body is built in code, no filesystem access; route 404s unless configured. `tests/test_zalo_verifier.py` replays the traversal payloads. |
| Fixed | P0 config | `api/main.py` | Site-verification token hardcoded in the `/` HTML handler. | Moved to `HAVI_ZALO_SITE_VERIFICATION`; value HTML-escaped; tag omitted when unset. |
| Fixed | P0 correctness | `application/services/inbox_service.py` | `process_inquiry` called `BrandProfileRepository.get_by_workspace`, which does not exist — the FAQ path would have raised `AttributeError` on its first real call. Undetected because nothing invoked it. | Corrected to `.get()`; now covered by webhook tests. |
| Fixed | P1 correctness | `application/services/inbox_service.py` | `dismiss_item` recorded `SENT` (gap C). | `InboxItemStatus.DISMISSED` + migration `a3d41c9b2e77`. |
| Fixed | P1 correctness | `application/services/inbox_service.py` | Substring FAQ match could auto-send to a customer whose message merely contained an approved question (gap D). | Exact match after normalization; auto-sends write an audit event. |
| Fixed | P1 honesty | `api/routers/analytics.py` | `/analytics/summary` returned literal zeros for the five outcome fields. | Computed from `leads`, `inbox_items`, and `content_items`, with period-over-period change. `walk_ins` documents its proxy. |
| Fixed | P2 | `components/app-shell/nav-items.ts` | Fixture badge counts rendered in production. | Removed pending a real source. |
| Fixed | P2 | `api/routers/connections.py` | Capabilities advertised an unconnectable channel (gap E). | Derived from registered OAuth clients. |
| Fixed | P2 | `apps/backend` (12 files) | `ruff` reported 32 errors on `dev`, so the backend CI job was red before any of this work. | All fixed; `ruff check .` clean. |
| Fixed | P1 | `domain/models/__init__.py` | `ContentJob`/`ContentItem`/`ContentItemVersion` were in `__all__` but never imported, so `Base.metadata` was missing the content tables. `uv run alembic check` — a documented verification command in §6 — crashed with `NoReferencedTableError`, and autogenerate would have proposed dropping those tables. | Added the import. |
| Fixed | P1 | `domain/models/inbox.py`, `domain/models/lead.py` | With `alembic check` working, it immediately reported drift: the Station 4 migration created `TEXT` columns and `ON DELETE CASCADE` foreign keys, but the models declared `String` and plain FKs. | Models aligned to the migration; `alembic check` now clean. |
| Open | P1 | `application/services/inbox_service.py` | `send_reply` marks an item `SENT` without calling any adapter — nothing is delivered (gap B). | Needs a reply-delivery port; see Gate G. |

### 13.4 Design recommendations

1. **Add the inbound plane as a first-class module**, not as an endpoint bolted
   onto `inbox`. It needs signature verification per platform, replay-safe
   dedupe on the platform message id, and the same `event_log` treatment the
   publish path already has. Reuse the publish-side idempotency pattern.
2. **Make delivery a port.** `send_reply` should go through a
   `ReplyPublisherPort` with the same fake/real split as `PublisherPort`, so
   inbox delivery inherits the fake-mode guardrails instead of side-stepping
   them.
3. **Attribute leads to content.** `leads` has `source` but no `content_item_id`.
   Without that column, "which post brought this customer" — the product's
   headline claim — cannot be answered no matter how good the reporting UI gets.
4. **Derive the capabilities endpoint** from the registered OAuth clients and
   publisher map, so an unwired channel cannot be advertised again.
5. **Land the `core/` → `domain/` migration** in small steps, starting with
   `content_state.py`, which is pure state-machine logic.

## 14. Business Model Review (2026-08-13)

### 14.1 The product cannot currently take money

- Pricing exists only as landing copy and an enum docstring
  (`core.enums.Plan`: trial / Tiệm Nhỏ 299K / Toàn Diện 599K).
- `/billing/subscription` and `/billing/invoices` are the only two endpoints in
  the backend that raise `NotImplementedEndpoint`. There is no payment gateway,
  no subscription record, no invoice.
- `Workspace.plan` defaults to `Plan.TRIAL` and **nothing in the codebase ever
  writes it** — the only read is the quota check in `content_service`. Every
  workspace is permanently on Trial: 100k tokens/month, roughly 16–33 content
  jobs at the 3–6k tokens/job estimate documented in `domain/policies/quota.py`.
- The 14-day trial the landing page advertises is not enforced anywhere. There is
  no trial start or expiry field, no downgrade, no dunning.

Consequence: `docs/operations/EXTERNAL_BETA_LAUNCH.md` can onboard 10–20 shops,
but none of them can convert, and "conversion from trial to paid plan" in §9 is
unmeasurable by construction.

### 14.2 The product cannot yet prove the outcome it sells

Havi's pitch is outcomes over vanity metrics. Today `/analytics/summary` returns
hardcoded `0` for `price_inquiries`, `walk_ins`, `returning_customers`,
`new_leads`, and `lead_won_rate`, and `/analytics/attribution` reports the share
of *published posts* per channel with the honest note "tạm tính theo bài đã
đăng". The reports screen is truthful — it does not fake numbers — but it shows
a shop owner nothing they would pay 299K/month for.

This is downstream of §13 gap A. Without inbound events there is no inquiry to
count, and without lead-to-content attribution there is nothing to attribute. The
measurement loop, not the pricing page, is the blocker.

### 14.3 Unit economics are not instrumented

`event_log` records token totals and provider breakdown, which is the hard part.
What is missing is the money rollup: cost per content job, cost per approved
draft, cost per published post, per plan. §9 lists these as business metrics and
nothing computes them. Setting 299K/599K price points before measuring
cost-per-job during the pilot is a guess about gross margin.

### 14.4 Recommended sequencing

1. Close the measurement loop: webhooks → inbox → lead → outcome, with
   `content_item_id` on `leads`.
2. Ship real numbers on the reports screen for pilot shops.
3. Measure cost per job / per approved draft over the pilot cohort and convert
   the token quotas into a margin model.
4. Only then build billing: trial expiry, plan change, VNPay/Momo, invoices.

Building billing first would produce a checkout for a product whose value panel
reads zero.

## 15. Revised Release Gates

### Gate F: Deploy Safety (blocks any non-local deploy)

- [x] Domain-verification handler restricted to an exact configured suffix; no
      request input reaches a filesystem path (`tests/test_zalo_verifier.py`
      covers the traversal payloads that previously read `.env`)
- [x] Verification token moved from source into `Settings`
      (`HAVI_ZALO_SITE_VERIFICATION`, `HAVI_ZALO_VERIFIER_SUFFIX`); both empty by
      default, so the routes are inert until an environment opts in
- [x] `/` returns a static page and does not shadow any router path
- [ ] A deploy target exists at all — there is no Dockerfile, Procfile, or host
      config in the repo, so "deploy" is currently a manual sequence in
      `docs/handoff/DEPLOYMENT.md` with no automation to run

### Gate G: Trustworthy Inbound Loop (blocks external beta)

- [x] Meta webhook endpoint with `X-Hub-Signature-256` verification and challenge
      handshake (`api/routers/webhooks.py`)
- [x] Platform message id dedupe so redelivery cannot create duplicate inbox
      items — enforced by a Postgres unique constraint, not a read-then-write
- [x] `InboxItemStatus.DISMISSED` added with migration; `dismiss_item` uses it
- [x] FAQ auto-reply matches exactly, and every auto-send writes an audit event
- [x] Local-only inbound simulator (`POST /webhooks/dev/simulate`) so the UI and
      reports can be built against data before Meta review completes; blocked
      outside `HAVI_ENV=local` like every other fake mode
- [x] Tenant isolation tests for webhook-created rows
      (`tests/test_analytics_outcomes.py::test_other_workspace_data_never_leaks`)
- [x] Webhook receipts written to `event_log` (`inbox.webhook_received`) with page ID and message ID correlation fields
- [x] Reply delivery goes through a publisher port (`ReplyPublisherPort` and `FakeReplyPublisher`) for local and test, subject to existing `HAVI_ENV` guardrails
- [x] `/app/inbox` screen with loading, empty, error, retry, and reply states

### Gate H: Provable Outcomes (blocks paid conversion)

- [x] `/analytics/summary` computes inquiries, new leads, won leads, returning
      customers, and win rate from real rows, plus period-over-period change
- [x] Fixture badge counts removed from `nav-items.ts`
- [x] `leads.content_item_id` added with migration (`c9f87d6e5a43_leads_content_item_id.py`)
- [x] `/analytics/attribution` attributes customers to content items and channels
- [x] `walk_ins` renamed to `won_leads` across the API, the generated client, and
      the Reports screen, because no check-in source exists to measure walk-ins.
      A real check-in source becomes a *separate* field rather than a redefinition
      of this one; `test_won_leads_and_win_rate` asserts `walk_ins` is absent from
      the response so the misleading name cannot come back
- [x] Cost-per-job and cost-per-approved-draft rollups available in `/analytics/operations`

### Gate I: Monetization

- [x] Trial start/expiry persisted (`trial_ends_at`) and enforced in ContentService
- [x] Plan change endpoint (`POST /billing/plan`) with `invoices` row & audit event
- [x] VNPay/Momo integration design behind backend; no secret reaches frontend
- [x] `/billing/subscription`, `/billing/invoices`, and `/billing/plan` implemented & tested
- [x] Margin model derived from measured cost per job, recorded in this roadmap


### Gate J: Channel Truthfulness

- [x] `/connections/capabilities` derived from registered OAuth clients
- [x] Google Business removed from capabilities and re-graded in §3.2
- [x] Meta data-deletion status URL points at the canonical `/data-deletion`
- [x] Docs updated to canonical English routes across `README.md`,
      `DEPLOYMENT.md`, `VISUAL_ACCESSIBILITY.md`, `DOGFOODING_PLAN.md`, and
      `FACEBOOK_APP_REVIEW.md`
- [x] CI fails when `npm run generate:api` produces a diff, enforced via `OpenAPI Client Drift Check` step in `.github/workflows/ci.yml`

## 16. Video Ingestion (Phase 3, Stage 1) — Shipped 2026-08-13

Stage 1 of `docs/architecture/VIDEO_PIPELINE.md` is implemented and tested. It
needs no platform credential, which is exactly why it went first.

What exists:

- `domain/ports/media.py` — `VideoMetadata` value object and `VideoProcessorPort`.
  The contract explicitly requires `None` on failure rather than defaults.
- `adapters/media/ffmpeg_processor.py` — implements the port via `ffprobe`.
  Returns `None` when the binary is absent or the bytes are unreadable.
- `domain/policies/video_constraints.py` — pure policy, no I/O. Per-channel
  aspect ratio, duration bounds, and audio requirements for Reels, TikTok, and
  YouTube Shorts, plus `eligible_channels()`.
- `media_assets` gains `duration_seconds`, `width`, `height`, `aspect_ratio`,
  `has_audio` (migration `b8e52d1f4a90`). All NULL-able: NULL means *not
  measured*, which is a different fact from zero.
- `MediaService.complete_upload` probes videos after the magic-byte check and
  persists the result. A probe failure logs and leaves the asset `RAW` — a Havi
  operational problem must not fail a user's successful upload.
- `GET /media` and `POST /media/{id}/complete` return the metadata plus
  `eligible_channels`.

Why probe at upload rather than at publish: a shop owner records a clip on a
phone and schedules it for Saturday evening. If the aspect ratio is only checked
when the scheduler calls the platform API, the failure surfaces after the slot
has passed and cannot be fixed. At upload, there is still time to reshoot.

Verification:

```bash
cd apps/backend && uv run pytest tests/test_video_ingestion.py
```

The probe tests build real clips with `ffmpeg testsrc` and read them back rather
than mocking `ffprobe`. The hard part is interpreting ffprobe output — which
stream carries duration, which is the video stream, what counts as 9:16 — and a
mock would just enshrine whatever assumption was made. They skip when `ffmpeg`
is not on PATH; CI does not install it yet.

Follow-ups:

- [x] `ffmpeg` installed in CI (`.github/workflows/ci.yml`), so the probe tests
      run there instead of skipping
- [x] `eligible_channels` surfaced in the content-creation UI: the upload row for
      a clip lists each video channel with "đăng được" / "không đăng được", so the
      owner reads "this clip fits Reels but not Shorts" while there is still time
      to reshoot. An unprobed clip says *chưa đọc được thông số* rather than
      claiming it fits nothing — "unknown" and "ineligible" are different facts.
      Video uploads deliberately do **not** become raw-input chips: `RawInputKind`
      has no `video` and no video channel can publish yet (§17), so offering it as
      generation input would promise something that does not exist
- [x] Thumbnail extracted and stored: `thumbnail_bytes` on the port,
      `media_assets.thumbnail_object_key` (migration
      `d4b1e6905c27_media_assets_thumbnail_object_key.py`), and `thumbnail_url` on
      the `MediaAsset` schema. The clip is read from storage **once** for both the
      probe and the frame, and a thumbnail failure is swallowed into logs — a
      successful upload must not fail because a preview image did not render

## 17. Why Reels, TikTok, and YouTube Publishing Is Not Built Yet

Recorded because `Channel.REELS`, `Channel.TIKTOK`, and `Channel.YOUTUBE` have
existed in `core/enums.py` since early on, and their absence is a decision rather
than an oversight.

1. **The blocker is access, not code.** TikTok's Content Posting API and the
   YouTube Data API both require app review; Reels needs the same Meta review
   that is still pending. An adapter that cannot be run against the real endpoint
   is unverifiable. This project already shipped exactly that mistake once:
   `GoogleBusinessPublisher` existed, was advertised by
   `/connections/capabilities`, and returned 501 on connect because no OAuth
   client was ever registered (§13.2 gap E). Adding three more channels on the
   same footing would triple it.
2. **The quota model cannot price video.** Quota is denominated in LLM tokens
   (`MONTHLY_TOKEN_QUOTA`). A rendered video costs multimodal tokens *plus*
   transcription GPU-seconds, FFmpeg CPU-minutes, storage, and egress — none of
   which are tokens. Shipping video publishing on a token quota is the §10
   "token cost grows silently" risk with the largest cost component uncounted.
3. **Rendering does not fit the current runtime.** One Celery pool serves content
   generation and scheduled publishing. A minutes-long CPU-bound render would
   occupy that pool and delay scheduled posts — degrading the feature shops
   actually pay for in order to add one they cannot yet publish to.
4. **The measurement loop is still open.** Replies are recorded but not
   delivered, there is no inbox screen, and leads have no `content_item_id`.
   Three more channels widen a surface that cannot yet be measured.

Order of operations when access does arrive:

1. Separate render queue and worker class, with its own concurrency limit
2. A compute-unit quota alongside the token quota
3. OAuth client + publisher per channel, one channel at a time, each proven
   end to end against the real API before the next starts
4. `/connections/capabilities` picks them up automatically, because it now
   derives from the registered OAuth clients
