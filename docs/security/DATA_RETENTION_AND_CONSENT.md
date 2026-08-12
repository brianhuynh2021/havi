# Data Retention, Deletion, and Consent Policy

> Documentation language: English. Product UI/customer-facing copy remains
> Vietnamese because the target users are Vietnamese small-business owners.

Last updated: 2026-08-11

## 1. Overview and Scope

This document defines the data retention, deletion, and consent recording policy for the Havi platform (`havi-platform`).

Havi processes small-business marketing inputs (text notes, voice notes, photos), AI-generated drafts, platform OAuth tokens (Facebook Page access tokens), and usage event logs. Because Havi sells marketing outcomes directly to small shop owners, user trust, transparency, and data ownership are core architectural requirements.

## 2. Retention Schedules

| Data Category | Data Type | Default Retention | Deletion Trigger | Retained After Deletion |
|---|---|---|---|---|
| **Account & Identity** | Email, Name, Password Hash, Phone | Duration of active account | User Account Deletion (`DELETE /auth/me`) | None |
| **Auth Sessions** | Refresh Sessions | Active until expiry / revoked | Logout / Password Reset / User Deletion | Revoked sessions pruned after 30 days |
| **Workspace Profile** | Workspace Name, Industry, Plan, Brand Profile | Duration of workspace | Workspace Deletion (`DELETE /workspaces/{id}`) | None |
| **Workspace Membership** | User <-> Workspace Role Mapping | Duration of membership | Member Removal / Workspace Deletion | None |
| **Media Assets** | Object Storage Files (S3/MinIO) & Metadata | Duration of workspace | Workspace Deletion / Asset Removal | None |
| **Content & Drafts** | Jobs, Items, Version History, Schedule Datetimes | Duration of workspace | Workspace Deletion | None |
| **Publishing Jobs** | Publish Jobs, External Post IDs, Failure Details | Duration of workspace | Workspace Deletion | External post remains on Page (owned by Facebook) |
| **Platform OAuth Tokens** | Encrypted Access Tokens & Refresh Tokens | Duration of active connection | Disconnect / Workspace Deletion | Permanently purged |
| **Operational & Audit Logs** | Event Log (Token Usage, Job Latency, Provider Errors) | 90 days for operational audit | Workspace Deletion | Anonymized (workspace_id cleared, raw inputs scrubbed) |

## 3. Workspace Deletion Policy (`DELETE /workspaces/{workspace_id}`)

### Access Control
- Workspace deletion can **only** be initiated by a user with the `OWNER` role.
- If a workspace has multiple members, only an `OWNER` can trigger deletion.

### Cascading Deletion Order
When a workspace is deleted:
1. **Media Asset Clean-up**: All `media_assets` associated with the workspace are listed, and their underlying physical objects in S3 / MinIO storage buckets are deleted via object-storage API.
2. **Platform Connections Purge**: All encrypted access tokens and refresh tokens in `platform_connections` are permanently deleted from Postgres. Token material cannot be recovered.
3. **Publishing & Content Data**: `publish_jobs`, `content_item_versions`, `content_items`, and `content_jobs` assigned to the workspace are cascade deleted.
4. **Brand Profile & Settings**: The 1:1 `brand_profiles` record is deleted.
5. **Workspace Memberships**: All `workspace_members` rows for this workspace are removed.
6. **Active Workspace Reset**: Any user whose `active_workspace_id` pointed to the deleted workspace will have their `active_workspace_id` set to `NULL` (requiring workspace selection/onboarding on next API interaction).
7. **Audit Log Anonymization**: `event_log` entries referencing the workspace have `workspace_id` set to `NULL`, and any `input_summary` / `output_summary` fields containing raw prompt context are scrubbed. Token metrics (`tokens_in`, `tokens_out`, `duration_ms`, `provider`) are preserved for aggregate platform analytics and quota auditing without identifying the workspace.

## 4. User Account Deletion Policy (`DELETE /auth/me`)

### Access & Safety Rules
When a user requests account deletion:
1. **Sole Workspace Owner Check**: If the user is the **sole member** of a workspace, that workspace is automatically deleted (following the Workspace Deletion Policy).
2. **Shared Workspace Ownership Check**: If the user is an `OWNER` of a workspace with other members, and no other `OWNER` exists, account deletion is **blocked** with HTTP 409 Conflict. The user must transfer ownership to another member or delete the workspace before deleting their account.
3. **Session Revocation**: All active `refresh_sessions` for the user are immediately revoked.
4. **User Removal**: The `users` record (including email, name, password_hash, and phone) is permanently deleted.

## 5. Platform Token Safety and Revocation

1. **At Rest**: Platform tokens are stored encrypted using AES-GCM-256 with `HAVI_TOKEN_ENCRYPTION_KEY`.
2. **On Disconnect**: When a user clicks disconnect or deletes a workspace, the encrypted token rows are immediately removed via SQL `DELETE`.
3. **Platform API Revocation**: The platform connection service sends an asynchronous revocation request to Facebook Graph API (`DELETE /me/permissions`) where applicable.

## 6. Consent Records & Audit Logging

Havi tracks key user consent and policy decisions to maintain auditability and compliance:

### Consent Types Recorded
1. **Publishing Mode Consent**:
   - `REVIEW_FIRST` (default): Every AI draft must be manually approved by owner before publishing.
   - `FULL_AUTO`: Owner explicitly consents to automatic dispatches at scheduled times.
   - Updating `publish_mode` via `PATCH /workspaces/{id}` emits an `EventLog` entry with `job_kind="consent.publish_mode_changed"`, capturing the user ID, timestamp, and chosen mode.
2. **Platform Integration Consent**:
   - Connecting Facebook Page via OAuth records `job_kind="consent.platform_connected"`, capturing platform name, external account ID, and connecting user ID.
3. **Terms & Onboarding Consent**:
   - Workspace creation records `job_kind="consent.workspace_created"`.

## 7. Compliance and Data Requests

- **Data Export**: Users may export brand profiles, content items, and event logs via standard API endpoints prior to deletion.
- **Immediate Effect**: Database deletion operations take place within the primary transaction. Backup retention follows the standard 7-day database snapshot cycle (after which database backups naturally expire).
