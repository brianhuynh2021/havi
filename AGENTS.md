# Havi — Development Guidelines

## What we are building

> **Havi — Nền tảng quản trị và vận hành mạng xã hội** dành cho doanh nghiệp và
> đội ngũ social. Quản lý kênh, nội dung, lịch đăng, hội thoại và thành viên tại
> một nơi.

Havi administers **the customer's social system**. It does not administer the
customer's business goals. That distinction is the whole scope.

Nine things, and nothing else is the product:

1. Accounts and social connections
2. Media and content library
3. Publishing calendar and publish status
4. Inbox, comments, conversations
5. Members, roles, permissions
6. The draft → approve → publish workflow
7. Activity history and audit log
8. Connection health, errors, alerts
9. Multi-channel operations reporting

**Long-term vision:** the trusted control plane for business social media
operations — Havi sits between the organisation and every platform, holding the
governance layer above them. Full 5–10 year picture in
[ROADMAP §1b](docs/product/ROADMAP.md).

**The test every feature must pass:**

> Does it help the business control social better, reduce steps, or reduce the
> risk of missing something?

If it cannot answer that, it does not belong in Havi — however good it is. A
feature that serves none of the nine domains needs its own product decision
before any code is written.

## Retired concepts — do not reintroduce

Each of these shipped, then was removed. They are listed by name so a future
proposal that smells like one is recognisable:

* **Universal Goal-to-Roadmap Execution OS** — and the whole
  `Goal → Roadmap → Evidence → Review` loop.
* **"🚀 Đẩy khách đến" / 1-Click In-App Ad Booster** — direct paid execution via
  Meta Marketing API and TikTok Spark Ads. Forbidden names: *Havi Ads*, *AI Ads*,
  *One-click Ads*, *Chạy quảng cáo bằng Havi*, *Tự động đẩy khách*.
* **Weekly Guided Progress**, **Weekly Social Operations Completed**, and every
  other user-facing North Star. A management platform does not hand its users a
  number to chase.
* **Verified Visits** as a headline metric.
* **"AI nhân viên marketing"** and any growth/traffic/revenue promise.
* **Onboarding that asks the user to set a goal.**
* **Dashboard showing "goal progress".**
* **Coach recommending a growth roadmap.**

The cost of these was concrete: ~8,000 lines of video-rendering code written and
deleted; a goal engine with four tables and three screens that never entered the
main navigation; a shipped build that was broken because two live screens linked
to a route removed with the rendering code.

**The rule:** describe what the software does, not what the business hopes it
becomes. Engineering builds toward the description.

If the word **"chiến dịch"** appears, it means *a group of content organised
together* — never a commitment to produce a business result.

## Boundaries

* **Nothing publishes without human approval.** The draft → approve → publish
  workflow is a constraint, not a preference.
* **No video editing.** Users are faster in CapCut. Havi takes the finished clip.
* **No goals, roadmaps, or evidence tracking.**
* **No ad execution — ever.** Havi may *guide* a user to a platform's Ads
  Manager, prepare the post data, and track results **read-only**. It must never
  create a campaign, set a budget, start or stop an ad, hold ad money, or pay a
  platform. Small upside, wildly asymmetric downside: one idempotency bug there
  spends the customer's real money, and any failure gets blamed on Havi
  regardless of cause. Boundary and naming rules in
  [ROADMAP §1c](docs/product/ROADMAP.md).
* **Never browser-automate a third-party platform.** It breaks silently,
  violates terms, and makes Havi the actor in a spend it cannot account for.
* **No promise of customers, revenue, or growth.**

## AI is a utility, not the positioning

AI may: suggest captions, adapt content per platform, summarise conversations,
classify inbox items, detect duplicate content, flag anomalies, and draft replies
for a human to approve.

AI may not: set goals, promise marketing outcomes, or decide on the business's
behalf.

## Metrics

Havi ships **no user-facing North Star**. Operations tracks internal health only:
publish success rate, active connections, sync latency, failed posts, content
awaiting approval, unhandled conversations, error resolution time, retention,
paying workspaces. Telemetry — not product philosophy.

## Engineering standards

* **Clean / Hexagonal DDD.** Entrypoints depend on application services; services
  depend on domain and ports; adapters implement ports. Business rules live in
  the domain, never in a router or a React component.
* **Tests before release.** A feature ships only when real integration/unit tests
  cover it and pass.
* **Truthful states above all.** The most expensive bugs here were never crashes
  — they were silent lies: a fake publisher reporting posts that never existed, a
  mock renderer marking jobs complete, a notifier logging "sent successfully"
  while sending nothing, a report showing "~1 giờ tiết kiệm" with
  zero data. Any path that can report success without proof is a defect, even
  with every test green.
* **Local-only fakes stay local.** Mock LLM, fake publisher, disabled rate limits,
  and dev-simulate endpoints are blocked outside `HAVI_ENV=local` by config
  validators, not by convention.
* **Fail closed.** When a flag is missing or a value is unrecognised, choose the
  option that does nothing. Auto-reply defaulted to "approved" when the field was
  absent; that could send invented opening hours to a real customer.
* **Idempotency at the database.** Duplicate prevention belongs in Postgres
  constraints, not in an `if` inside a service. Two workers will race.
* **Comments explain why**, especially why an obvious-looking alternative is wrong.

**Channel priority:** Facebook (Page, Reels, Messenger) done properly before any
second channel → YouTube Shorts and TikTok, whichever provider audit clears
first → Google Business Profile. Email is decided separately, not queued as a
channel. Zalo OA deferred.

## Working agreements

* **Never `git commit` or `git push` without an explicit request.**
* **UI copy is Vietnamese, documentation is English.**
* **Address users neutrally** — not "chị". The exception is text the business
  sends to *its own* customers, where the business's voice applies.

## Brand

**Havi** = **Ha**rry (the founder's son) + **Vi**etnam.
