# Roadmap — GDG TUM Build Arena

Where the project stands and what is planned next. Implementation details for
the completed phases live in [`ARCHITECTURE.md`](ARCHITECTURE.md),
[`backend/README.md`](../backend/README.md) and
[`frontend/README.md`](../frontend/README.md).

> **Current phase: Phase 2 complete. Phase 3 — verification and hardening — is
> next.** The v1 scope is feature-complete and runs locally, but it has not been
> deployed and live GitHub OAuth has not been exercised with real credentials.

## Phase overview

| Phase | Scope | State |
| --- | --- | --- |
| 1 | Backend API and evaluation platform | ✅ Complete |
| 2 | Student SPA and staff console | ✅ Complete |
| 3 | Verification and hardening | ⏭ Next |
| 4 | Staging and production launch | Planned |
| 5 | Scale and product enhancements | Later (candidates) |

---

## Phase 1 — Backend platform ✅

**Delivered**

- FastAPI service under `/api/v1` — 35 paths / 37 operations, documented at
  `/docs` and `/redoc`.
- PostgreSQL schema (8 tables) managed by Alembic; migrations, constraints and
  indexes are tested.
- GitHub OAuth with `state` + PKCE, database-backed sessions (only token hashes
  stored), cookie sessions plus Bearer clients, CSRF double-submit, CORS
  allowlist and Origin checks.
- Metadata-only evaluation engine with 11 check types, partial credit,
  required-check gating, per-user cooldowns/attempt caps and an
  `EvaluationExecutor` seam for a future queue worker.
- Best-attempt-per-challenge leaderboard with score overrides, disqualification,
  deterministic tie-breaks and per-track filters.
- Data-driven badge catalogue with idempotent automatic awarding and manual
  grants.
- Moderation and admin API (roles, user status, scores, badges) with a sanitized
  audit trail.
- 209 pytest tests, Ruff lint/format, Dockerfile and Docker Compose, health and
  readiness probes.

**Exit criteria — met:** the API runs locally against PostgreSQL, the test suite
and lint pass, and the full API contract is exercised by tests with the GitHub
transport mocked.

## Phase 2 — Frontend application ✅

**Delivered**

- React 19 + TypeScript SPA built with Vite 8, styled with Tailwind CSS v4
  tokens, routed with React Router 8 and code-split per route.
- 20 route entries (19 paths + the wildcard 404) covering the student journey
  and the staff console.
- Typed API client for the whole backend contract: cookie sessions, CSRF
  mirroring, normalized error envelopes, React Query caching and polling.
- Dark-first design system with a full light theme, responsive layouts, loading
  skeletons, empty/error states, toasts and Radix-based accessible primitives.
- Challenge authoring with the complete evaluation editor (11 check types) and
  explicit preserve/replace semantics.
- Moderation console (disqualify, reinstate, override scores, force re-runs),
  user/role/status management, badge CRUD and the admin audit log.
- 37 Vitest tests plus a local Playwright smoke run across the major routes,
  including a real submission POST, its auto-triggered evaluation and live
  repository-metadata reads from the public GitHub API.

**Exit criteria — met locally:** backend + seeded database + Vite dev server run
together; the smoke run produced no console or page errors. The smoke script is
not committed and is not part of CI.

## Phase 3 — Verification and hardening ⏭ next

**Goal:** prove the platform against real infrastructure and make the checks
repeatable.

### 3.1 Live GitHub OAuth

The OAuth flow has only run against the mocked transport in the test suite.
**Work**

- Create a GitHub OAuth App for staging and configure `GITHUB_CLIENT_ID`,
  `GITHUB_CLIENT_SECRET`, `BACKEND_BASE_URL`, `FRONTEND_ORIGINS` and
  `FRONTEND_AUTH_REDIRECT_URL`.
- Verify consent, denial, state mismatch, callback redirect, session
  persistence, logout, deactivation and role bootstrap.
- Replace the “unverified” status in the README and this roadmap with the
  observed result.

**Done when:** a real GitHub account signs in on the staging URL, a reload keeps
the session, logout and deactivation revoke it, and the documented error paths
behave as described.

### 3.2 Committed end-to-end suite and CI

The Playwright smoke run was a local, uncommitted script.
**Work**

- Add a Playwright project to the repository with a disposable seeded database
  and a cookie-bootstrap helper (never real tokens).
- Cover anonymous browsing, the sign-in boundary, submission → auto-evaluation →
  results, staff moderation and challenge authoring.
- Add CI for backend (`pytest`, Ruff), frontend (`vitest`, oxlint, Prettier,
  `tsc -b`, build) and the end-to-end suite; upload traces/screenshots on
  failure.

**Done when:** CI is green on `main` and required for merges. Unit and API tests
keep the GitHub transport mocked; any live-GitHub check is explicit and opt-in.

### 3.3 Browser and security hardening

**Work**

- Serve the SPA over HTTPS with a Content-Security-Policy and standard security
  headers; allow GitHub avatar images explicitly.
- Decide the cookie/hosting topology. The API issues `SameSite=Lax` session and
  CSRF cookies, so the SPA and API should share a site (for example
  `app.example.org` + `api.example.org`). A truly cross-site deployment needs a
  backend cookie-configuration change.
- Run a dependency audit and an accessibility pass (keyboard, focus, contrast,
  reduced motion).
- Verify rate limits and `X-Forwarded-For` handling behind the chosen proxy.

**Done when:** CSP is enforced on staging, no high-severity audit findings
remain, the accessibility review is recorded, and proxy/IP behavior is verified.

### 3.4 Observability

**Work**

- Error tracking for the SPA and API, request-ID propagation in logs and error
  reports, alerting on `/ready` failures and error-rate spikes.
- Confirm log redaction and retention settings.

**Done when:** a staged failure is traceable end-to-end and basic alerts are
configured.

## Phase 4 — Staging and production launch

**Work**

- Provision managed PostgreSQL, the API service (Docker or native Python) and a
  static host for the SPA; run migrations as a release step.
- Configure environment variables and secrets per environment; register OAuth
  apps for staging and production; bootstrap the first admins.
- Set up database backups and perform a restore drill; define retention.
- Write the operations runbook: deploy, rollback, migration recovery, incident
  handling and a launch smoke checklist.
- Launch on a custom domain with TLS and monitoring.

**Done when:** staging mirrors production, a production deploy passes the smoke
checklist, and backup + rollback procedures have been tested.

## Phase 5 — Scale and product enhancements (candidates)

These require product decisions and are not committed to a date.

- Queue-backed `EvaluationExecutor` with a worker process; the status model
  already includes `queued`.
- Redis-backed rate limiting for multi-instance deployments.
- Notifications (email or in-app) for evaluation results and badge awards.
- Manual-review check types and CSV/PDF exports.
- Dedicated catalogue facets endpoint and server-side faceting for larger
  catalogues.
- Private-repository evaluation with a deliberately scoped GitHub token.
- Organization/multi-tenant isolation if the programme expands beyond GDG TUM.

## Explicit non-goals (v1)

- Executing or sandboxing student code.
- Server-side rendering.
- Email/password authentication or built-in 2FA.
- Mobile applications.
- Multi-tenant or per-organization isolation.

## Open decisions

| Decision | Owner | Needed by |
| --- | --- | --- |
| License | Project owner | Before public reuse |
| Hosting provider, domain and TLS | Project owner | Phase 4 |
| GitHub OAuth App ownership | Organization/admin | Phase 3 |
| Data retention and moderation policy | Organizers | Phase 4 |
| Which Phase 5 items are in scope | Product owner | After launch |
