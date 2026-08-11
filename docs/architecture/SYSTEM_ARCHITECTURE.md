# Havi System Architecture

This is the canonical MVP deployment architecture, derived from the architecture
prototype, repository strategy, and technical spec.

## 0. Engineering Principles

Havi starts from invariants and simple interfaces. The system should be modular,
testable, observable, and scaled only where bottlenecks are proven.

### Required Principles

1. **Simple first:** begin with a modular monolith, one PostgreSQL database, and
   one queue. Do not add microservices, event buses, or extra databases before
   evidence requires them.
2. **Clear boundaries:** each module owns inputs, outputs, data, and failure
   modes.
3. **One-way dependencies:** entrypoints depend on application services;
   application services depend on domain/ports; adapters implement ports.
4. **Single source of truth:** PostgreSQL owns business state. Redis owns
   queue/cache/short locks. Calendar and dashboard are projections.
5. **Invariants before workflow:** approval, tenant isolation, quota, and
   idempotency are enforced in backend services/domain logic.
6. **Deterministic and idempotent:** retrying with the same command/idempotency
   key must not create duplicate external side effects.
7. **Failure isolation:** one job/adapter failure must not collapse unrelated
   requests.
8. **Observability is a feature:** request/job correlation, structured logs,
   state transitions, latency, token usage, and error reasons must be traceable.
9. **Scale by bottleneck:** API is stateless, workers scale by queue depth, media
   lives in object storage.
10. **Test contracts and invariants:** prioritize tests around module boundaries,
    state machines, tenant isolation, adapter contracts, and E2E smoke flows.

### Dependency Rules

Frontend:

```text
app/routes
    ↓
features
    ↓
components/ui + lib/api-client
```

- `app/` handles routing, layout, metadata, and composition.
- Features should not import private code from other features.
- UI primitives do not call HTTP directly.
- Feature data layers use the generated API client.

Backend:

```text
api / worker / scheduler          entrypoints
              ↓
application services             orchestration + transaction boundary
              ↓
domain + ports                   rules, state machine, interfaces
              ↑
repositories / provider adapters PostgreSQL, Redis, LLM, Facebook, storage
```

- Domain code does not import FastAPI, Celery, SQLAlchemy, Redis SDKs, LLM SDKs,
  or platform SDKs.
- API, worker, and scheduler call the same application services.
- Repositories/adapters translate I/O and do not own business decisions.
- Every schema change goes through Alembic.

Target backend structure:

```text
apps/backend/
├── api/                         # FastAPI entrypoint + thin routers
├── worker/                      # Celery entrypoint
├── scheduler/                   # Beat entrypoint
├── application/
│   └── services/                # Use cases + transaction boundaries
├── domain/
│   ├── models/                  # Entities/value objects
│   ├── policies/                # Approval, quota, scheduling, routing
│   └── ports/                   # Repository/provider interfaces
├── adapters/
│   ├── persistence/             # PostgreSQL repositories
│   ├── storage/                 # S3-compatible storage
│   ├── llm/                     # Text model providers
│   ├── publishers/              # Facebook/fake publishers
│   └── oauth/                   # OAuth clients
├── migrations/
└── tests/
```

`core/` is transitional scaffolding. Code should move into `domain/` and
`application/` gradually as boundaries mature; no big-bang rewrite is required.

## 1. System Overview

```mermaid
flowchart LR
    subgraph INPUT["Input"]
        WEB["Web app<br/>media, text, approval"]
        SALES["Sales webhook"]
        LISTEN["Social listening crawler"]
    end

    subgraph EDGE["API boundary"]
        API["FastAPI<br/>auth, workspace, CRUD, approvals"]
    end

    subgraph CORE["Job-based core"]
        QUEUE["Redis / Job Queue"]
        MEDIA["Ingest & Media Pipeline"]
        PROFILE["Industry / Brand Profile"]
        CONTENT["Content Engine<br/>one call, many drafts"]
        CLASSIFY["Listening Classifier"]
        REPLY["Reply Drafter + CRM<br/>approval first"]
        SCHEDULER["Scheduler<br/>publish, retry, quota"]
        EVENT["event_log<br/>input, output, tokens, latency"]
    end

    subgraph DATA["Data"]
        POSTGRES[("PostgreSQL<br/>tenant scoped")]
        OBJECT[("Object Storage<br/>media assets")]
    end

    subgraph OUTPUT["Channel adapters"]
        META["Facebook / Instagram"]
        ZALO["Zalo OA / ZNS"]
        GOOGLE["Google Business"]
        VIDEO["TikTok / YouTube"]
        EMAIL["Email"]
    end

    WEB -->|HTTPS / OpenAPI| API
    SALES --> API
    LISTEN --> API
    API --> POSTGRES
    API --> OBJECT
    API --> QUEUE
    QUEUE --> MEDIA
    QUEUE --> CONTENT
    QUEUE --> CLASSIFY
    QUEUE --> REPLY
    QUEUE --> SCHEDULER
    PROFILE --> CONTENT
    PROFILE --> REPLY
    MEDIA --> OBJECT
    MEDIA --> POSTGRES
    CONTENT --> POSTGRES
    CLASSIFY --> REPLY
    REPLY --> POSTGRES
    SCHEDULER --> META
    SCHEDULER --> ZALO
    SCHEDULER --> GOOGLE
    SCHEDULER --> VIDEO
    SCHEDULER --> EMAIL
    MEDIA --> EVENT
    CONTENT --> EVENT
    CLASSIFY --> EVENT
    REPLY --> EVENT
    SCHEDULER --> EVENT
    EVENT --> POSTGRES
```

## 2. Frontend Architecture

The frontend uses Next.js App Router. Routes compose screens; features own
business-facing state and API calls.

```mermaid
flowchart TD
    ROUTES["src/app<br/>routes, layout, metadata"] --> SHELL["App Shell"]
    SHELL --> DASHBOARD["features/dashboard"]
    SHELL --> CONTENT_UI["features/content-creation"]
    SHELL --> CALENDAR_UI["features/calendar"]
    SHELL --> LEADS_UI["features/leads"]
    SHELL --> REPORT_UI["features/reports"]
    SHELL --> OPS_UI["features/operations"]

    DASHBOARD --> UI["components/ui"]
    CONTENT_UI --> UI
    CALENDAR_UI --> UI
    LEADS_UI --> UI
    REPORT_UI --> UI
    OPS_UI --> UI

    DASHBOARD --> CLIENT["Generated OpenAPI client"]
    CONTENT_UI --> CLIENT
    CALENDAR_UI --> CLIENT
    LEADS_UI --> CLIENT
    REPORT_UI --> CLIENT
    OPS_UI --> CLIENT
    CLIENT --> API["FastAPI"]
```

Target structure:

```text
apps/web/src/
├── app/                         # Routing, layouts, metadata
├── components/
│   ├── app-shell/
│   └── ui/
├── features/
│   ├── dashboard/
│   ├── content-creation/
│   ├── calendar/
│   ├── leads/
│   ├── reports/
│   └── operations/
├── lib/
│   ├── api-client/
│   └── auth/
└── app/globals.css
```

## 3. Content State Machine

```mermaid
stateDiagram-v2
    [*] --> draft
    draft --> pending_approval: AI creates draft
    pending_approval --> draft: owner edits or rejects
    pending_approval --> approved: owner approves
    approved --> scheduled: schedule selected
    scheduled --> publishing: scheduler claims job
    publishing --> published: adapter succeeds
    publishing --> failed: platform error
    failed --> publishing: bounded retry
    failed --> dead_letter: retry exhausted/permanent failure
```

The backend is authoritative for the state machine. The frontend renders state
and sends actions; it never owns platform tokens, production prompts, or secrets.

## 4. Frontend Implementation Order

1. Lock design tokens and App Shell.
2. Build each screen with static fixtures.
3. Add prototype interactions inside each feature.
4. Generate the TypeScript client from OpenAPI and replace fixtures with API
   calls.
5. Add loading, empty, error, permission, and retry states before end-to-end
   integration.

## 5. Multi-Provider AI Layer

Status: text content generation is implemented; video/media pipeline remains
future scope.

### 5.1 Provider Router

`adapters/llm/` implements a domain `LLMProviderPort` for Gemini, Anthropic, and
OpenAI. Domain code depends on the port and `ProviderRouter`, not SDKs.

Provider fallback reasons:

1. outage, rate limit, timeout, or transient provider error
2. cost routing by workspace/plan
3. output fails schema or banned-claims validation

Every provider attempt should be observable through `event_log`: provider tried,
failure kind, final provider, latency, and token usage.

### 5.2 Token-Saving Funnel

Do not call expensive models at every step:

```text
100% input -> rules/keywords (0 tokens)
   -> small subset requiring semantics -> cheap classifier
      -> small subset requiring strong generation -> multi-provider LLM
```

The Content Engine is the main P0 use of multi-provider routing because it is
token-expensive and directly visible to users.

### 5.3 Future Video/Image Pipeline

Future content studio scope:

```mermaid
flowchart TD
    UPLOAD["Upload video"] --> VU["Video Understanding port"]
    VU --> TR["Transcript Engine port"]
    TR --> EDIT["Edit Engine<br/>deterministic domain logic"]
    EDIT --> SEM["Narrow LLM sub-call<br/>schema constrained"]
    SEM --> EDIT
    EDIT --> PLAN["EditPlan.json"]
    PLAN --> RENDER["Renderer port<br/>FFmpeg / Remotion"]
    RENDER --> OUT["Final media_asset<br/>approval flow"]
```

Design notes:

- Video understanding and transcription are separate ports.
- The Edit Engine should be deterministic and auditable.
- LLM calls should be narrow and schema-constrained, not responsible for the
  entire edit plan.
- `EditPlan.json` is a domain contract between the edit engine and renderer.
- Rendered output becomes a new `media_asset` and follows the same approval flow.
- This is not P0 pilot scope and should have its own quota/compute guardrails.
