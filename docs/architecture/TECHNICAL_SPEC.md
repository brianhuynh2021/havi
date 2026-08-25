# Havi Technical Specification

This document defines the current social-operations contract. The backend owns
database state, provider credentials, authorization, and state transitions.

## Data model

- `organization`: groups workspaces for a company or agency.
- `workspace`: one brand or branch; the primary tenant boundary.
- `workspace_member`: membership and role within a workspace.
- `brand_profile`: tone, prohibited claims, approved FAQ and reusable brand data.
- `platform_connection`: encrypted OAuth tokens, account identity and health.
- `media_asset`: reusable images, audio and finished video.
- `content_job`, `content_item`, `content_item_version`: generation request,
  editable draft and revision history.
- `publish_job`: idempotent scheduled publishing attempt and provider result.
- `video_post`, `video_publish_attempt`: finished clip review and confirmed publish.
- `inbox_item`: inbound message/comment/review, reply draft and handling status.
- `event_log`: tenant-scoped audit and operational diagnostics.
- `invoice`: SaaS billing record.

There are no goal, roadmap, lead, CRM, POS, inventory or delivery tables in the
active model.

## State contracts

### Content

`draft → pending_approval → approved → scheduled/publishing → published`

Failures are explicit. Permanent or exhausted errors enter `dead_letter`.
Ambiguous external outcomes enter `pending_reconciliation` and must not be sent
again until reconciled.

### Inbox

`new → drafted → sent | failed | dismissed`

Drafted replies remain editable. A send is marked successful only after the
provider confirms it. Exact approved FAQs are the only auto-reply exception.

### Connections

`connected | expired | revoked`

Publishing is blocked unless a valid connection is available. The UI surfaces
reauthorization instead of hiding provider errors.

## API surface

```text
/auth/*              identity, sessions and password reset
/workspaces/*        workspaces, members and activation
/brand-profile       reusable brand data and approved FAQ
/media/*             upload tickets, completion, list and update
/content/*           jobs, drafts, versions, approval and publish jobs
/calendar/*          scheduled content projection and rescheduling
/connections/*       OAuth start/callback, health and disconnect
/inbox/*             list, explicit reply and dismiss
/analytics/*         dashboard, reports, events and operational metrics
/billing/*           subscription, checkout and invoices
/webhooks/meta       signed inbound social events
```

Every endpoint requires a bearer token unless explicitly public. Every business
read and write is scoped to the active workspace.

## Provider rules

- Use official OAuth and publishing APIs.
- Never automate provider web pages or store user passwords.
- Organic publishing may happen directly after approval.
- Paid promotion is a handoff: validate the post and open the provider's own ad
  interface. Havi does not create campaigns, change budgets or hold ad funds.
- Provider responses are the source of truth for external success.

## Quality gates

1. Unit tests for domain rules and state transitions.
2. Integration tests against PostgreSQL for tenant scope and idempotency.
3. Router tests for authentication, truthful errors and contract shape.
4. Frontend tests for loading, empty, failure and action states.
5. OpenAPI regeneration plus lint, test and production build before release.
