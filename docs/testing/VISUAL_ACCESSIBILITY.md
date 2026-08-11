# Visual Regression and Accessibility Baseline

> Documentation language: English. Product UI/customer-facing copy remains
> Vietnamese because the target users are Vietnamese small-business owners.

This baseline covers the major web routes across desktop and mobile viewports.
It uses Playwright screenshots plus axe smoke checks. API responses are mocked
inside the browser test, so the backend does not need to run.

The axe smoke check currently disables `color-contrast`. Existing palette
contrast gaps are tracked as a separate UI hardening follow-up because the first
baseline should catch structural regressions in labels, landmarks, controls, and
ARIA state without forcing a broad color redesign in the same change.

## Covered Routes

- `/gioi-thieu`
- `/dang-nhap`
- `/`
- `/noi-dung`
- `/lich-dang`
- `/bao-cao`
- `/cai-dat`
- `/noi-bo/van-hanh`

## Local Commands

Install browser binaries once:

```bash
cd apps/web
npx playwright install chromium
```

Run the baseline:

```bash
npm run test:visual
```

When a local Next dev server is already running, reuse it instead of starting a
second server:

```bash
PLAYWRIGHT_SKIP_WEBSERVER=1 PLAYWRIGHT_BASE_URL=http://localhost:3000 npm run test:visual
```

Update screenshots intentionally after a reviewed UI change:

```bash
npm run test:visual -- --update-snapshots
```

## CI Behavior

The `Web Checks` job installs Chromium and runs:

```bash
npm run test:visual
```

The Playwright config starts `next dev` on port `3100`, uses mocked API
responses, and runs both `desktop` and `mobile` projects.

## Review Rules

- Treat screenshot diffs as UI changes that need review, not as snapshots to
  update automatically.
- Keep route data deterministic; do not depend on local database contents.
- Add a new covered route when a new primary workflow is added to the app shell.
- Accessibility failures should be fixed in UI code unless the violation is a
  documented false positive.
