# Havi — Development Guidelines

## What we are building

> **Havi — Trợ lý AI điều hành mạng xã hội** dành cho doanh nghiệp và
> đội ngũ social.

Havi is an **AI Secretary/Chief of Staff** for the customer's social system. Its primary value is not just "managing multiple channels" (which the market already provides), but actively reducing the cognitive load for business owners and teams.

**Product Philosophy:** *Don't make users manage Havi. Let Havi manage social for them.*

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

**Long-term vision:** the trusted control plane and intelligent executive assistant for business social media operations. Havi sits between the organisation and every platform, holding the governance and proactive intelligence layer above them. Full 5–10 year picture in [ROADMAP §1b](docs/product/ROADMAP.md).

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

## AI Secretary Positioning & Business Memory

Havi is highly proactive: **Observe → Prioritize → Recommend → Act**.
It is NOT a passive "Dashboard with a chatbot". Havi must watch everything, filter noise, tell the user what matters, and handle the action upon approval.

**Business Memory:** Havi learns what is "normal" for each brand (e.g., 20 comments/hour might be normal for Brand A, but a viral alert for Brand B). This contextual awareness is the core competitive moat.

## Metrics

Havi ships **ONE** core user-facing North Star: **Time Havi Saved**.
This replaces raw counts or vanity metrics. The home screen should highlight: *"Havi saved you 7h 18m this week."*

It also tracks AI triage metrics:
* % social tasks handled by Havi
* Issues detected before the user checked
* Comments auto-triaged
* Posts published automatically
* Anomalies surfaced
* Hours of reporting eliminated

Operations also tracks internal health: publish success rate, active connections, sync latency, failed posts, content awaiting approval, unhandled conversations, error resolution time, retention, paying workspaces.

## Engineering standards

* **Clean / Hexagonal DDD.** Entrypoints depend on application services; services depend on domain and ports; adapters implement ports. Business rules live in the domain, never in a router or a React component.
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
