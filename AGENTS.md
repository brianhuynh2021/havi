# Havi — Development Guidelines

## What we are building

> **Havi — Trợ lý vận hành social có kiểm soát** dành cho doanh nghiệp và
> đội ngũ social.

**What Havi is, what it ships, and the nine things that are the product are
defined once in [PRODUCT_CONTRACT.md](docs/product/PRODUCT_CONTRACT.md).**
Read it before proposing a feature. Do not restate its scope list here — a
second copy is a second thing to forget to update.

Havi today is a **control plane for social operations with AI-assisted
drafting**: it gathers work that needs attention, prepares safe next steps,
enforces human approval, and records provider-verified outcomes.

**Product Philosophy:** *Don't make users manage Havi. Let Havi manage social for them.*

**Long-term vision (NOT shipped):** an AI Secretary that observes, prioritizes,
recommends and acts on approval, backed by Business Memory. This is direction,
not current capability — see [ROADMAP §1b](docs/product/ROADMAP.md). Never
describe it in the present tense, in code comments or in customer-facing copy.

**The test every feature must pass:**

> "Hôm nay Havi đã lấy được việc gì khỏi đầu của CEO?" (What task/worry did Havi remove from the CEO's mind today?)
> Does it help the business control social better, reduce steps, or reduce the risk of missing something?

If it cannot answer that, it does not belong in Havi — however good it is.

## Retired concepts — do not reintroduce

Each of these shipped, then was removed. They are listed by name so a future proposal that smells like one is recognisable:

* **Universal Goal-to-Roadmap Execution OS** — and the whole `Goal → Roadmap → Evidence → Review` loop.
* **"🚀 Đẩy khách đến" / 1-Click In-App Ad Booster** — direct paid execution via Meta Marketing API and TikTok Spark Ads. Forbidden names: *Havi Ads*, *AI Ads*, *One-click Ads*, *Chạy quảng cáo bằng Havi*, *Tự động đẩy khách*.
* **Verified Visits** as a headline metric.
* **"AI nhân viên marketing"** and any growth/traffic/revenue promise.
* **Onboarding that asks the user to set a goal.**
* **Dashboard showing "goal progress".**
* **Coach recommending a growth roadmap.**

The cost of these was concrete: ~8,000 lines of video-rendering code written and deleted; a goal engine with four tables and three screens that never entered the main navigation.

**The rule:** describe what the software does, not what the business hopes it becomes. Engineering builds toward the description.

If the word **"chiến dịch"** appears, it means *a group of content organised together* — never a commitment to produce a business result.

## Boundaries

* **Nothing publishes without human approval.** The draft → approve → publish workflow is a constraint, not a preference.
* **No video editing.** Users are faster in CapCut. Havi takes the finished clip.
* **No goals, roadmaps, or evidence tracking.**
* **No ad execution — ever.** Havi may *guide* a user to a platform's Ads Manager, prepare the post data, and track results **read-only**. It must never create a campaign, set a budget, start or stop an ad, hold ad money, or pay a platform.
* **Never browser-automate a third-party platform.** It breaks silently, violates terms, and makes Havi the actor in a spend it cannot account for.
* **No promise of customers, revenue, or growth.**

## AI Secretary Positioning & Business Memory — FUTURE, NOT SHIPPED

The target loop is **Observe → Prioritize → Recommend → Act**, with Havi
watching everything, filtering noise, and handling actions upon approval.

**Business Memory** — learning what is "normal" for each brand (20 comments/hour
is routine for Brand A, a viral alert for Brand B) — is the intended competitive
moat.

**Neither ships today.** Current behaviour: drafting is AI-assisted; the work
queue, brief and inbox triage are deterministic rules over data Havi owns
(`domain/policies/`), which is why they can be audited and tested. Anomaly
detection and learned baselines do not exist.

When building toward this, the constraint holds: prompt context stays
inspectable, and no rule inferred from user behaviour is applied silently.

## Metrics

Havi ships **ONE** core user-facing North Star: **Time Havi Saved**.
This replaces raw counts or vanity metrics. The home screen should highlight: *"Havi saved you 7h 18m this week."*

Time Saved must show the counted actions and the per-action assumption on
screen; a total without its arithmetic is advertising, not a metric.

Future triage metrics (blocked on the capability above, do not report yet):
% tasks handled by Havi, issues detected before the user checked, anomalies
surfaced.

Operations also tracks internal health: publish success rate, active connections, sync latency, failed posts, content awaiting approval, unhandled conversations, error resolution time, retention, paying workspaces.

## Engineering standards

* **Layered architecture with DI.** Entrypoints depend on application services;
  services depend on repositories and on ports for outbound integrations;
  adapters implement those ports. Business rules live in `domain/policies/`,
  never in a router or a React component.

  Be accurate about what this is, because an inflated claim misleads reviewers
  and new contributors. Ports (`domain/ports/`) exist **only** for the six
  outbound integrations: LLM, publisher, reply publisher, media, email, voice.
  There is **no repository port** — application services import concrete
  classes from `adapters/persistence/`, and `domain/models/` are SQLAlchemy
  models. That is a deliberate, workable trade-off, not hexagonal architecture.
  Do not describe it as such.
* **Tests before release.** A feature ships only when real integration/unit tests cover it and pass.
* **Truthful states above all.** The most expensive bugs here were never crashes — they were silent lies. Any path that can report success without proof is a defect, even with every test green.
* **Local-only fakes stay local.** Mock LLM, fake publisher, disabled rate limits, and dev-simulate endpoints are blocked outside `HAVI_ENV=local` by config validators, not by convention.
* **Fail closed.** When a flag is missing or a value is unrecognised, choose the option that does nothing.
* **Idempotency at the database.** Duplicate prevention belongs in Postgres constraints, not in an `if` inside a service. Two workers will race.
* **Comments explain why**, especially why an obvious-looking alternative is wrong.

**Channel priority:** Facebook (Page, Reels, Messenger) done properly before any second channel → TikTok → YouTube Shorts → Google Business Profile. Email is decided separately, not queued as a channel. Zalo OA deferred. Provider audits are applied for in parallel, ahead of their implementation slot.

## Working agreements

* **Never `git commit` or `git push` without an explicit request.**
* **UI copy is Vietnamese, documentation is English.**
* **Address users neutrally** — not "chị". The exception is text the business sends to *its own* customers, where the business's voice applies.

## Brand

**Havi** = **Ha**rry (the founder's son) + **Vi**etnam.
