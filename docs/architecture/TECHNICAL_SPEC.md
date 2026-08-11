# Technical Spec — Modules Missing From the Original PRD

This supplements `README.md` and `REPOSITORY_STRATEGY.md`. The backend
(`apps/backend/api`) owns all database state and secrets.

## 0. User Accounts

- `user {id, email, name, password_hash, phone, active_workspace_id, created_at}`
- Email/password with Argon2id is the MVP login path.
- Phone is optional and reserved for Zalo/OA-related workflows, not primary auth.
- Password reset uses a six-digit email code:
  `otp_challenge {email, code_hash, expires_at, attempt_count, consumed_at}` with
  TTL, attempt limits, and resend cooldown.

## 1. Workspace / Multi-Tenant Model

- `workspace {id, name, industry, owner_user_id, plan, created_at}`
- `workspace_member {workspace_id, user_id, role}`
- One user can belong to multiple workspaces.
- JWT carries `active_workspace_id`.
- Every API query must scope by workspace id to prevent cross-tenant leaks.
- UI should support workspace selection when a user has more than one workspace.

## 2. Brand Profile / Brand Voice

- `brand_profile {workspace_id, industry, tone, banned_claims[], faq[], logo_url, brand_colors[]}`
- Required input for content-generation prompts.
- Settings UI owns tone, banned claims, FAQ, and reusable brand context.

## 3. Media Library

- `media_asset {id, workspace_id, url, type, tags[], status, uploaded_at}`
- Clients upload directly to object storage; the API stores metadata and upload
  tickets.
- Image/audio/video assets can be reused for new content.
- Future video pipeline output is stored as a new `media_asset` and follows the
  same approval flow as content.

## 4. Content Calendar

- `content_item.scheduled_at` is the source of truth.
- Calendar is a view/projection, not a separate state table.
- Rescheduling is allowed only for `approved` / `scheduled` items.
- Published items cannot be rescheduled or edited.

## 5. Content Editor and Approval Queue

- Approval queue lists `pending_approval` items by workspace.
- Filters should include channel and date.
- Bulk approve/reject and edit-before-approve are supported.
- `content_item_version {content_item_id, version_no, text, edited_by, edited_at}`
  stores every text edit.

## 6. Connected Accounts

- `platform_connection {workspace_id, platform, access_token_encrypted,
  refresh_token_encrypted, expires_at, status, connected_by}`
- Platform tokens are encrypted with `TOKEN_ENCRYPTION_KEY`.
- OAuth follows each provider's official flow.
- Publishing is blocked unless connection status is `connected`.

## 7. Unified Inbox

- `inbox_item {id, workspace_id, platform, type, content, author_name, sentiment,
  ai_suggested_reply, status, created_at}`
- Social listening should use official APIs where possible.
- Suggested replies must identify the owner/business truthfully.
- Replies do not support full-auto mode; the owner must send or approve.

## 8. Lead Pipeline / CRM

- `lead {id, workspace_id, name, phone, source, stage, notes, created_at}`
- `crm_message {lead_id, channel, draft_text, status, created_at}`
- AI can draft nurture messages, but the owner approves each message.
- UI should expose a stage-based pipeline and message history.

## 9. Analytics

- Sources: `content_item.published_at`, engagement snapshots, and lead conversion.
- MVP metrics: posts published by channel, new leads, and lead-to-won rate.
- Real-time analytics are not required for MVP.

## 10. Settings and Billing

- Settings owns brand profile, connected accounts, and publishing mode.
- `subscription {workspace_id, plan, status, current_period_end}`
- Payment gateway secrets stay backend-only.
- Workspace members are invited by email; phone remains optional.

## API Surface Summary

```text
/auth/*              sign-up/login, password reset, refresh token, optional phone
/workspaces/*        CRUD, members
/brand-profile       GET/PUT
/media               upload, list, tag
/content             CRUD, approve, versions, publish jobs
/calendar            scheduled content view
/connections/*       OAuth start/callback, status, disconnect
/inbox               list, reply
/leads               CRUD, stage updates
/crm-messages        list, approve/send
/analytics           summary, timeseries, events, operations
/billing             plan, invoices
```

Every endpoint requires `Authorization: Bearer <JWT>` unless explicitly public,
and all workspace data is scoped by `active_workspace_id`.
