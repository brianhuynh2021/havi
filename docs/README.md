# Docs Index

Documentation in `docs/` is grouped by audience and purpose:

- [`handoff/`](handoff/) — design-to-implementation handoff, [DEPLOYMENT.md](handoff/DEPLOYMENT.md), and [CREDENTIALS_AND_SECRETS_GUIDE.md](handoff/CREDENTIALS_AND_SECRETS_GUIDE.md)
- [`product/`](product/) — roadmap, product direction, and [COMMERCIALIZATION_PHASES.md](product/COMMERCIALIZATION_PHASES.md)
- [`architecture/`](architecture/) — technical spec, repository strategy, and
  architecture decisions
- [`operations/`](operations/) — dogfooding, external beta launch, Facebook App
  Review, and [BETA_READINESS_REVIEW.md](operations/BETA_READINESS_REVIEW.md)
- [`security/`](security/) — security review checklists and release gates
- [`testing/`](testing/) — visual regression and accessibility baselines

Setting up staging or production? Start with
[`handoff/DEPLOYMENT.md`](handoff/DEPLOYMENT.md). It captures the operational
details that are not obvious from code: local-only fake modes, Facebook Developer
setup order, quota/rate-limit behavior, required processes, and silent failure
modes.

Preparing founder beta? Read
[`security/SECURITY_REVIEW.md`](security/SECURITY_REVIEW.md) before inviting
users.

About to charge a real customer? Read
[`operations/BETA_READINESS_REVIEW.md`](operations/BETA_READINESS_REVIEW.md)
first. It records the verified state of the tree, the P0 defects that block
payment, the test protocol, and the paid-beta gate.

Canonical deployment architecture:
[`architecture/SYSTEM_ARCHITECTURE.md`](architecture/SYSTEM_ARCHITECTURE.md).

Add new documentation to the correct group instead of growing root-level docs.
