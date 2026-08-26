# Havi Product Roadmap

## 1. Product contract

Havi is a lightweight social media management and operations platform for
businesses, freelancers and teams. It provides one place to control:

1. social accounts and connection health;
2. reusable media and content;
3. calendar and publishing status;
4. messages, comments and reviews;
5. members, roles and permissions;
6. draft → review → approve → publish;
7. activity history and audit;
8. channel alerts and failures;
9. concise multi-channel operational reports.

AI may draft or summarize. It is not the product promise and does not make
business decisions.

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

### Retired product concepts

The following are intentionally outside Havi: goal/roadmap/evidence operating
systems, AI-marketing positioning, revenue or growth promises, video editing,
POS, inventory, delivery, sales pipelines, complex CRM, direct ad spending,
spam-scale bulk publishing and decorative dashboards without an action.

## 1b. Five-to-ten-year vision

Havi becomes the trusted control plane for a company's social presence: one
identity and permission layer, one media library, one review workflow, one
calendar, one inbox, one audit trail and one truthful view of channel health.

The long-term moat is not “more AI.” It is operational memory and governance:
who can act, what was approved, what reached each platform, what failed, and
what still needs attention across brands, branches and external collaborators.

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

### Phase A — Facebook operations core

- Reliable Page and Reels publishing with external confirmation.
- Messenger inbox with signed webhook ingestion and explicit human replies.
- Media library, content revisions, approval queue and calendar.
- Connection health, failed-post recovery and audit history.
- Customer Zero operation at Trung Tâm Công Nghệ Nhật Minh.

Exit criteria: zero false publish/reply success, no cross-workspace access, all
critical integration tests passing.

### Phase B — Team control

- Organization above workspaces for multiple brands or branches.
- Clear owner, marketer, reviewer and support permissions.
- Review assignments, activity filters and approval accountability.
- Mobile-friendly daily operations.

### Phase C — Additional organic channels

Expand only after the previous channel is operationally complete. Implementation
is not the long pole; provider approval is. Every channel's review is applied
for in parallel, well before its implementation slot comes up.

1. TikTok. The second channel, because it reaches more Vietnamese small
   businesses than any other after Facebook. An unaudited TikTok app can only
   post privately, so its audit is applied for during the Facebook pilot — it is
   the slowest approval in the set and sits on the critical path from day one.
2. YouTube Shorts. Same Havi path as TikTok: a finished vertical clip is
   published and confirmed, so the second video channel is mostly adapter work.
   Upload quota needs an increase request against the default daily limit.
3. Google Business Profile, deferred behind the video channels. Beyond enabling
   the API it requires a separate access application.
4. Email is not a channel decision. It needs list management, unsubscribe and
   consent handling that social operations does not have, and is decided
   separately rather than queued behind the channels above.

Each adapter must support truthful connection state, provider constraints,
idempotent publishing, reconciliation and channel-specific error guidance.

### Phase D — Multi-brand and agency operations

- Shared media with explicit workspace ownership.
- Cross-workspace calendar and health overview.
- Client review links with limited permissions.
- Reusable approval policies and exportable audit history.
- Concise reports comparing operational workload and failures by channel.

### Phase E — Governance platform

- Enterprise identity and access controls.
- Approval policies based on brand, channel and risk.
- Retention, export and compliance controls.
- Provider-independent archive of approved content and external references.
- Read-only paid-promotion status where providers permit it.

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

## 4. Internal health metrics

Havi does not impose a user-facing North Star. The team monitors service health:
publish success, connection health, sync latency, unresolved failures, pending
approvals, unhandled conversations, incident recovery time, retention and paid
workspace count.
