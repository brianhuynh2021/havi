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

> Re-derived from the 2026-08-22 public-launch audit. The list below the divider
> is retained as delivery history. The active source of truth is now §25,
> **10/10 Public Launch Program**. A checked historical item does not override a
> regressed test, a newer security finding, or a failed end-to-end release gate.

> Zalo scope is deferred by decision on 2026-08-13. Zalo OAuth, publishing,
> webhooks, and domain verification stay in the codebase but are out of the
> active queue and out of the gates below until the channel is picked back up.

Active now — execute in this order; full acceptance criteria are in §25:

1. [ ] **P0 Revenue integrity** — remove every production path that activates a
   plan before a verified payment; validate webhook signature, invoice, amount,
   currency, status, and unique gateway reference; add replay and reconciliation
   tests.
2. [ ] **P0 Production boot and secret safety** — make the production compose
   configuration boot with real providers, fail on missing secrets, remove
   default credentials, keep PostgreSQL/Redis/object storage private, and use
   private media with signed access.
3. [ ] **P0 Truthful delivery state** — never mark publish or reply success until
   the platform confirms it; persist the Facebook sender PSID; separate message
   replies from comment replies; reconcile ambiguous external outcomes.
4. [ ] **P0 Release test gate** — restore backend to 100% pass and repair the
   visual/accessibility harness to 36/36 on the current routes and UI. No release
   is allowed with a red check.
5. [ ] **P1 First-value journey** — replace simulated onboarding with a Business
   Truth Pack, connect one Facebook Page, and reach one verified live post in a
   median of five minutes or less.
6. [ ] **P1 Mobile product excellence** — reduce Content Studio to one primary
   mobile flow, move advanced controls behind progressive disclosure, meet WCAG
   2.2 AA, and meet Core Web Vitals `Good` thresholds at p75.
7. [ ] **P1 Server-side entitlements** — enforce plan/channel/post/video/lead/
   location limits in the backend and align all prices, quotas, trial copy, and
   invoices.
8. [ ] **P1 Facebook closed loop** — Multi-Page Picker, verified Page publishing,
   Messenger reply delivery, inbox-to-lead conversion, and real outcome reports.
9. [ ] **P2 Platform approvals** — run Meta review, Google Business approval,
   TikTok Direct Post audit, and YouTube audit in parallel; keep unapproved
   channels labeled Beta/export-only.
10. [ ] **P2 Paid pilot and SLO proof** — Customer Zero plus 5–10 design partners,
    real low-value PayOS transactions, alerting, restore rehearsal, and 30 days
    of measured SLO/activation/retention evidence before public launch.

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

Status: **regressed and release-blocking as of 2026-08-22**. The historical
baseline repair reached 36/36, but the current audit run reached only 2/36 after
subsequent route, heading, and UI changes. This result means the harness and its
baselines are no longer current; it does not by itself prove that every route
has an accessibility defect.

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
- [ ] Repair 2026-08-22 regression: update the route readiness contract and
      intentional screenshots for the current product only after reviewing each
      diff; add Billing and Video Studio coverage; return the suite to 36/36 or
      higher without blindly updating snapshots.

## 9. Metrics That Matter

North Star metric:

- **verified weekly business outcomes per active workspace**: a platform-confirmed
  published post, delivered reply, created lead, booked appointment, attributed
  POS sale, or verified returning customer. Drafts and clicks are not outcomes.

Product metrics:

- signup → Business Truth Pack completion rate
- signup → first connected Page rate
- signup → first verified live publish activation rate
- median and p90 time from signup to first verified value
- time from first draft to first approved post
- approved drafts per workspace
- platform-confirmed published posts per workspace
- publish failures by kind
- reconnect rate
- owner edits per draft
- support time per workspace
- day-1/day-7 activation and week-4 retention by acquisition cohort
- weekly active workspaces with at least one verified outcome

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
- payment checkout → verified payment → activated subscription conversion
- unpaid activation count (target: zero)
- month-one paid renewal and gross revenue retention

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
- [x] Dockerfiles, production compose, nginx configuration, and deploy scripts
      now exist.
- [ ] Production configuration boots successfully with `HAVI_ENV=production`
      and explicit real email, LLM, and publisher providers. The 2026-08-22
      audit fails at configuration validation because production inherits the
      debug email default; mock LLM/fake publisher defaults would also be
      rejected if not explicitly disabled.
- [ ] Remove all default production database, object-storage, JWT, webhook, and
      token-encryption secrets; fail startup when a required secret is absent.
- [ ] PostgreSQL, Redis, and object storage are internal-only; media is private
      by default and delivered through signed access rather than an anonymous
      bucket with wildcard CORS.
- [ ] Readiness checks verify PostgreSQL, Redis, object storage, and the worker
      queue; liveness checks only process health; a failed deploy rolls back.

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
- [x] `/billing/subscription`, `/billing/invoices`, checkout creation, and PayOS/
      VietQR webhook routes exist.
- [ ] Remove or local-gate `POST /billing/plan`: it currently changes the plan
      and grants 30 days while creating only a `PENDING` invoice.
- [ ] Remove frontend fallback/manual confirmation paths that call `changePlan`
      when checkout fails or when a user claims to have transferred money.
- [ ] Require and verify the PayOS signature in every non-local environment;
      reject a generic webhook when its required signature is missing.
- [ ] Activate a subscription only when invoice, amount, currency, successful
      payment state, and unique gateway reference all match in one transaction.
- [ ] Add replay protection, idempotent redelivery, reconciliation, refund/
      cancellation handling, and an immutable payment audit trail.
- [ ] Enforce plan entitlements in the backend and align posts, token quota,
      video, lead, channel, location, and branch limits with pricing copy.
- [ ] Execute real low-value PayOS end-to-end tests because PayOS has no sandbox;
      prove success, wrong amount, invalid signature, replay, timeout, and retry.
- [ ] Margin model and final price points are derived from measured pilot cost
      per verified outcome and month-one renewal behavior.


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

---

## 18. Niche Execution & Closed-Loop Ingest: Real Estate Brokers & Local Shops (2026-08-16)

### 18.1 Target Personas & Core Behavioral Realities

1. **Cò Bất Động Sản (Real Estate Brokers):**
   - **Daily Reality:** On the road conducting site visits, legal notary paperwork, and taking 5–10 photos of land, houses, and red books (`sổ đỏ`) on mobile devices. Exhausted by evening, lacking copywriting skills and short-form video hooks, yet fearing algorithmic invisibility if they do not post daily.
   - **Burning Pain:** Inability to consistently produce high-converting Facebook/Zalo posts and short video hooks (TikTok/YouTube Shorts) from raw property photos.
   - **Willingness to Pay:** High. A single transaction yields tens of millions VND; paying 299k–599k/month for automated daily listing presence and 24/7 lead capture is an immediate positive ROI.

2. **Chủ Tiệm (Spas, Salons, F&B, Auto/Motorbike Repair, Local Clinics):**
   - **Daily Reality:** Hands literally occupied with chemical treatments, cutting hair, cooking, or servicing customers. 100% mobile device users.
   - **Burning Pain:** Customer inquires at 11 PM or during rush hours; missing or delaying response by 15 minutes causes the lead to go to a neighboring competitor.
   - **Willingness to Pay:** High. Replaces a 2.5M–3M/month part-time page moderator who frequently sleeps through late-night inquiries.

### 18.2 Competitive Moat vs. DIY Tools (LovinBot, Unikon, ChatGPT Wrappers)

- **The DIY Trap:** Competitors provide complex dashboards with dozens of templates, prompt inputs, and manual copy-pasting. Shop owners abandon DIY tools within 3–4 days due to cognitive overload.
- **Havi's "Outcome over Tool" Moat:**
  1. **30-Second Ingest:** Single mobile upload (photo + voice/text note) -> Havi generates channel-native drafts automatically.
  2. **Zero-Effort Closed Loop:** Content Engine -> 1-Tap Approval -> Multi-channel publishing -> 24/7 Auto Lead Care.
  3. **Brand Knowledge Base (Retention Lock-in):** Havi accumulates and remembers the shop's pricing table, service menu, property catalog, and FAQs. Switching costs increase over time.

---

## 19. The POS-Utility Paradigm & 24/7 Auto-Pilot Closing

### 19.1 Utility Guarantee over Speculative Traffic Promises

- Shifting the core value proposition from speculative "10x viral growth" to measurable operational utility (akin to KiotViet / Sapo POS systems):
  - **Zero Missed Inquiries:** Instant 24/7 automated greeting, price quote delivery, and consultation via official Meta Graph API.
  - **Single Pane of Glass (Unified Inbox):** Aggregated incoming inquiries across Facebook, Instagram, and connected channels.
  - **Continuous Channel Liveness:** Scheduled content cadence ensures the page remains active, signaling trust to walk-ins and referrals.

### 19.2 Required Engineering Enablers for Commercial Readiness

1. **Outbound Meta Graph API Auto-Reply (Lead Care Station 4 Dispatch):**
   - Wire `api/routers/inbox.py` and worker reply tasks to deliver real outbound messages through `FacebookPublisherAdapter` via official Meta Graph API endpoints.
   - Maintain strict audit trail and tenant isolation.
2. **Mobile-First UX Optimization:**
   - Touch-optimized targets (>= 48px) for mobile Safari and Chrome.
   - 1-tap fast media ingest and quick approval actions designed for single-thumb mobile usage.
   - Eliminating technical jargon from UI (`Prompt`, `Temperature`, `LLM Provider` replaced with `Tạo bài đăng`, `Bảng giá dịch vụ`, `Khách cần tư vấn`).

---

## 20. Commercialization & 7-Day Dogfooding Go-To-Market Blueprint

### 20.1 Pricing & Unit Economics (No-Brainer Tiering)

| Tier | Target User | Price (VND/month) | Entitlements | Gross Margin Target |
|---|---|---|---|---|
| **Khởi Nghiệp (Starter)** | Chủ tiệm solo, Spa mini, Quán F&B | **199,000 – 299,000 đ** | 1 Fanpage/IG, 24/7 Auto Inbox & FAQ, 30 AI posts/month | >= 85% |
| **Chuyên Nghiệp (Pro)** | Cò BĐS, Chuỗi 2-3 quán, Dịch vụ | **599,000 đ** | Multi-channel (FB + TikTok Hooks + Google Business), Phone/Appointment Lead extraction, CRM Nudge | >= 80% |

### 20.2 Automated VietQR Subscription Activation

- Integrate automated VietQR payment flows (PayOS / SePay / Casso webhook integration) for instant subscription upgrades within 3 seconds of scanning.
- Auto-generate VAT invoices and update `Workspace.plan` seamlessly upon idempotent webhook receipt.

### 20.3 7-Day Customer Zero Validation Protocol

- **Day 1–2:** Dogfood internal operations at Trung Tâm Công Nghệ Nhật Minh (ingest daily workshop repair photos + auto-inbox reply).
- **Day 3–4:** Deploy pilot with 1 Real Estate Broker (uploading land photos + generating listing posts and 3-second short-form scripts).
- **Day 5–6:** Deploy pilot with 1 Local Spa/Salon (configuring service price list + 24/7 auto lead consultation).
- **Day 7:** Review outcome metrics (`/analytics/summary`), verify zero dropped leads, and initiate first paid conversion via VietQR.

---

## 21. Strategic 5-Phase Commercial Scale Master Plan

The complete 5-phase product, engineering, and monetization roadmap from Local Dogfooding to Global Scale is formally recorded in [`docs/product/COMMERCIALIZATION_PHASES.md`](COMMERCIALIZATION_PHASES.md):

* **Phase 1 (Month 1):** The Cash-Flow Core Engine (30s Mobile Ingest, Live Meta Reply, VietQR Activation, Dogfooding at Trung Tâm Công Nghệ Nhật Minh).
* **Phase 2 (Months 2–3):** Local Dominance & AI Video Studio (Google Maps Local SEO Ranker, 3s TikTok Hooks, Smart Lead Triage).
* **Phase 3 (Months 4–5):** Customer Retention & Smart CRM Nudge Loop (Automated re-activation of past leads, POS sales attribution, Brand Knowledge Base v2).
* **Phase 4 (Months 6–8):** Autonomous Marketing Radar & Ads Copilot (AI Trend Scout, 1-tap Meta Ads Lite).
* **Phase 5 (Months 9+):** Global Scale & Multi-Location Enterprise (Stripe multi-currency billing, global affiliate PLG, franchise mode).

---

## 22. Comprehensive Strategic & Architectural Appraisal (MIT/Stanford Board Review)

### 22.1 Executive Commercial Readiness Scorecard — superseded 2026-08-22

The earlier 91/100 appraisal mixed architectural intent, planned work, and UI
copy with production evidence. It is retained in Git history, but it is not a
valid launch decision. The 2026-08-22 audit grades only what a new merchant can
complete safely end to end with real external systems.

| Pillar | Audited score | Current decision |
|---|---:|---|
| Product idea and customer value | 7/10 | Strong thesis; paid renewal and verified outcome evidence are still missing. |
| Overall interface | 6/10 | Visually credible, but Content Studio is dense and the mobile path delays first value. |
| New-user activation | 4/10 | Onboarding simulates learning/drafts instead of producing one verified live outcome. |
| Real channel integrations | 3/10 | Facebook is the first viable wedge; Google/TikTok/YouTube require contract fixes and/or external approval. |
| Payment and revenue protection | 1/10 | A pending invoice can currently grant a paid plan; webhook amount/signature gates are incomplete. |
| Production operations | 2/10 | Production configuration, secret/network posture, alert delivery, readiness, and current test gates are not launch-ready. |
| **Public commercial readiness** | **3/10** | **NO-GO for public paid launch. Founder dogfood only; supervised design partners after P0 closes.** |

The replacement target scorecard, execution plan, and evidence gates are in §25.

### 22.2 The 10-Year Evolution Roadmap (2026–2036)

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        HAVI 10-YEAR HORIZON EVOLUTION                                  │
├───────────────────┬───────────────────┬───────────────────┬────────────────────────────┤
│ GIAI ĐOẠN 1 (Năm 1-2)│ GIAI ĐOẠN 2 (Năm 3-5)│ GIAI ĐOẠN 3 (Năm 5-7)│ GIAI ĐOẠN 4 (Năm 7-10)     │
│ Cash-flow Core    │ Voice AI & POS    │ Local SLM On-Prem │ Global Autonomous Commerce │
│ Local Domination  │ Auto-Pilot CMO    │ Franchise Multi-Store│ Hệ sinh thái kinh doanh AI │
└───────────────────┴───────────────────┴───────────────────┴────────────────────────────┘
```

1. **Years 1–2 (Cash-Flow Core & Local Domination):**
   - Solidify Havi as the "KiotViet of AI Marketing & 24/7 Lead Care" across Vietnam.
   - Frictionless PayOS VietQR automated monetization.
   - Local SEO Google Maps dominance and automated 9:16 Video Studio.
2. **Years 3–5 (Autonomous AI CMO & Voice AI Call Agent):**
   - Natural Vietnamese Voice AI Call Agent for appointment reminders and customer care.
   - Closed-Loop POS Attribution directly tying social posts to cash register receipts.
   - Evolution from Co-pilot (1-tap approval) to Auto-pilot for trusted routine campaigns.
3. **Years 5–10 (Global AI Autonomous Commerce & Local SLMs):**
    - On-premise / Edge Small Language Models (SLMs) for zero-latency, private enterprise knowledge.
    - International expansion (SEA, US/EU) with Stripe multi-currency billing ($29–$79/mo).
    - Target Valuation & Scale: $10M–$50M ARR.

---

## 23. Planned Milestone #12: Super-Admin Portal & Enterprise Customer Support

To support cohort scaling (50–300 pilot workspaces) and ensure zero unassisted customer churn, the following Super-Admin and Customer Support capabilities are planned for upcoming implementation:

### 23.1 Core Capabilities
1. **Workspace Impersonation (Support Mode):**
   - Cryptographically signed temporary support token allowing authorized admins to view a customer's workspace with strict read-only/audit logging.
   - Eliminates customer frustration when reporting UI or publishing issues without sharing passwords.
2. **Tenant Health Score & Churn Risk Radar:**
   - Real-time heuristic scoring of merchant engagement:
     - 🟢 **Healthy:** Active posting $\ge 3$ posts/week, leads answered $< 1$ hour.
     - 🟡 **Needs Care:** Inactive 7+ days or platform token expiring within 3 days $\rightarrow$ Auto-prompt proactive CSKH outreach via Zalo/SMS.
     - 🔴 **At-Risk:** 14+ days no logins $\rightarrow$ Flag for founder check-in.
3. **Automated Incident & Webhook Alerting (`#havi-ops-alerts` Telegram Channel):**
   - Real-time bot notifications sent to the engineering team upon repeated 5xx errors from Meta/TikTok/OpenAI or sudden surges in Dead-Letter publishing jobs.
4. **In-App Proactive Support Widget:**
   - 1-tap floating support widget for shop owners to instantly reach out to the Havi operations desk.
5. **Dual-Key Secret Rotation & Distributed Tracing:**
    - Zero-downtime re-encryption for `HAVI_TOKEN_ENCRYPTION_KEY` and OpenTelemetry APM tracing for sub-millisecond bottleneck visibility.

---

## 24. Planned Milestone #11: Multi-Page Picker & Dynamic Channel Switcher (Dropdown)

Based on direct founder dogfooding feedback with multi-brand accounts (*Trung Tâm Công Nghệ Nhật Minh* & *Havi Sandbox*):

### 24.1 User Need & Problem
When a shop owner manages multiple Facebook Pages (e.g., separate brand pages, multiple regional branches, or test environments), OAuth returns all authorized pages. Currently, the system deterministically picks the highest-priority business page. Merchants need the flexibility to view all connected pages and switch their primary active publishing/inbox page with a single click.

### 24.2 Architecture & Feature Specification
1. **Multi-Page Token Vault:**
   - Store all authorized page tokens in `platform_connections` or a linked `workspace_page_assets` table.
2. **Dynamic UI Dropdown Selector:**
   - On `/app/connections` and Onboarding Step 2, render a clean dropdown selector when $\ge 2$ Pages are available.
   - Live preview of page avatar, page name, and follower count.
3. **Instant Active Page Switcher:**
   - 1-click active page switching without re-triggering the Facebook OAuth popup.
   - Dynamic update to AI Lead Agent webhook listeners and scheduled calendar jobs for the active page.

---

## 25. 10/10 Public Launch Program (2026-08-22)

### 25.1 Decision, Scope, and Scoring Rule

Status: **active; supersedes earlier commercial launch declarations**.

The objective is not to add enough features to claim 10/10. The objective is to
produce repeatable evidence that a Vietnamese shop owner can receive value,
publish safely, collect a lead, pay, and continue using Havi without founder
intervention. A workstream reaches 10/10 only after all acceptance criteria pass
and the target metrics hold for 30 consecutive pilot days.

Until Gate 10 in §25.10 passes:

- public paid acquisition is blocked;
- Founder Customer Zero dogfooding is allowed;
- supervised design-partner access is allowed only after P0 closes;
- unapproved external channels must be hidden, disabled, or labeled Beta/
  export-only with truthful limitations;
- no marketing surface may display hypothetical ROI as measured customer value.

### 25.2 North Star and Golden Journey

North Star:

> **Verified weekly business outcomes per active workspace.**

A verified outcome is a platform-confirmed published post, a delivered reply, a
created lead, a booked appointment, an attributed POS sale, or a verified
returning customer. Draft generation, clicks, impressions, and simulated states
do not qualify.

Golden journey:

1. Sign up.
2. Complete the Business Truth Pack.
3. Connect and select one Facebook Page.
4. Capture one photo, voice note, or short text.
5. Receive one best grounded draft.
6. Review and approve.
7. Publish and receive a real external ID/permalink.
8. Receive/reply to an inquiry and convert it to a lead.
9. See the verified outcome report.
10. Create PayOS checkout, complete payment, and activate the entitled plan from
    a verified webhook only.

Required product events:

```text
signup_completed
business_truth_completed
channel_connected
first_draft_generated
first_draft_approved
first_publish_verified
first_inquiry_received
first_value_verified
checkout_created
payment_verified
subscription_activated
```

Every event must include workspace, timestamp, source, correlation/request ID,
and a schema version without storing secrets or unnecessary customer content.

### 25.3 Target Scorecard

| Workstream | 10/10 evidence standard |
|---|---|
| Product idea and customer value | At least 5 real paying pilots; >=80% month-one renewal; >=60% weekly use; each retained shop proves either >=2 hours/week saved or at least one verified lead/outcome. |
| Overall interface | >=90% golden-journey task completion without assistance; System Usability Scale >=80; WCAG 2.2 AA; no critical mobile defect; p75 Core Web Vitals all `Good`. |
| New-user activation | >=60% of qualified signups reach first verified live publish; median time-to-value <=5 minutes and p90 <=10 minutes; no simulated learning or phantom drafts. |
| Real channel integrations | Approved/capable channels publish >=99% of valid requests; zero false success; every success stores external ID/permalink; ambiguous outcomes reconcile automatically. |
| Payment and revenue protection | Zero unpaid activations; 100% non-local webhooks require valid signatures; exact amount/currency/invoice match; replay-safe and daily-reconciled ledger. |
| Production operations | User-journey SLO >=99.9%; P1 MTTR <30 minutes; RPO <=24 hours; RTO <=2 hours; restore rehearsed; 100% required automated checks pass before release. |

### 25.4 Workstream A — Product Value: 7/10 → 10/10

Owner outcome: the product proves useful operational value before it claims
marketing ROI.

- [ ] Interview at least 15 owners across Nhật Minh, local services, F&B, beauty,
      repair, and real-estate workflows; record job, trigger, current workaround,
      frequency, consequence, and willingness to pay.
- [ ] Recruit 5–10 design partners with explicit baseline measurements: weekly
      content time, posts, response time, inquiries, leads, appointments, and POS
      revenue where available.
- [ ] Freeze the paid MVP promise to: **one capture → one approved Facebook post
      → one verified publish → one inbox/lead loop**.
- [ ] Remove hardcoded savings, agency-cost, ROI multiple, trial-extension, and
      algorithm-year claims unless backed by workspace data or labeled clearly
      as an example.
- [ ] Build proof-of-value reporting from platform, inbox, lead, and POS records;
      expose the data lineage and confidence level for attribution.
- [ ] Measure cost per generated draft, approved draft, verified publish, reply,
      lead, and retained paid workspace.
- [ ] Run willingness-to-pay interviews only after the owner has experienced a
      verified outcome; finalize price/limits from margin and renewal evidence.
- [ ] Do not resume broad feature expansion until at least 5 pilots pay and the
      month-one renewal threshold is measured.

### 25.5 Workstream B — Interface: 6/10 → 10/10

Owner outcome: a non-technical merchant can complete the golden journey with one
thumb and without learning marketing terminology.

- [ ] Redesign the first viewport of Content Studio around only three decisions:
      source, goal, and **Create post**.
- [ ] Move review mode, automation, variants, per-channel settings, trend/SEO,
      hook controls, and schedule tuning behind progressive disclosure.
- [ ] Keep one primary CTA per state; add explicit loading, empty, blocked,
      retry, reconnect, and partial-success states.
- [ ] Replace technical/internal copy with owner language; mark examples, Beta
      capabilities, and external-platform completion steps truthfully.
- [ ] Use >=48 px internal touch targets and validate single-thumb operation at
      375 px, 390 px, and 430 px widths plus desktop.
- [ ] Reach WCAG 2.2 AA across auth, onboarding, dashboard, content, calendar,
      inbox, reports, billing, settings, connections, video, and operations.
- [ ] Instrument real-user Core Web Vitals and meet p75 LCP <=2.5 s, INP <=200
      ms, and CLS <=0.1 on mobile and desktop.
- [ ] Run three moderated usability rounds with at least five target owners per
      round; close all critical/high findings and reach >=90% unassisted task
      completion plus SUS >=80.
- [ ] Restore reviewed visual baselines and accessibility checks; snapshot
      updates require an intentional diff review.

Research baseline:

- [WCAG 2.2](https://www.w3.org/TR/WCAG22/)
- [Core Web Vitals thresholds](https://web.dev/articles/defining-core-web-vitals-thresholds)
- [Stanford Fogg Behavior Model](https://behaviordesign.stanford.edu/resources/fogg-behavior-model)

### 25.6 Workstream C — Activation: 4/10 → 10/10

Owner outcome: the first session creates one real, observable result.

- [ ] Replace timer-based onboarding claims with persisted progress and real API
      operations; never claim that Havi learned the business or created drafts
      unless those artifacts exist.
- [ ] Build a Business Truth Pack covering name, address, opening hours,
      services, prices, offer conditions, CTA/contact, FAQs, prohibited claims,
      and media/automation consent.
- [ ] Add starter templates by industry without inventing business facts; every
      generated factual claim must trace to the Truth Pack or owner input.
- [ ] Make channel capability/precondition checks explicit; if no channel is
      connected, offer an honest demo/export path rather than an active publish
      control.
- [ ] Connect and select the first Facebook Page during onboarding; resume safely
      after OAuth interruption or failure.
- [ ] Generate one best draft first; expose variants only after first value.
- [ ] Return platform-confirmed status and permalink after the first publish.
- [ ] Start the meaningful trial window at first connected channel or first
      verified value, and make every trial-extension rule a backend-owned,
      audited policy.
- [ ] Build activation/cohort dashboards for every event in §25.2 and segment by
      industry, acquisition source, device, and failure reason.
- [ ] Meet >=60% qualified signup-to-verified-publish activation, median <=5
      minutes, p90 <=10 minutes, and measure day-1/day-7/week-4 retention.

Research baseline:

- [Amplitude 2025 Product Benchmark Report](https://amplitude.com/resources/product-benchmark-report)

### 25.7 Workstream D — Real Channels: 3/10 → 10/10

Owner outcome: Havi reports only what the external platform actually accepted.

All publisher/reply adapters must implement:

- OAuth and reconnect;
- account/Page/location/channel selection;
- capability and permission detection;
- media and metadata eligibility before approval;
- idempotency and external correlation ID;
- documented rate-limit behavior and bounded retry with jitter;
- platform-confirmed external ID/permalink;
- `PENDING_RECONCILIATION` for ambiguous timeout outcomes;
- reconciliation, dead-letter, and actionable owner guidance;
- token revocation, disconnect, and data deletion;
- contract, integration, failure-injection, and live smoke tests.

Execution order:

1. [ ] **Facebook Page** — finish Multi-Page Picker, permission inspection,
       verified publishing, permalink capture, token refresh/reconnect, and one
       real Page smoke test before each beta wave.
2. [ ] **Facebook Messenger** — persist sender PSID, respect the messaging
       window, separate messages from comments, and mark `SENT` only after Graph
       API confirmation.
3. [ ] **Instagram Business** — build only through supported Meta APIs and the
       approved Facebook/Instagram asset relationship; repeat the same truth and
       reconciliation contract.
4. [ ] **Google Business Profile** — obtain project approval, enable required
       APIs, list real accounts/locations, let the owner choose a location, and
       use `validateOnly` where supported; never derive a location ID from Google
       userinfo.
5. [ ] **YouTube** — complete OAuth/upload contract and audit; unverified-project
       uploads remain private and must not be sold as public auto-publishing.
6. [ ] **TikTok** — implement Direct Post creator-info, privacy, metadata, consent,
       status polling, verified-domain media, `video.publish`, and audit; use an
       honest inbox/export flow until direct public posting is approved.
7. [ ] Keep Zalo deferred until business/legal prerequisites justify reopening
       the scope.

Platform references:

- [Google Business Profile basic setup](https://developers.google.com/my-business/content/basic-setup)
- [TikTok Direct Post setup](https://developers.tiktok.com/docs/en/content-posting-api-get-started)
- [TikTok Content Sharing Guidelines](https://developers.tiktok.com/docs/en/content-sharing-guidelines)
- [YouTube `videos.insert`](https://developers.google.com/youtube/v3/docs/videos/insert)
- [Meta Messenger Platform API reference](https://www.postman.com/meta/messenger-platform-api/documentation/iyp204x/messenger-platform-api)

### 25.8 Workstream E — Revenue Protection: 1/10 → 10/10

Owner outcome: payment state is correct, explainable, and cannot be activated by
a client claim.

Required state machine:

```text
CHECKOUT_CREATED → PENDING → WEBHOOK_VERIFIED → PAID → SUBSCRIPTION_ACTIVE
```

- [ ] Delete or hard local-gate the direct production plan-mutation path.
- [ ] Delete checkout-error fallback and manual-transfer-confirmation calls that
      activate a plan from the frontend.
- [ ] Make PayOS client ID, API key, checksum key, webhook URL, and public return/
      cancel URLs required non-local configuration.
- [ ] Verify every PayOS webhook signature in constant time and reject missing or
      invalid signatures; do the same for any generic provider-specific webhook.
- [ ] Match exact invoice ID/order code, workspace, expected amount, VND currency,
      success status, payment-link ID, and unique gateway reference.
- [ ] Lock invoice/subscription rows and update invoice, payment record,
      entitlement, and audit event atomically.
- [ ] Treat redelivery as idempotent; prevent a replay from adding another paid
      period; retain evidence of rejected mismatches without leaking secrets.
- [ ] Add provider status reconciliation, timeout handling, refund/cancel/dunning,
      daily ledger reconciliation, and founder-visible discrepancy alerts.
- [ ] Implement server-side entitlement policy and tests for every plan feature,
      channel, post/video allowance, lead automation, location, member, and
      branch limit.
- [ ] Test real low-value payments end to end: success, cancel, invalid/missing
      signature, wrong amount, wrong currency, unknown invoice, duplicate
      gateway reference, replay, delayed webhook, timeout, and reconciliation.
- [ ] Adopt OWASP ASVS 5.0 Level 2 as the public-launch application security
      baseline and record each applicable control with test/evidence links.

Payment/security references:

- [PayOS webhook schema](https://payos.vn/docs/du-lieu-tra-ve/webhook/)
- [PayOS webhook verification](https://payos.vn/docs/sdks/back-end/node/)
- [PayOS production-only test guidance](https://payos.vn/docs/moi-truong-test/)
- [OWASP ASVS 5.0](https://github.com/OWASP/ASVS)

### 25.9 Workstream F — Production Operations: 2/10 → 10/10

Owner outcome: a failure is detected, contained, explained, and recovered before
it silently loses posts, replies, payments, or customer data.

- [ ] Make production configuration boot with real providers and fail fast on
      every missing/placeholder secret, URL, origin, provider, or encryption key.
- [ ] Remove host exposure for PostgreSQL, Redis, MinIO API/console; use internal
      networks and explicit firewall rules.
- [ ] Replace anonymous media bucket/wildcard CORS with private source assets,
      signed access, narrow origins, and a deliberate public-derivative policy.
- [ ] Pin immutable container versions; run migrations as one controlled release
      job; add rolling deployment, rollback, and forward-only repair procedures.
- [ ] Add liveness, dependency readiness, and startup checks for API, database,
      Redis, object storage, worker queue, scheduler, and required external
      credentials.
- [ ] Replace logging-only operational alerts with a real alert adapter and
      routing for API error/latency, queue depth, dead letters, OAuth refresh,
      invalid payment webhooks, payment mismatches, LLM spend/latency, backup
      age, and SLO burn rate.
- [ ] Add metrics, traces, correlation IDs, safe structured logs, dashboards,
      synthetic golden-journey checks, and automated log-redaction tests.
- [ ] Rehearse PostgreSQL and object-storage restore monthly and after material
      infrastructure changes; prove RPO <=24 hours and RTO <=2 hours.
- [ ] Create incident severity, owner, communication, rollback, and blameless
      postmortem procedures; P1 MTTR target is <30 minutes.
- [ ] Adopt user-journey SLOs and stop feature releases when the error budget is
      exhausted.

Initial SLOs:

| User journey | Objective |
|---|---:|
| Login and core API availability | >=99.9% |
| Draft generation | >=99% complete within 30 seconds |
| Valid scheduled publish dispatch | >=99% within ±2 minutes |
| Verified payment webhook processing | >=99.9% within 10 seconds |
| False publish/reply/payment success | 0 |
| P1 mean time to recovery | <30 minutes |
| Backup recovery point | <=24 hours |
| Restore time | <=2 hours |

Reliability reference:

- [Google SRE Service Level Objectives](https://sre.google/sre-book/service-level-objectives/)
- [Google SRE Error Budgets](https://sre.google/sre-book/embracing-risk/)

### 25.10 Phased Execution and Release Gates

#### Phase 0 — Trust Foundation (target weeks 1–2)

- [ ] Close Gate I revenue-integrity defects.
- [ ] Close Gate F production boot, secret, network, and media defects.
- [ ] Fix reply/publish truth-state defects and the TikTok media-eligibility
      approval/publish contract.
- [ ] Achieve 100% backend and web unit/integration pass.
- [ ] Achieve reviewed visual/accessibility pass on all covered desktop/mobile
      routes; add Billing and Video Studio.

Exit gate: no unpaid activation, no false success, production config validates,
and every required automated check is green.

#### Phase 1 — Facebook Cash-Flow Loop (target weeks 3–5)

- [ ] Business Truth Pack and honest onboarding.
- [ ] Milestone #11 Multi-Page Picker.
- [ ] One-photo/voice → one-draft mobile flow.
- [ ] Verified Facebook publish with permalink.
- [ ] Messenger reply with sender PSID and delivered state.
- [ ] Activation and verified-outcome event pipeline.

Exit gate: Nhật Minh completes the golden journey without database/manual state
editing; median first verified value <=5 minutes across five fresh test accounts.

#### Phase 2 — Product Excellence and Entitlements (target weeks 6–8)

- [ ] Progressive-disclosure Content Studio and WCAG/Core Web Vitals work.
- [ ] Three usability rounds and >=90% unassisted task completion.
- [ ] Server-side plan entitlements and consistent pricing/quota/trial copy.
- [ ] Outcome and proof-of-value reports from real data.

Exit gate: UI and activation scorecard thresholds pass on target mobile devices.

#### Phase 3 — External Channel Approval (parallel target weeks 6–10+)

- [ ] Submit/complete Meta permissions and business verification.
- [ ] Submit/complete Google Business Profile access and location workflow.
- [ ] Submit/complete YouTube audit.
- [ ] Submit/complete TikTok Direct Post audit.
- [ ] Maintain an evidence folder with reviewer steps, screencasts, test assets,
      permissions, privacy/deletion URLs, and exact approved capability.

Exit gate per channel: external approval plus live smoke, failure, reconnect,
reconciliation, and deletion evidence. Approval timing is external and cannot be
represented as an engineering completion date.

#### Phase 4 — Customer Zero and Paid Pilot (target weeks 9–12+)

- [ ] Seven consecutive days of Nhật Minh dogfooding.
- [ ] Five to ten supervised design partners.
- [ ] Real PayOS low-value transactions and daily reconciliation.
- [ ] Alerts, incident drill, rollback, and restore rehearsal.
- [ ] Four-week cohort measurement for activation, weekly use, outcomes, support
      load, conversion, margin, and month-one renewal.

Exit gate: all §25.3 thresholds hold for 30 consecutive days; no open P0/P1
release blocker; founder signs the public-launch checklist.

#### Gate 10 — Public Paid Launch

All boxes are mandatory:

- [ ] 100% required automated tests pass on the release candidate.
- [ ] Zero known critical/high payment, tenant-isolation, secret, OAuth, publish,
      reply, or data-loss defect.
- [ ] Zero false-success event during the 30-day pilot.
- [ ] Production SLO/error budget, alert, backup, restore, rollback, and incident
      evidence is current.
- [ ] At least 5 real paying pilots and >=80% measured month-one renewal.
- [ ] >=60% qualified signup-to-verified-publish activation; median <=5 minutes.
- [ ] Every advertised channel has the exact required external approval and live
      evidence; all others are hidden or truthfully labeled Beta/export-only.
- [ ] Pricing, plan entitlements, invoice amounts, landing copy, dashboard copy,
      and in-app billing are consistent.
- [ ] Privacy, terms, deletion, consent, support, and incident communication are
      available on the production domain.
- [ ] Founder approval is recorded after Customer Zero review. Commit and push
      remain explicit user-controlled actions.

### 25.11 Resourcing and Sequencing Constraints

Planning estimate, not a launch promise:

- three strong engineers plus product/design: roughly 10–14 weeks for the work
  Havi controls;
- one founder-engineer using AI assistance: roughly 16–24 weeks;
- Meta/Google/TikTok/YouTube review time is external and may exceed either plan.

Do not parallelize feature breadth ahead of trust. Phase 0 is strictly first;
platform submissions may start immediately, but a channel cannot enter paid
scope until its own approval and evidence gate passes.
