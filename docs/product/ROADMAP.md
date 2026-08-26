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

Expand only after the previous channel is operationally complete. Provider
approval, not implementation, sets the schedule: every channel's review is
applied for in parallel, and channels ship in whatever order approvals land.

1. YouTube Shorts and TikTok. Both take a finished vertical clip through the
   same Havi path, so whichever audit clears first ships first. TikTok reaches
   more Vietnamese small businesses; an unaudited TikTok app can only post
   privately, and YouTube upload quota needs an increase request.
2. Google Business Profile, deferred behind the video channels. Beyond enabling
   the API it requires a separate access application, the slowest approval in
   the set.
3. Email is not a channel decision. It needs list management, unsubscribe and
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

## 4. Internal health metrics

Havi does not impose a user-facing North Star. The team monitors service health:
publish success, connection health, sync latency, unresolved failures, pending
approvals, unhandled conversations, incident recovery time, retention and paid
workspace count.
