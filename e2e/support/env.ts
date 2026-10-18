/**
 * Shared constants for the end-to-end suite.
 *
 * Keep the seeded identifiers in sync with `backend/scripts/seed_e2e.py` and
 * the canned repository in `scripts/mock-github.mjs`.
 */

export const BASE_URL = process.env.E2E_BASE_URL ?? "http://127.0.0.1:5174";
export const BACKEND_URL = process.env.E2E_BACKEND_URL ?? "http://127.0.0.1:8002";
export const MOCK_GITHUB_URL = process.env.E2E_MOCK_GITHUB_URL ?? "http://127.0.0.1:8990";

/** Host-only cookie domain derived from the frontend origin. */
export const COOKIE_DOMAIN = new URL(BASE_URL).hostname;

export const SESSION_COOKIE = "ba_session";
export const CSRF_COOKIE = "ba_csrf";

/** Repository served by scripts/mock-github.mjs — every seeded check passes on it. */
export const MOCK_REPO_URL = "https://github.com/e2e-labs/cloud-notes";

/** Published challenge whose checks pass completely against the mock repository. */
export const SEEDED_CHALLENGE = {
  slug: "cloud-notes-platform",
  title: "Cloud Notes Platform",
} as const;

/** Draft challenge that must stay invisible to anonymous visitors. */
export const SEEDED_DRAFT_CHALLENGE = {
  slug: "lab-telemetry-pipeline",
  title: "Lab Telemetry Pipeline",
} as const;

export const SEEDED_STUDENT = {
  username: "e2e-aisha",
  displayName: "Aisha Khan",
} as const;

export const SEEDED_STUDENT2 = {
  username: "e2e-ben",
  displayName: "Ben Müller",
} as const;

/** Full score the seeded challenge awards for MOCK_REPO_URL. */
export const EXPECTED_SCORE = { awarded: 100, max: 100 } as const;
