# Handoff: Havi Multi-Industry AI Marketing MVP

## Overview

Havi is an AI marketing assistant for non-technical small-business users. The
target users include spas, cafes, restaurants, real-estate brokers, engineers,
specialists, and small online sellers. The product is a closed loop with four
stations:

1. **Raw input capture**: quick photos, voice notes, typed notes, or future
   business-system webhooks.
2. **AI content engine**: detect industry context, process media, and use one LLM
   call to generate several channel-specific drafts.
3. **Distribution hub**: publish approved content through official APIs at local
   golden-hour slots.
4. **Lead and care loop**: listen for opportunities, draft replies for approval,
   run lifecycle CRM nudges, and answer only pre-approved FAQ content.

The product promise is outcome-based. Reports should focus on price inquiries,
visits, returning customers, and published-post reliability rather than likes or
reach.

## Design Files

The files in `prototypes/` are high-fidelity HTML design references. They show
intended UI and behavior, but they are not production code to copy. Rebuild the
experience in the real Next.js/FastAPI codebase.

## Fidelity

The prototypes should be treated as high fidelity for layout, color, spacing,
typography, and interaction intent. Customer-facing product copy remains
Vietnamese in the actual website/app because the intended users are Vietnamese.
Engineering documentation should be English.

## Main Screens

### 1. MVP App

Prototype: `Havi - MVP App.dc.html`.

Layout: fixed left sidebar, main content area, warm paper background, and a
compact operational dashboard style.

Dashboard:

- Greeting/date header
- Three actionable stat cards
- Raw-input CTA
- Suggested work cards
- Zalo approval banner in the prototype
- Recent activity feed

Content creation:

- Raw input list and upload/drop area
- Content generation action
- Publishing-mode toggle
- Async generating state
- Draft cards with channel labels
- Bulk and per-draft approval actions

Calendar:

- Week/day columns
- Post cards with channel, time, and status
- Reschedule controls for approved/scheduled posts in the implementation

Leads:

- Approval-first messaging principle
- Lead cards with source/status
- Drafted replies that require owner approval
- No deceptive seeding or impersonation

Reports:

- Business-result stats
- Channel attribution
- Weekly published-post bars
- Plain-language insight block

### 2. Onboarding

Prototype: `Havi - Onboarding.dc.html`.

Three steps:

1. Choose industry.
2. Connect at least one channel.
3. Let Havi learn initial context and enter the app.

### 3. Login and Signup

Prototype: `Havi - Dang Nhap.dc.html`.

The prototype shows OTP-first login. The production roadmap has moved the MVP to
email/password with password reset, while keeping the UX principle: one screen,
one job, large inputs, clear primary action.

### 4. Landing Page

Prototype: `Havi - Landing Page.dc.html`.

Public marketing page with product promise, workflow explanation, pricing, and
trial CTA. It should describe benefits, not internal prompt chains or scraping
mechanics.

### 5. Architecture Prototype

Prototype: `Havi - Kien Truc He Thong.dc.html`.

Key backend principles:

- LLMs run only from explicit jobs, not background loops.
- Cheap filters come before expensive models.
- One generation call creates multiple channel drafts.
- Tenant profile and prompt context are cached.
- AI core is channel-agnostic; each platform is an adapter.
- Every task is a job with an id, queueing, retry policy, and event logging.

## Repository and Deployment

See `REPOSITORY_STRATEGY.md` for the monorepo structure:

- `apps/web`: Next.js frontend
- `apps/backend`: FastAPI API, Celery worker, scheduler, and domain core
- frontend talks to backend only over HTTP/OpenAPI
- secrets never belong in the frontend bundle
- processes can deploy independently

## Approval Workflow

Default rule: no content goes online until the owner approves it.

Publishing modes:

- `review_first` is the default and recommended mode. AI drafts move to
  `pending_approval`; the owner approves; scheduled worker publishes later.
- `full_auto` is opt-in and should be unlocked only after a tenant has a strong
  approval history with low edit rate. It applies only to content publishing, not
  customer replies.

Content item state machine:

```text
draft -> pending_approval -> approved -> scheduled -> publishing -> published
                                                      -> failed -> dead_letter
```

Backend requirements:

- Approval writes `approved_by`, `approved_at`, and an audit event.
- Publish jobs use idempotency keys, unique constraints, and row locks.
- Customer replies always require approval unless they are exact pre-approved FAQ
  answers.
- Editing a draft creates version history instead of overwriting history.
- Publish errors are classified as temporary, auth/permission, or permanent
  validation errors.

## Interactions and Behavior

- Navigation should behave like an app, without full-page reloads.
- Generating/learning states in prototypes are simulated; production uses async
  jobs and polling.
- Approval can update optimistically in the UI, but backend state is authoritative.
- Disabled and hover states should match the design system.
- No automatic outbound action is allowed except approved scheduled posts and
  exact pre-approved FAQ responses.

## Production State Model

- `tenant`: industry, brand voice, logo, channels, plan, token quota
- `content_job`: id, tenant id, raw inputs, status, draft ids
- `draft/content_item`: channel, kind, text, media note, status, schedule,
  approval fields, version history
- `tenant.publishMode`: `review_first` or `full_auto`
- `auth`: email/password for MVP; OTP remains a future/alternate auth option
- `lead`: source, message, suggested reply, status
- `suggestion`: generated content idea that still enters the approval loop
- `event_log`: audit, tokens, provider, latency, and operational traceability

## Design Tokens

- Primary: `#D4956F`
- Primary dark: `#B8744D`
- Background: `#F5F1ED`
- Dark surface: `#2C2C2C`
- Success: `#5FA76F`
- Info: `#3B6B9F`
- Danger: `#C75B4A`
- Border: `#E0D9D3`
- Typography: Merriweather for display headings, Inter for UI/body
- Spacing: 8px grid
- Radius: 8px controls, 12px cards, 999px pills

## Phase-1 Build Scope

Build for real:

- photo/text input
- content engine with one call producing multiple drafts
- official Facebook Page publishing first
- Google Business/Zalo later by priority and API access
- approval-first publishing
- basic reports from real publish data
- FAQ/reply automation only after explicit approval rules exist

Manual behind-the-scenes during early pilot:

- social listening
- CRM lifecycle operations
- qualitative customer feedback loops

Legal/platform principle: use official APIs and keep approval-before-send as the
default for anything that leaves the system.

## Files

- `Havi - MVP App.dc.html` — main app prototype
- `Havi - Dang Nhap.dc.html` — login/signup/OTP/password reset prototype
- `Havi - Onboarding.dc.html` — onboarding prototype
- `Havi - Landing Page.dc.html` — public landing page prototype
- `Havi - Kien Truc He Thong.dc.html` — backend architecture prototype
- `Havi - AI Marketing.dc.html` — pitch/demo reference
