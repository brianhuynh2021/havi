# 7-Day Founder Dogfooding Plan & Operational Runbook

## 1. Overview & Objectives

This runbook guides the founder through a 7-day internal testing period (dogfooding) for Havi before launching the closed pilot/beta cohort.

### Primary Goals
1. Validate the core value loop end-to-end: **Signup -> Onboarding -> Raw Input -> AI Generation -> Approval -> Scheduled Publish -> Facebook Page -> Report**.
2. Verify system safety, token encryption, tenant isolation, and automated retry mechanisms under daily operational usage.
3. Establish baseline operational metrics: LLM token usage cost, API response latencies, and publish failure rates.

---

## 2. Pre-Requisites & Environment Setup

Before starting Day 1:

- [ ] Backend stack running with worker & beat:
  ```bash
  npm run infra:up
  cd apps/backend && uv run uvicorn api.main:app --reload
  cd apps/backend && uv run celery -A worker.celery_app:celery_app worker -Q havi.default,havi.content,havi.publish,havi.video_publish --loglevel=info
  cd apps/backend && uv run celery -A scheduler.beat:celery_app beat --loglevel=info
  ```
- [ ] Web frontend running:
  ```bash
  npm run dev:web
  ```
- [ ] Test Facebook Page available with valid Admin permissions for OAuth connection testing.
- [ ] S3/MinIO bucket configured for media asset storage.

---

## 3. 7-Day Action Checklist

### Day 1: Onboarding, Brand Profile & Platform Connection
- [ ] **Task 1.1**: Register a test founder account via `/signup` and complete onboarding (`/onboarding`).
- [ ] **Task 1.2**: Configure Workspace Name, Brand Tone, and Banned Claims in Settings (`/app/settings`).
- [ ] **Task 1.3**: Connect a test Facebook Page via OAuth connection flow.
- [ ] **Verification**: Confirm encrypted access tokens are stored in `platform_connections` table and NEVER exposed in API responses or browser local storage.

### Day 2: Raw Input Capture & Media Processing
- [ ] **Task 2.1**: Upload photo raw input in Content Creation screen (`/app/content`).
- [ ] **Task 2.2**: Verify upload progress bar, cancel flow (`AbortController`), and image preview functionality.
- [ ] **Task 2.3**: Upload multi-file inputs and verify direct-to-object-storage upload contract (images bypass backend API body parsing).
- [ ] **Verification**: Inspect object storage bucket to ensure uploaded files exist at generated key paths.

### Day 3: Multi-Channel Content Generation & Draft Inspection
- [ ] **Task 3.1**: Trigger AI content generation from raw inputs.
- [ ] **Task 3.2**: Inspect generated channel-specific drafts (Facebook Page post, short copy).
- [ ] **Task 3.3**: Verify tone matching and strict enforcement of Banned Claims filter (e.g., claims like "cam kết 100%" should be blocked or flagged).
- [ ] **Verification**: Check database `content_jobs` state is `completed` and `content_items` are created in `draft` status.

### Day 4: Draft Editing, Versioning & Approvals
- [ ] **Task 4.1**: Edit a draft's text in Content Creation UI.
- [ ] **Task 4.2**: Verify version history tracking (`content_item_versions`) to ensure past revisions are preserved.
- [ ] **Task 4.3**: Approve drafts individually and via bulk approval.
- [ ] **Verification**: Confirm approved items transition to `approved` / `scheduled` state with `approved_by` and `approved_at` audit fields set.

### Day 5: Calendar Scheduling & Rescheduling
- [ ] **Task 5.1**: View scheduled posts on Calendar screen (`/app/calendar`).
- [ ] **Task 5.2**: Test rescheduling a post to a different date/time slot.
- [ ] **Task 5.3**: Verify Asia/Ho_Chi_Minh timezone handling across calendar views and scheduled Celery jobs.
- [ ] **Verification**: Ensure Celery beat picks up scheduled jobs at the exact target time.

### Day 6: Live Facebook Page Publishing & Failure Recovery
- [ ] **Task 6.1**: Allow Celery worker to execute live publication for an approved scheduled post.
- [ ] **Task 6.2**: Verify post is visible on the live Facebook Page with correct text and image layout.
- [ ] **Task 6.3**: Simulate a network failure or connection expiry to test failure handling, status transition to `failed`, and manual/automatic retry from Failed Posts panel.
- [ ] **Verification**: Check `publish_jobs` table for idempotency keys, execution logs, and published status.

### Day 7: Analytics, Operations & Deletion Safety Audit
- [ ] **Task 7.1**: Review verified publishing and conversation outcomes on `/app/reports`.
- [ ] **Task 7.2**: Inspect Internal Operations metrics at `/app/internal/operations` (content-generation P95, slow-job count, token usage, provider breakdown, and dead-letter count).
- [ ] **Task 7.3**: Test Workspace Deletion & Account Deletion in Settings (`/app/settings`) Danger Zone.
- [ ] **Verification**: Confirm deletion cascades to content/connections and anonymizes audit logs (`workspace_id=NULL`).

---

## 4. Daily Telemetry & Operational Metrics Log Template

Copy and fill this log template daily during the 7-day dogfooding phase:

| Date | Active Workspaces | Content Jobs Created | Posts Published | Publish Success Rate (%) | Total LLM Tokens Used | Estimated LLM Cost ($) | Avg Gen Latency (s) | Active Incidents / Issues |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Day 1** | | | | | | | | |
| **Day 2** | | | | | | | | |
| **Day 3** | | | | | | | | |
| **Day 4** | | | | | | | | |
| **Day 5** | | | | | | | | |
| **Day 6** | | | | | | | | |
| **Day 7** | | | | | | | | |

---

## 5. Incident Triage Matrix & SLAs

| Priority Level | Description & Examples | SLA Response Time | Action Required |
| :--- | :--- | :--- | :--- |
| **P0 (Critical)** | - Duplicate post published to social platform.<br>- Secrets, API keys, or raw tokens written to logs.<br>- Tenant data cross-leakage (User A sees User B data).<br>- Total system outage or 100% publish failure rate. | **< 1 hour** | **Stop publishing immediately.** Revert build, revoke compromised tokens, and run database sanity check. |
| **P1 (High)** | - Content generation latency > 20 seconds.<br>- Upload failure without a clear per-file error and retry action.<br>- Calendar timezone display offset.<br>- Facebook Page permission revoked without marking the connection unhealthy and offering reconnect. | **< 12 hours** | Log the incident, preserve the user's input, apply a scoped hotfix or retry/reconnect path, and update test coverage. |
| **P2 (Medium)** | - Minor UI visual alignment bug.<br>- Non-blocking copy suggestion improvement.<br>- Optional feature request. | **< 3 days** | Add to backlog priority queue. |

---

## 6. Immediate Stop Rules (Kill Switches)

Dogfooding and beta publishing **MUST STOP IMMEDIATELY** if any of the following triggers occur:

1. **Duplicate Publish Trigger**: A publish job fires twice for the same content item resulting in multiple posts on a social channel.
2. **Credential Leak Trigger**: An API key, JWT secret, or OAuth access token appears in plain text in stdout logs, error responses, or frontend bundles.
3. **Tenant Breach Trigger**: Database query returns data belonging to a different `workspace_id`.
4. **Mass Platform Rejection Trigger**: Facebook API returns consecutive permission or policy violation errors (indicates OAuth scope or app review issue).
