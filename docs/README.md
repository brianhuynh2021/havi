# Docs Index

Documentation in `docs/` is grouped by audience and purpose:

- [`handoff/`](handoff/) — [DEPLOYMENT.md](handoff/DEPLOYMENT.md) and [CREDENTIALS_AND_SECRETS_GUIDE.md](handoff/CREDENTIALS_AND_SECRETS_GUIDE.md)
- [`product/`](product/) — [ROADMAP.md](product/ROADMAP.md),
  [PRODUCT_CONTRACT.md](product/PRODUCT_CONTRACT.md) and
  [COMMERCIALIZATION_PHASES.md](product/COMMERCIALIZATION_PHASES.md)
- [`architecture/`](architecture/) —
  [SYSTEM_ARCHITECTURE.md](architecture/SYSTEM_ARCHITECTURE.md),
  [TECHNICAL_SPEC.md](architecture/TECHNICAL_SPEC.md),
  [REPOSITORY_STRATEGY.md](architecture/REPOSITORY_STRATEGY.md) and
  [VIDEO_PIPELINE.md](architecture/VIDEO_PIPELINE.md)
- [`operations/`](operations/) —
  [EXTERNAL_BETA_LAUNCH.md](operations/EXTERNAL_BETA_LAUNCH.md),
  [DOGFOODING_PLAN.md](operations/DOGFOODING_PLAN.md) and
  [FACEBOOK_APP_REVIEW.md](operations/FACEBOOK_APP_REVIEW.md)
- [`security/`](security/) — [SECURITY_REVIEW.md](security/SECURITY_REVIEW.md)
  and [DATA_RETENTION_AND_CONSENT.md](security/DATA_RETENTION_AND_CONSENT.md)
- [`testing/`](testing/) —
  [VISUAL_ACCESSIBILITY.md](testing/VISUAL_ACCESSIBILITY.md)
- [BRAND_GUIDELINES.md](BRAND_GUIDELINES.md) — brand voice and visual identity

Setting up staging or production? Start with
[`handoff/DEPLOYMENT.md`](handoff/DEPLOYMENT.md). It captures the operational
details that are not obvious from code: local-only fake modes, Facebook Developer
setup order, quota/rate-limit behavior, required processes, and silent failure
modes.

Preparing founder beta? Read
[`security/SECURITY_REVIEW.md`](security/SECURITY_REVIEW.md) before inviting
users — and check its staleness banner first. It was last run on 2026-08-11 and
names the request surfaces added since that have not had a security pass.

**[`product/PRODUCT_CONTRACT.md`](product/PRODUCT_CONTRACT.md) is the single
source of truth** for what Havi is, the nine things that are the product, and
what may be claimed to customers. If any other document disagrees with it, the
contract wins and the other document is the bug.

[`product/ROADMAP.md`](product/ROADMAP.md) holds future direction (§1b vision,
§1c paid-promotion boundary, §2 delivery sequence). Everything there that is not
in the contract's "Shipped and claimable now" list is future work and must be
labelled as such.

Canonical deployment architecture:
[`architecture/SYSTEM_ARCHITECTURE.md`](architecture/SYSTEM_ARCHITECTURE.md).

Add new documentation to the correct group instead of growing root-level docs.
