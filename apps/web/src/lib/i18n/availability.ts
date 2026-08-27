/**
 * English is deliberately unavailable until every core workflow is translated.
 *
 * Keep this as a literal boolean: `scripts/i18n-audit.mjs` reads the same flag,
 * so the UI and release check cannot disagree about whether English is shipped.
 */
export const ENGLISH_UI_ENABLED = false as const;
