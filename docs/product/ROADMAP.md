# Havi Product Roadmap

Customer-facing claims must follow [PRODUCT_CONTRACT.md](PRODUCT_CONTRACT.md).
This roadmap includes future capability and is not itself a list of shipped
features.

## 1. Product contract

**This document is future direction. It is not a list of shipped features.**
What exists today and may be claimed to customers is defined only in
[PRODUCT_CONTRACT.md](PRODUCT_CONTRACT.md), including the canonical nine-item
product scope. That document wins over this one on any disagreement.

The direction is an **AI Secretary (Chief of Staff)** that proactively observes,
prioritizes anomalies, recommends actions and executes them upon approval.
Business Memory and anomaly detection are **not shipped** and must never be
described in the present tense.

### The daily user is staff, not the owner

Whoever opens Havi every day is usually not the person who pays for it: it is the
employee who mans the page, the owner's child, the resort's front-of-house staff
who was handed Facebook and TikTok. The owner buys control and traceability; the
staff member gets one screen instead of five.

That is why the main surface is a single work queue rather than a dashboard of
counts. Approval stops being friction the moment the writer and the accountable
person are different people — it is the owner's peace of mind, and the audit trail
is how they verify without standing over anyone.

Every item offers two exits and both are correct: handle it inside Havi, or deep
link straight to the platform. The expensive part of the job is not answering —
it is hunting across five sites for what needs answering.

The owner reads a brief, not a queue. Staff work the queue daily; the owner opens
Havi weekly to learn what happened and whether it earned its fee. Those are two
surfaces, and forcing the owner through the staff's queue means reading forty
lines to find four.

### What the brief may not say

The brief counts from data Havi owns, in SQL, with no model call. That rules out
three numbers that every "AI social manager" pitch opens with, because Havi
measures none of them: revenue attributed to social (no order data), per-platform
engagement (no insights permission yet), competitor movement (a different data
domain entirely). Absent beats guessed.

Time saved is reported only for work Havi actually performed — replies sent,
posts published — multiplied by a stated per-action assumption that is shown on
screen next to the total. A customer who can see the arithmetic can check it; a
total with the assumption hidden is advertising. Anything that is real value but
has no timestamp to measure ("spotted a failed post", "saved five tabs") stays out
of the number.

### Pricing may only sell what ships

A plan may sell seats, brands and AI quota — never a channel count that
`domain/policies/channel_capabilities.py` does not serve. `LIVE_CHANNELS` is
Facebook Page and Reels; every tier therefore states the same channel list and
differs on operating scale. Selling channel counts that do not exist is the same
class of error as inventing a metric, so this rule outlives the specific bug that
prompted it: when a channel goes live, `LIVE_CHANNELS` and the pricing page move
in the same change.

The same applies to plan identity in the UI. Plan keys are the `Plan` enum values
(`trial/tiem_nho/toan_dien/doanh_nghiep`) and are compared verbatim — a plan label
looked up by a key the API never returns silently shows a paying customer the
wrong tier, and no test fails.

### Retired product concepts

The following are intentionally outside Havi: goal/roadmap/evidence operating
systems, AI-marketing positioning, revenue or growth promises, video editing,
POS, inventory, delivery, sales pipelines, complex CRM, direct ad spending,
spam-scale bulk publishing and decorative dashboards without an action.

## 1b. Five-to-ten-year vision

Havi becomes the trusted control plane for a company's social presence: one
identity and permission layer, one media library, one review workflow, one
calendar, one inbox, one audit trail and one truthful view of channel health.

The long-term moat is not just “more AI.” It is **Business Memory** and governance: understanding the baseline of what is normal for a specific brand (e.g., distinguishing a viral alert from normal traffic), who can act, what was approved, what reached each platform, what failed, and what still needs attention across brands, branches and external collaborators.

## 1c. Paid-promotion boundary

Organic publishing is managed directly after approval. Paid promotion remains
on the provider:

- Havi may validate the selected post, prepare a checklist and deep-link to the
  correct Meta, TikTok or Google interface.
- The user sets targeting, budget and payment on that platform.
- Havi may later read provider-reported status and spend with read-only access.
- Havi does not create ads, change budgets, turn campaigns on/off, hold media
  money or take a percentage of ad spend.

## 2. Delivery sequence

A ticked box means the capability runs against a real provider and is covered by
tests — not that the code exists. Untick anything that regresses.

### Phase A — Facebook operations core

- [x] Reliable Page and Reels publishing with external confirmation.
- [x] Messenger inbox with signed webhook ingestion and explicit human replies.
- [x] Media library, content revisions, approval queue and calendar.
- [x] Connection health, failed-post recovery and audit history.
- [ ] Customer Zero operation at Trung Tâm Công Nghệ Nhật Minh.

Exit criteria: zero false publish/reply success, no cross-workspace access, all
critical integration tests passing.

### Phase B — Team control

- [x] Organization above workspaces for multiple brands or branches.
- [x] Clear owner, marketer, reviewer and support permissions.
- [ ] Review assignments, activity filters and approval accountability.
- [ ] Mobile-friendly daily operations.

### Phase B2 — Draft quality from the shop's own data

The competitive question is not whether Havi can post; Buffer posts too. It is
whether the draft is close enough to what the owner would have written that
approving it is cheaper than rewriting it. Everything in this phase serves that
one number: how often a draft ships unedited.

The model is Cursor, not a chat window. Cursor won a market that already had
Copilot by reading the user's own codebase, so its suggestions arrive in the
user's own names and patterns. The equivalent here is not "AI writes posts" but
**AI that knows this shop** — and the shop's data is already in Havi's database.

#### Shipped: the owner's own post, and what the page will actually show

- `POST /content/items` takes a finished post and queues it without calling a
  model. Before it, the only way in was the "let Havi write it" button, so anyone
  arriving with a post already written had to have Havi produce a draft nobody
  wanted, spend quota on it, and overwrite it. The new path still obeys the
  workspace `publish_mode` — writing it yourself is not a back door around
  review.
- `POST /content/preview` answers "what will this look like on the Page" without
  writing anything. Facebook does not render Markdown and cuts a post after
  roughly 800 characters, so a post written in an editor that shows bold text
  arrives on the Page with the asterisks visible and the tail behind "See more".
  Neither is detectable after publishing, which is the only time it used to
  become visible. The preview deliberately renders as badly as Facebook does; one
  that showed `**bold**` as bold would be lying about the outcome.

#### Shipped (Phase A groundwork, not yet used for drafting)

- Every AI-generated draft is stored as version 1 the moment it is created, with
  `edited_by = NULL` marking machine authorship. Owner edits become v2, v3, …
  This is what makes the pair `(what AI wrote → what the owner shipped)`
  recoverable; `content_items.text` is overwritten on edit, so a draft not saved
  at creation time is gone for good. `ContentRepository.list_ai_human_pairs`
  reads those pairs back.

#### Ordered by evidence, not by appeal

1. **Style from real edits.** Feed recent `(AI draft, owner's final)` pairs into
   the drafting prompt. Where the owner edits is a stronger signal than any
   onboarding form, because it is behaviour rather than self-description — every
   shop describes its tone as "friendly and professional".
2. **Topics from the real inbox.** What customers actually asked this week
   decides what is worth posting about. Requires the Messenger webhook to have
   been live long enough to hold real traffic — `inbox_items` is empty until
   then, so this cannot be built before the pilot has run.
3. **Inline refine over regeneration.** Presets (shorten, add a call to action,
   warmer) plus a free-text instruction that rewrites the current draft instead
   of generating a new one, with a word-level diff so the owner approves a
   visible change rather than re-reading a whole post. This lowers the cost of a
   near-miss draft, which is the common case and the one regeneration handles
   worst.
4. **Remaining pre-publish diagnostics.** Video aspect ratio and absolute-claim
   wording. Facebook's own rendering differences already ship (see below); what
   is left is channel constraints and policy risk, and it belongs after the three
   above because a well-formatted draft in the wrong voice is still rewritten.

Deliberately excluded: learned brand baselines and automatic style rules derived
without review. A rule inferred from a handful of edits and applied silently
produces drafts nobody can explain, and the owner cannot correct what they
cannot see. Prompt context stays inspectable.

No vector database until the data says otherwise. One shop's corpus is hundreds
of posts, not millions; Postgres text search with recency and frequency ordering
covers it, and an embedding store can be added later behind the same interface.

Entry criteria: the Facebook pilot has produced real edit pairs and real inbox
volume. Building this before that means guessing which part of the draft was
wrong — which is copying the diagram instead of reading the evidence.

Exit criteria: unedited-approval rate improves against the pilot baseline, and
prompt context remains auditable per draft.

### Phase C — Additional organic channels

Expand only after the previous channel is operationally complete. Implementation
is not the long pole; provider approval is. Every channel's review is applied
for in parallel, well before its implementation slot comes up.

1. [ ] TikTok. The second channel, because it reaches more Vietnamese small
   businesses than any other after Facebook. An unaudited TikTok app can only
   post privately, so its audit is applied for during the Facebook pilot — it is
   the slowest approval in the set and sits on the critical path from day one.
2. [ ] YouTube Shorts. Same Havi path as TikTok: a finished vertical clip is
   published and confirmed, so the second video channel is mostly adapter work.
   Upload quota needs an increase request against the default daily limit.
3. [ ] Google Business Profile, deferred behind the video channels. Beyond enabling
   the API it requires a separate access application.
4. [ ] Email is not a channel decision. It needs list management, unsubscribe and
   consent handling that social operations does not have, and is decided
   separately rather than queued behind the channels above.

Each adapter must support truthful connection state, provider constraints,
idempotent publishing, reconciliation and channel-specific error guidance.

### Phase D — Multi-brand and agency operations

- [ ] Gate `POST /organizations` on plan. The multi-brand tier is sold as a paid
      capability, but organization creation enforces no plan check, so the tier
      is billable and free at the same time.
- [ ] Shared media with explicit workspace ownership.
- [ ] Cross-workspace calendar and health overview.
- [ ] Client review links with limited permissions.
- [ ] Reusable approval policies and exportable audit history.
- [ ] Concise reports comparing operational workload and failures by channel.

### Phase E — Governance platform

- [ ] Enterprise identity and access controls.
- [ ] Approval policies based on brand, channel and risk.
- [ ] Retention, export and compliance controls.
- [ ] Provider-independent archive of approved content and external references.
- [ ] Read-only paid-promotion status where providers permit it.

## 3. Prioritization test

A proposed feature belongs in Havi only if it materially improves at least one:

- control over social channels;
- reduction in repetitive operations;
- reduction in missed work or hidden failures;
- governance and traceability for a team.

If it primarily promises business outcomes or duplicates a specialist tool, it
does not belong in the product.

## 3b. Commercial model

Plans sell **operating scale**, not AI tokens. What grows with a business is the
number of people manning channels, the number of channels connected, and the
number of brands. Those are where both value and cost increase, so those are the
ladder. Token quota is a cost guard, not a price lever.

Brands bill per workspace: `plan` lives on the workspace, so a second brand is a
second subscription. That is the expansion lever, and it needs no new mechanism.

Seats and channels bill as add-ons on top of a plan. Without them, a customer on
the 189k plan who needs a fourth person must jump to 369k — a staircase, not a
lever. The add-on price is set so a small need costs a small step, and a large
need makes the next tier genuinely cheaper. The pricing page then argues for the
upgrade on its own.

Annual billing exists because VietQR has no card-on-file: every month the
customer must actively decide to pay again, and active renewal churns far worse
than automatic renewal. An annual term trades twelve decisions for one. It is
quoted as "pay ten months, use twelve" rather than a percentage, because the
first phrasing needs no arithmetic.

Quota counts output tokens at a weight, not one-for-one. Output costs four to five
times input at every provider, so summing the two raw meant two workspaces at the
same cap could differ several-fold in real cost — the cap guarded volume, not
spend. Quota is still expressed in tokens, because a ratio does not go stale when
a provider changes prices.

Limits are shown to customers in units they use: seats, channels, and posts.
"2,000,000 tokens" means nothing to a business owner. The token-to-post rate is
measured from that workspace's own history and falls back to a declared default,
which is stated on screen — an estimate presented as a measurement is the same
class of error as inventing a metric.

## 4. Metrics

Havi's primary user-facing North Star is **"Time Havi Saved"** (e.g., "Havi saved you 7h 18m this week"). This proves the value of the AI Secretary by measuring cognitive load and manual tasks eliminated (comments auto-triaged, issues detected proactively).

Operations also monitors internal service health:
publish success, connection health, sync latency, unresolved failures, pending
approvals, unhandled conversations, incident recovery time, retention and paid
workspace count.
