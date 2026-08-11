# Repository Strategy and Future Split Plan — Havi

This technical note accompanies the design handoff and guides codebase
initialization.

## MVP Decision

```text
Repository model:    Monorepo
Frontend/backend:    Logically separated, same repository
Deployment:          Independent per app/process
Database ownership:  Backend only
Secrets ownership:   Backend and infrastructure only
API contract:        OpenAPI
Future split method: git subtree split
Manual file copying: Not allowed
```

Architectural boundaries exist from day one. Repository splitting should happen
only when team structure, security, ownership, or deployment cadence makes it
necessary.

## Initial Structure

```text
havi-platform/
├── apps/
│   ├── web/              # Next.js frontend
│   └── backend/
│       ├── api/          # FastAPI entrypoint
│       ├── worker/       # Celery worker entrypoint
│       ├── scheduler/    # Celery Beat entrypoint
│       ├── core/         # Transitional core utilities
│       └── migrations/   # Alembic migrations
├── packages/
├── contracts/
├── infrastructure/
├── docs/
└── docker-compose.yml
```

## 1. Separation Principles

Frontend and backend are independent applications even while they share a repo.
The only runtime communication path is HTTP:

```text
Next.js frontend
        ↓ HTTPS / OpenAPI
FastAPI backend
```

The frontend must not:

- import backend Python code
- access PostgreSQL/Redis directly
- contain database credentials, OAuth secrets, LLM keys, production prompts, or
  encryption keys
- depend on backend private file paths

Use the generated API client:

```typescript
import { apiClient } from "@/lib/api-client";
```

The backend exposes OpenAPI at `/openapi.json`; the frontend generates TypeScript
types/client code from that contract.

## 2. Independent Deployment

Recommended workflow split:

```text
.github/workflows/
├── deploy-web.yml
├── deploy-api.yml
├── deploy-worker.yml
└── deploy-scheduler.yml
```

Deployment ownership:

- `apps/web` changes deploy only the frontend.
- `apps/backend/api` changes deploy only the API.
- `apps/backend/worker` changes deploy only the worker.
- `apps/backend/scheduler` changes deploy only beat/scheduler.
- Database migrations are controlled separately.

Example deployment targets:

```text
apps/web               -> Cloudflare/Vercel/etc.
apps/backend/api       -> Railway/AWS/Fly/etc.
apps/backend/worker    -> Railway/AWS/Fly/etc.
apps/backend/scheduler -> Railway/AWS/Fly/etc.
```

## 3. Environment Variable Boundaries

Frontend:

```env
NEXT_PUBLIC_API_URL=https://api.example.com
NEXT_PUBLIC_MEDIA_URL=https://media.example.com
```

Backend:

```env
DATABASE_URL=
REDIS_URL=
OPENAI_API_KEY=
FACEBOOK_CLIENT_SECRET=
GOOGLE_CLIENT_SECRET=
ZALO_CLIENT_SECRET=
TOKEN_ENCRYPTION_KEY=
```

Never expose backend secrets to the frontend runtime.

## 4. When to Split Repositories

Do not split repositories just to look more mature. Split only when one or more
of these are true:

- frontend and backend teams work independently
- release cadences differ significantly
- monorepo CI/CD becomes too slow or difficult
- code access must differ by team
- backend source contains higher-protection IP
- background processing has grown into a separate system
- ownership and on-call boundaries diverge
- the monorepo causes clear bottlenecks

## 5. Split Method

Do not copy files manually. Use `git subtree split`.

Frontend:

```bash
git subtree split --prefix=apps/web -b split-web
git remote add web-repo <NEW_FRONTEND_REPOSITORY_URL>
git push web-repo split-web:main
```

Backend:

```bash
git subtree split --prefix=apps/backend -b split-backend
git remote add backend-repo <NEW_BACKEND_REPOSITORY_URL>
git push backend-repo split-backend:main
```

Infrastructure:

```bash
git subtree split --prefix=infrastructure -b split-infrastructure
git remote add infrastructure-repo <NEW_INFRASTRUCTURE_REPOSITORY_URL>
git push infrastructure-repo split-infrastructure:main
```

The new repo contains only that directory and the relevant commit history.

## 6. Do Not Remove Monorepo Code Immediately

Before deleting the moved directory from the monorepo:

```text
[ ] New repo can be cloned
[ ] Application builds
[ ] Tests pass
[ ] Environment variables are configured
[ ] CI/CD works
[ ] Deployment works
[ ] API contract works
[ ] Shared dependencies are handled
[ ] Secrets did not move to the wrong repo
```

Only then:

```bash
git rm -r apps/web
git commit -m "chore: move frontend to separate repository"
git push
```

## 7. Update After Splitting

Review CI/CD workflows, Docker build context, environment variables, deployment
configuration, README files, API URLs, CORS, shared dependencies, OpenAPI client
generation, versioning, release process, branch protection, repository
permissions, secret configuration, and local-development instructions.

## 8. Shared Packages

Do not share business logic between frontend and backend packages. Across the
frontend/backend boundary, share only contracts:

```text
OpenAPI schema
Generated TypeScript API client
JSON schema
Event schema
Public enums
```

```text
Backend is the source of truth.
```

After a repo split, choose one strategy for `packages/generated-api-client`:

1. Generate the client in frontend CI from an OpenAPI URL.
2. Publish a private package.
3. Commit generated client code to the frontend repo.

For MVP, prefer option 1.

## 9. Target Structure After Full Split

```text
havi-frontend
havi-backend
havi-infrastructure
```

The backend repository should still contain API, worker, and scheduler because
they share domain logic. Split the worker only when ownership or release cadence
becomes genuinely independent.

## 10. Design Responsibility Map

| Design area | Owning app/process |
|---|---|
| Landing page, auth UI, onboarding, main app | `apps/web` |
| Auth, content CRUD, approval, connected accounts | `apps/backend/api` |
| AI content generation, listening, reply drafting | `apps/backend/worker` |
| Scheduled publishing, CRM reminders | `apps/backend/scheduler` |

Mandatory Havi constraints:

- Production prompts live in the backend, never in the frontend bundle.
- The approval state machine belongs to the backend.
- Platform tokens are encrypted with `TOKEN_ENCRYPTION_KEY` and decrypted only by
  the backend.
