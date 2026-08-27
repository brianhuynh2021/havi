# Havi Product Contract

This document is the canonical boundary between what Havi ships, what it may
claim, and what remains a product direction. Product copy, pricing, sales
material and release tests must agree with it. `AGENTS.md` contains development
rules; this contract contains the customer-facing truth.

Last verified: 2026-08-27.

## Product promise

Havi is the control plane and AI secretary for a business's social operations.
It gathers work that needs attention, prepares safe next steps, enforces human
approval for external actions, and records the verified outcome. It reduces
operational load; it does not promise business growth.

The product consists only of accounts and social connections, media and content,
publishing calendar and status, conversations, team permissions, approval,
audit history, connection health and operational reporting.

## Shipped and claimable now

- Multi-tenant accounts, workspaces, members and server-enforced roles.
- Reusable media, content drafts, versions and brand constraints.
- Facebook Page and Facebook Reels publishing through official APIs.
- Draft → approve → publish, idempotent jobs and provider-confirmed outcomes.
- Messenger/comments ingestion, work assignment and explicit reply or dismiss.
- A prioritized work queue for approvals, inbox, failed publishes and broken
  connections.
- A 24-hour operational brief and transparent time-saved calculation derived
  from actions stored by Havi.
- Activity history, publishing/conversation reports and VietQR billing.
- AI-assisted content drafting. Inbox triage is deterministic; an exact,
  previously approved FAQ may prefill a reply, but a person must submit it.

## Not shipped and not claimable

- Learned brand baselines, Business Memory or anomaly detection.
- A general autonomous agent that continuously observes, plans and acts.
- Automatic AI reply drafting for non-FAQ conversations.
- Automatic platform-token refresh or engagement polling.
- Public live publishing to TikTok, YouTube, Google Business Profile or Zalo OA.
- Google/Facebook social sign-in, a persisted notification center, or English UI.
- Automatic enterprise lead capture from the public website.
- Ad creation, budget control, video editing, goals, growth roadmaps, customers,
  revenue, reach or conversion promises.

Items in this section may appear in a roadmap only when clearly labelled as
future work. They must not appear as current plan benefits or sales claims.

## Customer and activation

The first design partner is a service business with an active Facebook Page and
at least two people involved in social operations: one prepares or handles work,
and one owns or approves it.

Activation requires a real Facebook Page connection and one verified operation
within 24 hours: either a provider-confirmed approved post or a real conversation
handled in Havi. Registration, opening a demo, or generating an unapproved draft
does not count as activation.

## Safety and measurement

- Nothing publishes without human approval.
- External success requires evidence returned by or read back from the provider.
- Unknown states fail closed and enter reconciliation.
- Every tenant query is scoped to a workspace.
- Time saved is an estimate, not elapsed-time telemetry. Every displayed total
  must expose the counted actions and per-action assumption.
- No customer-facing copy may promise customers, revenue or growth.

## Claim gate

A customer-facing claim is allowed only when an automated test or a named pilot
procedure can prove it against current code and a real provider. If proof is not
available, describe the workflow that exists or label the item as future work.
