# Havi System Architecture

Havi uses a modular monolith with explicit process boundaries. PostgreSQL is the
source of truth, Redis carries queued work, object storage holds media, and all
social access goes through official provider APIs.

## Dependency direction

```text
api / worker / scheduler
          ↓
application services
          ↓
domain policies and outbound ports
          ↑
persistence and provider adapters
```

This is layered-with-DI, not hexagonal: ports exist only for the six outbound
integrations, there is no repository port, and `domain/models/` are SQLAlchemy
models. See [ARCHITECTURE.md](../../ARCHITECTURE.md) §"What the layering
actually is" for the precise shape and its cost.

Frontend routes compose feature screens. Screens use the generated OpenAPI
client and shared UI primitives; they do not own provider secrets or duplicate
backend state machines.

## Processes

```mermaid
flowchart LR
    WEB["Next.js web"] --> API["FastAPI"]
    API --> DB[("PostgreSQL")]
    API --> STORE["Object storage"]
    API --> REDIS[("Redis queue")]
    REDIS --> CONTENT["Content worker"]
    REDIS --> PUBLISH["Publish worker"]
    BEAT["Scheduler"] --> REDIS
    CONTENT --> DB
    PUBLISH --> SOCIAL["Official social APIs"]
    SOCIAL --> PUBLISH
    PUBLISH --> DB
```

- API: auth, tenant scope, CRUD, approvals, connections and webhooks.
- Content worker: optional AI-assisted drafting from user-provided context.
- Publish worker: idempotent provider calls and external reconciliation.
- Scheduler: enqueues due work; it never performs slow provider calls inline.

## Frontend features

```text
dashboard       actionable channel/content/conversation health
media           reusable source assets
content         draft, edit, review and approve
calendar        schedule and publish status
inbox           messages, comments, reviews and explicit replies
connections     OAuth lifecycle and channel health
team            workspace roles and membership
activity        auditable action history
reports         concise publishing and conversation counts
billing         SaaS plan and invoices
```

## Core invariants

1. Every business query is scoped by `workspace_id`.
2. Content is reviewed before publication.
3. Every reply, including an approved FAQ suggestion, requires a person to send it.
4. External success requires provider confirmation.
5. Duplicate webhooks and publish commands are idempotent.
6. Ambiguous publish outcomes stop and enter reconciliation.
7. Fake providers and mock models are local-only.
8. Actions and failures are traceable in the audit log.

## Scope boundary

Havi manages social operations. It does not implement business goals, sales
pipelines, POS, inventory, delivery, full CRM, video editing or direct ad spend.
Havi is positioned as an AI secretary, not an autonomous marketer. Today AI
drafts content inside typed workflows; deterministic policies prioritize work,
and provider side effects remain role-gated and human-approved. The exact
shipping boundary is in [PRODUCT_CONTRACT.md](../product/PRODUCT_CONTRACT.md).

For state models and API routes, see [TECHNICAL_SPEC.md](TECHNICAL_SPEC.md). For
the product boundary and channel sequence, see
[ROADMAP.md](../product/ROADMAP.md).
