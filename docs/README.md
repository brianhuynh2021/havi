# Docs Index

Documentation in `docs/` is grouped by audience and purpose:

- [`handoff/`](handoff/) — design-to-implementation handoff and
  [DEPLOYMENT.md](handoff/DEPLOYMENT.md)
- [`product/`](product/) — roadmap and product direction
- [`architecture/`](architecture/) — technical spec, repository strategy, and
  architecture decisions

Setting up staging or production? Start with
[`handoff/DEPLOYMENT.md`](handoff/DEPLOYMENT.md). It captures the operational
details that are not obvious from code: local-only fake modes, Facebook Developer
setup order, quota/rate-limit behavior, required processes, and silent failure
modes.

Canonical deployment architecture:
[`architecture/SYSTEM_ARCHITECTURE.md`](architecture/SYSTEM_ARCHITECTURE.md).

Add new documentation to the correct group instead of growing root-level docs.
