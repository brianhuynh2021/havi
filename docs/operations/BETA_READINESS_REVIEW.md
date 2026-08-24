# Beta Readiness Review — Paid Beta Gate (2026-08-24)

> Documentation language: English, per ROADMAP §1 convention. Vietnamese is kept
> only where it quotes real product or sales copy.
>
> **Method:** audited against the working tree on 2026-08-24 and verified by
> *running* the suites, not by reading status claims in docs. Every finding below
> cites `file:line`. Grades reflect what a paying customer can complete end to
> end, not what code exists.
>
> **Verdict:** commercial infrastructure (payments, security, channels) is close
> to ready. The behavioral loop Havi actually sells is not reachable by a
> customer. Do not open paid signup broadly. Charge 3–5 supervised pilots first.

---

## 1. Verified State of the Tree

| Check | Command | Actual result | What docs claimed |
|---|---|---|---|
| Web lint | `npm run lint:web` | PASS (exit 0) | matches |
| Backend lint | `uv run ruff check .` | PASS (exit 0) | matches |
| Backend tests | `uv run pytest` | **509 passed, 2 failed** (25.9s) | ROADMAP §26.11: "501/501 PASSED" |
| Web tests | `npm run test:web` | 179 passed, 32 files | ROADMAP: 173–175 |
| Working tree | `git status` | **100 files uncommitted** (+3547 / −797) | — |
| Browser E2E | `apps/web/e2e/` | only `visual-a11y.spec.ts` — **no functional browser E2E on the money or goal loop** | — |

Failing tests:

1. `tests/test_content_flow.py::test_upload_rendered_video_binary` — real runtime bug, see P0-1.
2. `tests/test_scheduler_wiring.py::TestBeatSchedule::test_task_chua_lam_khong_nam_trong_lich` — **passes in isolation (8 passed), fails in the full suite** → order-dependent test, see P1-1.

---

## 2. Multi-Criteria Scorecard

| Criterion | Score | Evidence |
|---|---|---|
| Behavioral idea — as designed | **8.5** | `Goal→Roadmap→Next Action→Evidence→Review→Replan` is anchored in Locke & Latham, Gollwitzer & Sheeran, choice-overload, Kluger & DeNisi. The §26.3 "no revenue guarantee" contract is a real asset. |
| Behavioral idea — as implemented | **4.5** | Roadmap engine is 4 `if/elif` template branches; Coach is client-side keyword matching; Evidence and Reports screens have no inbound link. |
| Architecture & code | **8.0** | Clean ports/adapters, pure domain policies, idempotent publish with dead-letter, one shared publisher adapter map for API retry and scheduler. |
| Test quality | **7.0** | 688 tests is real coverage, but one runtime bug escaped, one test is order-dependent, and zero browser E2E covers the paid path. |
| Security | **8.5** | Strong production config guard (`apps/backend/core/config.py:226`), login rate limit 10/5min, Fernet token encryption, HMAC webhooks, `.env` untracked. |
| Revenue integrity | **5.0** | Main money path is correct, but a customer can pay and not get activated (P0-2), and an expired workspace keeps most paid features (P0-3). |
| Production operations | **5.5** | Prod compose + nginx + 4 healthchecks exist, but **no error monitoring (no Sentry)**, alerts are `LoggingAlertSink` only, and **no automated backup job** in `docker-compose.prod.yml`. |
| Unit economics | **3.0** | Only token counts exist. `grep 'cost_vnd\|cost_usd'` returns zero hits — cost per workspace per month is unknown. |
| Activation measurement | **4.0** | Missing `goal_created`, `roadmap_accepted`, `evidence_attached` events → the two thresholds ROADMAP §26.13 sets as the gate for charging **cannot be computed**. |
| Product truthfulness | **6.0** | Landing copy is clean, but unverified numbers moved into the product core (§3.5). |

---

## 3. Behavioral Review

### 3.1 What holds up — keep it

- Selling **"hết mù mờ bước tiếp theo"** instead of "AI writes posts" is the
  correct and more defensible positioning against ChatGPT wrappers.
- `done_rule` + `fallback_action` + `why_this_is_next` on every task is a real
  implementation-intention structure. This is what a generic chatbot lacks.
- `owner_type` (Havi does / you do / together) matches NIST AI RMF oversight.
- Weekly review discusses behavior and evidence instead of scoring the person —
  avoiding the one-third-of-feedback-hurts-performance trap.

### 3.2 The roadmap is a form letter, not a roadmap

`apps/backend/application/services/roadmap_service.py:347` has exactly four
branches: `ACQUIRE_CUSTOMERS|LAUNCH`, `RECRUIT|GROW_AUDIENCE`,
`SELL_OFFER|DELIVER_PROJECT`, and `else`. A spa, a salon, a cafe, a training
center, and a real-estate broker all fall into branch 1 and receive **the same
task sequence and the same 90/30/7 horizons**, differing only by `goal.title`
interpolated into an f-string. `confidence_score=0.88` is hardcoded at line 52.

There is no LLM anywhere in roadmap generation, so the customer's real
constraints (3M budget, working alone, cannot shoot video) **do not affect the
plan at all** — which is the exact pain ROADMAP §26.2 promises to solve.

Behavioral consequence: retention dies in week 2, and it dies fastest the moment
two customers in the same local group compare their plans.

### 3.3 "AI Coach" contains no AI

`apps/web/src/features/coach/coach-screen.tsx:44` is
`if (text.includes("kẹt")) … else if (text.includes("video")) …`, entirely
client-side. There is no backend coach endpoint (`grep coach api/routers/` is
empty). The "AI Lead Agent" is likewise regex-based:
`apps/backend/application/services/ai_lead_agent_service.py:34` calls
`classify_lead_intent`, a 122-line policy in `domain/policies/ai_lead_intent.py`.

Deterministic logic is a legitimate engineering choice — cheap and it cannot
hallucinate. The defect is the **label**. Calling it "AI Coach" on a screen a
paying customer sees is the exact class of claim §26.3 forbids.

### 3.4 The evidence loop — the thing being sold — is unreachable

Every in-app `href` in the codebase:

```
/app/content(5)  /app(5)  /app/video-studio(3)  /app/settings(3)  /app/roadmap(2)
/app/inbox(2)    /app/calendar(2)  /app/leads(1)  /app/connections(1)  /app/billing(1)
```

There is **no link to `/app/coach`, `/app/evidence`, or `/app/reports`**. All
three screens exist with tests, none appear in
`apps/web/src/components/app-shell/nav-items.ts` (6 items), and nothing links to
them. `/app/reports` is the business-outcome screen — i.e. Gate H "Provable
Outcomes", the gate that blocks paid conversion.

ROADMAP Phase 1 ticks `[x]` for building `/app/evidence` and `/app/coach` as
core surfaces. The code exists; the path to it does not.

### 3.5 Stale roadmap ticks and unverified numbers inside the product

- `apps/web/src/features/onboarding/onboarding-screen.tsx:26` is still
  `["Chọn ngành", "Nối kênh", "Havi bắt đầu học"]` — industry-first. Phase 1
  ticks `[x]` "Replace industry-first onboarding with goal-first intake". Goal
  intake actually lives on the Today screen, after onboarding. **The tick is wrong.**
- `roadmap_service.py:358,374` ships unverified quantitative claims to customers
  inside `why_this_is_next`: *"Video ngắn 9:16 giữ chân người xem cao gấp 4 lần
  hình ảnh tĩnh"*, *"Tốc độ phản hồi < 10s giúp tăng tỷ lệ chốt hẹn gấp 3 lần"*.
  Phase 0 ticks `[x]` "Remove fabricated ROI/funnel numbers" — landing was
  cleaned, but the numbers moved into the product.
- ROADMAP §3.2 is stale: it says inbox `send_reply` "writes DB state only and
  calls no publisher", but `application/services/inbox_service.py:232` already
  calls a real reply publisher.

### 3.6 Contradictory promise between sales script and product

`docs/operations/EXTERNAL_BETA_LAUNCH.md` §5 promises *"Havi tự đăng 1-2 bài/ngày
+ trực inbox"*. `apps/web/src/features/landing/landing.content.ts:203` promises
*"Tuyệt đối KHÔNG [tự đăng]. Bạn duyệt trước, luôn luôn"*. Pick one before
talking to a customer.

---

## 4. P0 Defects — Blocking Any Paid Customer

- [ ] **P0-1 — Runtime 500 in the video flow.**
      `apps/backend/api/routers/content.py:445` assigns
      `asset.status = MediaStatus.READY`, but `core/enums.py:140` defines only
      `PENDING|RAW|USED|ARCHIVED` → `AttributeError`. This is one of the two
      failing tests, and it sits in uncommitted code.
- [ ] **P0-2 — A customer can transfer money and never get activated.**
      `apps/backend/adapters/payment/payos_gateway.py:129`: if the PayOS SDK
      throws (network, bad key, rate limit) it logs and **falls back to a static
      VietQR pointing at a hardcoded personal account
      (`0984883750 / NGUYEN THANH HUYNH`)**. PayOS never sees that transfer → no
      webhook → the invoice stays `PENDING` forever → the customer paid and got
      nothing, silently. Production must **fail closed** (surface an error, do
      not render a QR), never fail open.
- [ ] **P0-3 — An expired workspace keeps most of the product.**
      `sub_state.is_active` is checked in exactly one place:
      `application/services/content_service.py:100` (content job creation). It is
      absent from publish dispatch, video render (CPU-heavy ffmpeg), inbox
      auto-reply, CRM nudge, trend scout (real Gemini call at
      `trend_scout_service.py:281`), and roadmap generation. A `PAST_DUE`
      workspace still publishes on schedule and still burns your LLM budget.
- [ ] **P0-4 — Hot-lead alerts report false success in production.**
      `adapters/outbound/telegram_notifier.py:47`: an empty token defaults to
      `"MOCK_TELEGRAM_BOT_TOKEN"`, logs, and **`return True`**. The production
      guard at `core/config.py:230` requires SMTP/LLM/Facebook/PayOS but **not
      `HAVI_TELEGRAM_BOT_TOKEN`**. The "close the customer in 5 seconds" promise
      can silently never fire while the system reports success — precisely what
      §26.5 forbids ("never display external success from an internal state").
- [ ] **P0-5 — Three dead screens.** Link `/app/reports`, `/app/evidence`, and
      `/app/coach` into navigation, or delete them. See §3.4.
- [ ] **P0-6 — The activation funnel is not measurable.** Emitted `job_kind`
      values include `task.completed`, `task.blocked`, `roadmap.reviewed`,
      `roadmap.restored`. **Missing:** `goal_created`, `roadmap_accepted`,
      `roadmap_edited`, `evidence_attached`, `task_scheduled`. Without these,
      "≥70% accept or meaningfully edit a roadmap" and "median goal → first
      scheduled action ≤10 minutes" (§26.13) cannot be computed — you would be
      selling blind.

## 5. P1 Defects

- [ ] **P1-1 — Order-dependent test.**
      `tests/test_scheduler_wiring.py::test_task_chua_lam_khong_nam_trong_lich`
      passes alone, fails in the full suite; `task.run()` touches state another
      test monkeypatches. Add `pytest-randomly` and run 3 seeds in CI.
- [ ] **P1-2 — No cost instrumentation.** No `cost_vnd`/`cost_usd` anywhere;
      margin on the 189k plan is unknown.
- [ ] **P1-3 — No error monitoring or automated backup.** No Sentry/APM; alerts
      are log-only; `docker-compose.prod.yml` has no backup job (only a `pg_dump`
      instruction in `docs/handoff/DEPLOYMENT.md`).
- [ ] **P1-4 — Price list is inconsistent across three documents.** Code
      (`domain/policies/subscription.py:29`) = 189/369/799k; ROADMAP §26.11 =
      "299k/599k"; `EXTERNAL_BETA_LAUNCH.md` §1 = "299k–599k" but §5 = "189k/369k".
      Settle on one before printing a QR.
- [ ] **P1-5 — 100 uncommitted files** make review and rollback impossible.
- [ ] **P1-6 — Invoice prefix lookup silently picks the newest match.**
      `adapters/persistence/billing_repository.py:58` `find_by_prefix` orders by
      `issued_at desc` and takes `.first()`; it should assert a single match.

---

## 6. Test Protocol to Run Before Beta

### Layer 0–1 — static + unit/integration (every commit)

```bash
npm run lint:web && npm run test:web && npm run build:web
```

```bash
cd apps/backend && uv run ruff check . && uv run pytest -q
```

Gate: zero failures. Reproduce P1-1 by comparing
`uv run pytest tests/test_scheduler_wiring.py` (passes) against the full suite (fails).

### Layer 2 — core E2E (mock LLM, FakePublisher, no paid API calls)

```bash
npm run e2e
```

### Layer 3 — simulated 7-day dogfooding

```bash
cd apps/backend && python ../../scripts/dogfood_suite.py
```

### Layer 4 — browser E2E, MISSING and required

Only `visual-a11y.spec.ts` exists. Four Playwright specs must be written; these
are the precondition for charging money:

- [ ] `signup → onboarding → create goal → generate roadmap → complete task 1 with evidence`,
      asserting time-to-first-action ≤ 10 minutes.
- [ ] `trial expires → every paid feature is blocked → QR shown → signed PayOS webhook → plan activates`
      (covers P0-3).
- [ ] `fanpage price question → inbox → approve reply → real send → lead with phone → Telegram alert on a real device`
      (covers P0-4).
- [ ] `weekly review → choose Improve/Pivot → see diff → accept → roadmap v2 while v1 is preserved`.

### Layer 5 — failure drills on staging (manual, write down the result)

| Scenario | Expected |
|---|---|
| Revoke the Facebook token mid-schedule | job → `AUTH_PERMISSION`, UI says reconnect, **never** reports published |
| PayOS returns 500 at checkout | **surface an error**, no personal-account QR (after P0-2) |
| LLM 429 / quota exhausted | job `FAILED` with a readable reason, quota not consumed |
| Kill the worker 30 min, restart | queued jobs run once, no duplicate publish (idempotency) |
| Kill Postgres 60s | clean 503, no invoice lost |
| Restore from `pg_dump` | restored in < 30 min, `PAID` invoices intact |

### Layer 6 — security and legal

```bash
cd apps/backend && uv run pytest tests/test_security_pentest.py tests/test_production_config.py tests/test_object_storage_security.py tests/test_token_crypto.py -q
```

Plus: manually attempt cross-workspace reads with two accounts; verify
`/privacy`, `/terms`, `/data-deletion` are live over HTTPS before submitting Meta
App Review.

### Layer 7 — real-money test (mandatory, once)

Create a 10,000 VND test plan, scan and transfer from a real phone, and confirm:
signed webhook → invoice `PAID` → `paid_until` +30 days → replaying the same
`reference` is rejected with `DuplicatePaymentReferenceError`.

---

## 7. Paid Beta Plan — 4 Weeks from 2026-08-25

### Week 1 (Aug 25–31) — fix P0, remove ambiguity

- [ ] Fix P0-1 … P0-6.
- [ ] Split the 100 uncommitted files into meaningful commits.
- [ ] Add Evidence and Reports to navigation.
- [ ] Either drop the "AI" label from Coach (e.g. `Hướng dẫn nhanh`) or wire a real LLM behind it.
- [ ] Remove the "gấp 3/4 lần" claims from roadmap templates.
- [ ] Settle one price list across code, ROADMAP, and EXTERNAL_BETA_LAUNCH.
- [ ] Submit Meta App Review using `docs/operations/FACEBOOK_APP_REVIEW.md`.

Gate: pytest + vitest green three runs in a row; Layer 5 drills pass; the
10,000 VND real-money test passes.

### Week 2 (Sep 1–7) — Customer Zero, for real

- [ ] Run production for 7 days with Trung Tâm Nhật Minh, you as the customer.
- [ ] Log daily: time to first action, which tasks got blocked, whether the
      roadmap respected real constraints.

Gate to continue: you voluntarily use all 7 days without editing code, and the
week-1 review produces a meaningful Continue/Improve decision.

This is where §3.2 will surface hardest. If the training-center roadmap reads
like the spa roadmap, stop and generate roadmaps with an LLM constrained by goal
+ budget + time + available assets, keeping the templates as an LLM-failure fallback.

### Week 3 (Sep 8–21) — 3–5 supervised pilots, real money

- [ ] Recruit 3–5 shops you can meet in person for 30 minutes (2 spa/salon,
      1 F&B, 1 real estate, 1 training — the Cohort 1 profile).
- [ ] **Charge 189k up front with a 100% refund inside 14 days.** Do not run a
      silent 7-day free trial and then pop a QR on day 7 — paying up front filters
      for real customers, the refund removes purchase risk, and the day-7 popup
      reads as a trap.
- [ ] Measure (after P0-6): activation, time-to-first-action, weekly guided
      progress, review completion, LLM cost per workspace per month.

Gate to open a wider cohort: ≥3/5 pilots voluntarily pay month 2; no refund
requested for "the AI does not understand my business"; zero wrong-publish or
cross-tenant incident; positive margin at 189k.

### Week 4 (Sep 22–30) — decide

- [ ] Gate met → open 10–20 shops. Gate missed → add only 5 more pilots. Do not
      scale a template roadmap.

### The 10 conditions before accepting the first payment

- [ ] 1. `pytest` and `vitest` fully green.
- [ ] 2. 10k real-money test passes, including the duplicate-reference replay.
- [ ] 3. PayOS failure fails closed — no personal-account QR.
- [ ] 4. Expiry blocks **every** cost-bearing feature.
- [ ] 5. Telegram alert proven to arrive on a real device (no MOCK path).
- [ ] 6. Reports and Evidence screens are reachable.
- [ ] 7. No "AI" label on anything that is `if/else`.
- [ ] 8. No "N times better" claim without a cited source.
- [ ] 9. Sentry + `pg_dump` cron + a rehearsed restore.
- [ ] 10. `cost_vnd` per workspace exists, proving 189k is profitable.

---

## 8. If Only Three Things Get Done

1. **Generate roadmaps from each customer's real constraints** — otherwise
   retention dies in week 2 (§3.2).
2. **Fail closed on PayOS and gate subscription across the whole system** —
   otherwise you lose money and trust (P0-2, P0-3).
3. **Link `/app/reports` and `/app/evidence` into navigation** — otherwise you
   have nothing to show when a customer asks "what did I get?" (§3.4).
