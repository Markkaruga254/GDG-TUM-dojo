# GDG TUM Build Arena — Backend

Production-minded FastAPI backend for **GDG TUM Build Arena**, a competitive
developer-learning and portfolio platform run by Google Developer Groups on
Campus at the Technical University of Mombasa.

Students authenticate with GitHub, publish a project repository per challenge,
and receive an automated, metadata-only evaluation with a public leaderboard and
badges. This service is the API behind the React single-page app in
[`frontend/`](../frontend/README.md); the current phase and next work are in the
[project roadmap](../docs/ROADMAP.md).

- **API**: FastAPI, served under `/api/v1` (OpenAPI docs at `/docs`)
- **Data**: PostgreSQL + SQLAlchemy 2.x + Alembic migrations
- **Validation/config**: Pydantic v2 + pydantic-settings
- **Tests**: pytest + HTTPX against a real PostgreSQL database
- **Lint**: Ruff (checks + formatting)

No Redis, worker or queue is required for v1: evaluations run behind an
`EvaluationExecutor` seam (synchronous implementation shipped; a queue-backed
implementation can be dropped in without touching the API — see
[Evaluation architecture](#evaluation-architecture)).

Related documentation: [architecture](../docs/ARCHITECTURE.md) ·
[security](../docs/SECURITY.md) · [roadmap](../docs/ROADMAP.md) ·
[contributing](../CONTRIBUTING.md).

---

## Table of contents

1. [Requirements](#requirements)
2. [Local setup (no Docker)](#local-setup-no-docker)
3. [Docker Compose](#docker-compose)
4. [Configuration](#configuration)
5. [Migrations](#migrations)
6. [Running the tests](#running-the-tests)
7. [GitHub OAuth setup](#github-oauth-setup)
8. [API overview](#api-overview)
9. [Scoring and evaluation](#scoring-and-evaluation)
10. [Leaderboard policy](#leaderboard-policy)
11. [Badges](#badges)
12. [Rate limiting](#rate-limiting)
13. [Security model](#security-model)
14. [Operations (scripts, health, audit)](#operations)
15. [Troubleshooting](#troubleshooting)
16. [Deployment (Render)](#deployment-render)
17. [Project layout](#project-layout)
18. [Known limitations](#known-limitations)
19. [License](#license)

---

## Requirements

- Python **3.12+**
- PostgreSQL **14+** (16 recommended)
- Optional: Docker + Docker Compose for the containerized stack

## Local setup (no Docker)

```bash
cd backend

# 1. Virtualenv + dependencies (editable install, includes dev tools)
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"

# 2. Configuration
cp .env.example .env
#    → set DATABASE_URL and the GitHub OAuth values
#    Local development example ONLY (replace credentials/port as needed):
#    postgresql+psycopg://buildarena:buildarena@127.0.0.1:5432/buildarena

# 3. Database (any PostgreSQL instance you control)
createdb buildarena          # or: psql -c "CREATE DATABASE buildarena"

# 4. Schema + default badge catalogue
.venv/bin/alembic upgrade head
.venv/bin/python -m scripts.seed_badges

# 5. Serve
.venv/bin/uvicorn app.main:app --reload --port 8000
```

Then open <http://localhost:8000/docs>.

## Docker Compose

From the repository root:

```bash
cp backend/.env.example .env     # optional; compose fills sensible defaults
docker compose up --build        # starts db → runs migrations + seeds → serves API
```

The API is exposed on <http://localhost:8000> (docs at `/docs`). The stack:

- `db` — PostgreSQL 16 with a named volume and `pg_isready` healthcheck;
- `api` — the image built from `backend/Dockerfile`; its start command runs
  `alembic upgrade head`, seeds the badge catalogue, then starts uvicorn.

`POSTGRES_PORT` (default `5432`) is overridable so an existing local PostgreSQL
never conflicts:

```bash
POSTGRES_PORT=5433 docker compose up --build
```

> In production, migrations should be a separate release step (see
> [Deployment](#deployment-render)) rather than part of the container start
> command.

## Configuration

All settings come from environment variables (and an optional `.env`), defined
in `app/core/config.py` and documented in [`.env.example`](.env.example).
The values shown there — including the database credentials
`buildarena`/`buildarena` — are **local development examples only**. Highlights:

| Variable | Purpose | Default |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql+psycopg://user:pass@host:port/db` | local dev URL |
| `ENVIRONMENT` | `development` \| `test` \| `production` | `development` |
| `BACKEND_BASE_URL` | Public API URL; builds the OAuth redirect URI | `http://localhost:8000` |
| `FRONTEND_ORIGINS` | Comma-separated CORS allowlist (credentials) | `http://localhost:5173` |
| `FRONTEND_AUTH_REDIRECT_URL` | Browser target after OAuth callback | `http://localhost:5173/auth/callback` |
| `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET` | GitHub OAuth app credentials | empty (auth disabled with a clear 503) |
| `GITHUB_API_TOKEN` | Optional server-side token raising the GitHub API rate limit for evaluations | empty |
| `ADMIN_GITHUB_USERNAMES` | Comma-separated usernames promoted to admin on first login | empty |
| `SESSION_TTL_HOURS` | Session lifetime | `168` |
| `SESSION_COOKIE_SECURE` | `Secure` cookie flag; defaults to `true` when `ENVIRONMENT=production` | derived |
| `RATE_LIMIT_ENABLED` | Master switch for the in-process limiter | `true` |
| `AUTH_RATE_LIMIT_PER_MINUTE` | Login/callback attempts per IP per minute | `30` |
| `SUBMISSION_RATE_LIMIT_PER_HOUR` | Submission creations per IP per hour | `30` |
| `SUBMISSION_COOLDOWN_SECONDS` | Minimum seconds between a user's attempts on one challenge | `30` |
| `MAX_SUBMISSIONS_PER_CHALLENGE_PER_DAY` | Per-user daily attempt cap per challenge | `10` |
| `MAX_EVIDENCE_URLS` | Evidence links accepted per submission | `5` |
| `EVALUATOR_VERSION` | Recorded on every evaluation result | `1.0.0` |

`Settings` validates *production* configuration at startup and refuses unsafe
combinations (debug mode, insecure cookies, wildcard CORS origins, missing
OAuth credentials).

## Migrations

Alembic lives in `migrations/`. The database URL is resolved, in order, from:

1. `alembic -x db_url=...` (one-off runs and tests),
2. the `DATABASE_URL` environment variable,
3. application settings (`.env`).

```bash
.venv/bin/alembic upgrade head          # apply
.venv/bin/alembic downgrade base        # full rollback (safe, tested)
.venv/bin/alembic check                 # drift check against the models
.venv/bin/alembic revision --autogenerate -m "describe change"
```

The initial migration (`b3eafbacb03b`) defines all eight tables
(`users`, `auth_sessions`, `challenges`, `submissions`, `evaluations`,
`badges`, `user_badges`, `audit_logs`) with UUID primary keys, foreign keys,
CHECK constraints for enum-like columns, and the indexes used by the
leaderboard and moderation queries.

> `alembic revision` runs `ruff format` on the generated file (configured as a
> post-write hook), so run it through the project virtualenv.

## Running the tests

Tests need a **disposable PostgreSQL database** (they create and drop tables
themselves) — at least two databases if you also want the migration tests:

```bash
cd backend
createdb buildarena_test
createdb buildarena_mig

TEST_DATABASE_URL=postgresql+psycopg://user:pass@127.0.0.1:5432/buildarena_test \
TEST_MIGRATION_DATABASE_URL=postgresql+psycopg://user:pass@127.0.0.1:5432/buildarena_mig \
.venv/bin/pytest
```

- `TEST_DATABASE_URL` — the main schema, created via `Base.metadata`.
- `TEST_MIGRATION_DATABASE_URL` — a second database used only by
  `tests/test_migrations.py`, which runs `alembic upgrade head`, compares the
  migrated schema with the models (`compare_metadata`, the automated
  equivalent of `alembic check`) and verifies `downgrade base`. The module is
  skipped when the variable is unset.

Each test runs inside a transaction that is rolled back afterwards, so tests
are isolated without truncation. Suites cover models/constraints, migrations,
auth (OAuth + sessions + CSRF), users, challenges, submissions, the evaluation
API (idempotency, partial credit, errors, badges), leaderboard, badges, admin,
and security middleware.

Lint and format:

```bash
.venv/bin/ruff check app tests scripts migrations
.venv/bin/ruff format --check app tests scripts migrations
```

## GitHub OAuth setup

1. Go to **GitHub → Settings → Developer settings → OAuth Apps → New OAuth App**.
2. **Authorization callback URL**:
   `https://<your-api-host>/api/v1/auth/github/callback`
   (locally: `http://localhost:8000/api/v1/auth/github/callback`).
3. Copy the client ID/secret into `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET`.
4. Set `BACKEND_BASE_URL` to the public API URL so the redirect URI matches.

Flow: `GET /api/v1/auth/github/login` redirects to GitHub with an OAuth
`state` and a PKCE `code_challenge`; both are also stored in short-lived
HttpOnly cookies. The callback validates the state cookie (constant-time
compare), exchanges the code **with the PKCE verifier**, reads the user's
GitHub identity once, and immediately discards the GitHub token — it is never
persisted or exposed. A database-backed session token is then issued as an
HttpOnly cookie (hashed at rest) together with a readable CSRF cookie.

> **Verification status.** The automated suite drives the complete OAuth flow
> against a mocked GitHub transport and never calls github.com; exercising the
> live flow requires real OAuth app credentials and a callback URL reachable by
> GitHub, which has not been verified yet (see
> [Known limitations](#known-limitations)).

API clients (CLI/scripts) may alternatively send
`Authorization: Bearer <session-token>`; browsers use cookies + CSRF.

Roles: `student` → `moderator` → `admin`. Bootstrap the first admins with
`ADMIN_GITHUB_USERNAMES=alice,bob` (applied on first login) or explicitly via
`python -m scripts.promote_admin <github_username>`.

## API overview

All endpoints live under `/api/v1`. Errors always use a machine-readable
envelope:

```json
{"error": {"code": "validation_error", "message": "...", "details": [{"field": "body.repo_url", "reason": "..."}]}}
```

List endpoints return a page envelope:
`{"items": [...], "total": n, "page": 1, "page_size": 20, "pages": 1}`.

| Area | Examples | Access |
| --- | --- | --- |
| Health | `GET /health`, `GET /ready`, `GET /api/v1/health` | public |
| Auth | `GET /auth/github/login`, `GET /auth/github/callback`, `GET /auth/me`, `POST /auth/logout` | public / session |
| Users | `GET/PATCH /users/me`, `GET /users/{username}/profile`, `GET /users/{username}/portfolio` | session / public |
| Challenges | `GET /challenges`, `GET /challenges/{slug}`, `POST/PATCH /challenges...`, `POST .../publish`, `POST .../archive` | public reads / staff writes |
| Submissions | `POST /challenges/{id}/submissions`, `GET /users/me/submissions`, `GET /submissions/{id}`, `GET /submissions/{id}/results`, `POST /submissions/{id}/evaluate` | owner or staff |
| Leaderboard | `GET /leaderboard`, `GET /leaderboard/me` | public / session |
| Badges | `GET /badges`, `GET /users/{username}/badges` | public |
| Admin | user role/status, submission disqualify/reinstate/score, badges, audit logs | moderator / admin |

Ownership rules: submission detail and results are visible to the owner and to
staff only; other students receive `404` (existence is not leaked). Draft
challenges are invisible to non-staff. Every privileged mutation is written to
`audit_logs` (actor, action, target, metadata; sensitive keys are stripped).

## Scoring and evaluation

Evaluations are **metadata-only**: the engine inspects repository metadata
through the GitHub API (existence, visibility, files, README, commits, license,
languages) — **student code is never executed** in the API process, and the
application never clones repositories.

A challenge carries a validated `evaluation_config`: a list of checks, each
with `id`, `type`, points, `required` flag and optional params. Max points must
cover the sum of check points.

Supported check types: `repo_accessible`, `repo_public`, `required_files`,
`required_directories`, `readme_present`, `readme_sections`,
`readme_min_length`, `evidence_links`, `min_commits`, `license_present`,
`language_present`.

Statuses and scoring:

- Every check lands in `passed` / `partial` / `failed` / `skipped` / `error`;
  checks whose criteria can be partially satisfied (required files or
  directories, README sections, README length, required languages) award
  proportional credit.
- **Partial credit**: awarded score is the sum of passed check points (capped
  at the challenge maximum).
- **Required checks gate the outcome**: if any required check did not pass,
  the submission is `failed` even with points awarded.
- If a check *errors* (GitHub unavailable etc.) the evaluation and submission
  are marked `error`, contribute **0 points**, and are excluded from the
  leaderboard; staff can re-run them.
- Each evaluation stores its result set, feedback, summary, and the
  `EVALUATOR_VERSION` used.
- Multiple attempts are allowed (subject to cooldown + daily cap); each run is
  recorded as a separate `evaluations` row, `evaluation_attempts` is
  incremented on the submission, and only the best attempt counts for the
  leaderboard (see below).

### Submission lifecycle

- `pending` — created and not yet evaluated.
- `queued` / `running` — evaluation in flight. `queued` is produced by a future
  queue-backed executor; the shipped synchronous executor moves submissions
  straight to `running`.
- `passed` / `failed` — final results; the only statuses counted by the
  leaderboard (failed attempts with partial credit still count).
- `error` — infrastructure failure (for example GitHub unavailable):
  contributes 0 points, is excluded from the leaderboard and is retryable by
  staff.

Concurrent triggers are safe: the atomic claim returns `202` for an in-flight
submission instead of re-running it, and staff can force a re-run of a final
result with `?force=true` (audited).

### Evaluation architecture

`POST /submissions/{id}/evaluate` is **idempotent**: a submission that is
already final returns `202` without re-running. Staff may pass `?force=true`
to re-evaluate (audited as `submission.force_evaluate`).

The engine is split so that the API does not depend on *how* evaluation runs:

- `EvaluationService` owns the state machine
  (pending → running → passed/failed/error) and the audit trail;
- `EvaluationExecutor` is the seam. The shipped `SynchronousExecutor` runs the
  evaluation inline (single-process v1). A queue/worker deployment only needs
  a new executor implementation; the claim step in the repository uses an
  atomic `UPDATE ... WHERE status IN (...)` so concurrent triggers cannot
  double-run an evaluation.

External GitHub calls go through `GitHubClient` (cached per-request, bounded
retries, timeouts); tests inject a mocked transport, so the suite never talks
to the network.

## Leaderboard policy

Multiple attempts per challenge are allowed, but the leaderboard counts at
most one result per (user, challenge):

1. **Best effective score wins.** For each pair, the counted result is the
   attempt with the highest *effective* score, where the effective score is the
   admin **score override** if present, otherwise the awarded points.
2. **Ineligible results are excluded**: disqualified submissions, evaluations
   that errored, and results without a final `evaluated_at`. Failed-but-scored
   attempts (partial credit) *do* count.
3. **Challenge status**: `draft` challenges never count; `published` and
   `archived` challenges keep their points.
4. **Inactive users** (deactivated accounts) are excluded entirely.
5. A user's totals are the sum of counted results; `completed_challenges`
   counts counted results with a positive score.
6. **Tie-breaks**, in order: higher total points → more completed challenges →
   earlier `achieved_at` (the most recent `evaluated_at` among counted results)
   → user id.
7. `GET /leaderboard?track=...` filters counted results to one track;
   `GET /leaderboard/me` returns the caller's rank, totals and per-challenge
   entries (optionally track-filtered).

This policy is implemented in `app/repositories/leaderboard.py`
(`best_scores_cte`) and covered by the leaderboard test module.

## Badges

Five default badges are seeded by `python -m scripts.seed_badges`
(idempotent): `first-submission`, `first-challenge`, `five-challenges`,
`ten-challenges`, `perfect-build`. Rules are data
(`submissions_finalized`, `challenges_passed`, `perfect_scores`,
`track_challenges_passed`) validated by `BadgeCriteria` and evaluated
server-side only, never from client input.

Automatic awarding happens after each successful evaluation and is idempotent
(`ON CONFLICT DO NOTHING` on `(user_id, badge_id)`): the same final results
always award the same badge set exactly once. Staff can additionally grant
badges manually via the admin API (audited).

## Rate limiting

v1 uses an **in-process sliding-window limiter**
(`app/core/ratelimit.py`) keyed by client IP + scope:

- auth endpoints per minute (`AUTH_RATE_LIMIT_PER_MINUTE`, default 30);
- submission creation per hour (`SUBMISSION_RATE_LIMIT_PER_HOUR`, default 30);
- evaluation triggers per hour (`EVALUATION_RATE_LIMIT_PER_HOUR`, default 60);
- plus per-user challenge rules: cooldown between attempts and a daily cap.

Rejections return `429` with `{"details": [{"retry_after_seconds": n}]}` and a
`Retry-After` hint. Client IP resolution honors `X-Forwarded-For` only when
`TRUST_PROXY_HEADERS=true` (enable it behind a trusted proxy such as Render —
otherwise the header is ignored to prevent spoofing).

**Multi-instance caveat**: an in-process limiter is per worker. When running
more than one instance or worker, also apply limits at the platform level
(Render / reverse proxy / WAF); the limiter can then be swapped for a
Redis-backed implementation behind the same interface.

## Security model

- GitHub OAuth with `state` + PKCE; state and verifier in short-lived HttpOnly
  cookies; constant-time comparisons.
- Sessions are database-backed; only SHA-256 hashes of session tokens are
  stored. Logout and account deactivation revoke tokens immediately.
- Cookies: `HttpOnly`, `SameSite=Lax`, `Secure` (default in production).
- CSRF: double-submit token (`X-CSRF-Token` header must match the `ba_csrf`
  cookie) for cookie-authenticated mutating requests; Bearer clients are
  exempt; Origin checks reject disallowed browser origins.
- CORS: explicit origin allowlist with credentials; wildcards are rejected in
  production.
- No secrets in logs: structured logging redacts authorization/cookies/tokens,
  and audit metadata is sanitized (sensitive keys dropped, payloads capped).
- Every privileged or score-affecting action is written to the audit trail.
- Production configuration is validated at startup (debug off, secure cookies,
  no wildcard origins, OAuth configured). `ALLOWED_HOSTS` enables host-header
  enforcement.
- Student code is never executed by the API; evaluations only read GitHub
  metadata.

## Operations

```bash
# Seed/refresh the default badge catalogue (idempotent — safe to re-run)
.venv/bin/python -m scripts.seed_badges

# Promote an existing account (must have signed in at least once) to admin.
# Unknown usernames produce a clear error and no change.
.venv/bin/python -m scripts.promote_admin <github_username>
```

Probes: `GET /health` (liveness), `GET /ready` (readiness incl. database),
plus `GET /api/v1/health`. Admin audit trail: `GET /api/v1/admin/audit-logs`
(filter by `action`, paginated; admin-only).

## Troubleshooting

| Symptom | Likely cause / fix |
| --- | --- |
| `503` with `oauth_not_configured` from `/auth/github/login` | `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET` are not set — configure a GitHub OAuth App or skip auth-dependent flows. |
| `Redirect URI mismatch` at GitHub | `BACKEND_BASE_URL` must match the public URL registered as the OAuth callback (`<BACKEND_BASE_URL>/api/v1/auth/github/callback`). |
| Tests fail during setup/fixtures | `TEST_DATABASE_URL` is not set or does not point at a disposable PostgreSQL database — create `buildarena_test` (and optionally `buildarena_mig`) first. |
| `alembic revision` fails in its post-write hook | The hook runs `ruff format`; run Alembic through the project virtualenv (`.venv/bin/alembic`) so `ruff` is on `PATH`. |
| `docker compose up` port conflict | Something already listens on 5432 or 8000 — use `POSTGRES_PORT=5433 API_PORT=8001 docker compose up --build`. |
| `docker build` cannot reach PyPI | A Docker daemon DNS/network problem on the host; check the daemon's DNS configuration or network access. |
| `429` responses during manual testing | Rate limits are active (`RATE_LIMIT_ENABLED`); honor `Retry-After` or raise the limits locally. Behind a proxy, set `TRUST_PROXY_HEADERS=true` only if the proxy overwrites `X-Forwarded-For`. |
| CORS failures in the browser | `FRONTEND_ORIGINS` must contain the exact origin (scheme, host, port) of the frontend. |
| Session cookies not stored over plain HTTP | Set `SESSION_COOKIE_SECURE=false` for development; production requires HTTPS and defaults to secure cookies. |
| `alembic check` reports pending operations | Models and migrations drifted — generate a revision with `alembic revision --autogenerate` after reviewing the diff. |

## Deployment (Render)

The repository ships a production `Dockerfile` (unprivileged user, dependency
layers cached, healthcheck). Two supported approaches:

1. **Docker deploy**: point the service at `backend/Dockerfile`. Run
   `alembic upgrade head` as the release command, then serve.
2. **Native Python**: build
   `pip install .`, start
   `uvicorn app.main:app --host 0.0.0.0 --port $PORT`, release command
   `alembic upgrade head`.

Required environment variables: `DATABASE_URL` (Render PostgreSQL),
`BACKEND_BASE_URL`, `FRONTEND_ORIGINS`, `FRONTEND_AUTH_REDIRECT_URL`,
`GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, and `ENVIRONMENT=production`
(which turns on secure cookies and config validation). Recommended:
`GITHUB_API_TOKEN`, `TRUST_PROXY_HEADERS=true`, `ADMIN_GITHUB_USERNAMES`.

Health check path for Render: `/health`. If you scale beyond one instance,
apply platform-level rate limits (see [Rate limiting](#rate-limiting)) and run
a single release command for migrations.

## Project layout

```
backend/
├── app/
│   ├── api/v1/            # routers: health, auth, users, challenges, submissions, leaderboard, badges, admin
│   ├── core/              # config, errors, logging, security, rate limiting, middleware, dependencies
│   ├── db/                # engine/session, declarative base
│   ├── evaluation/        # check rules, GitHub probe, runner (scoring), executor seam
│   ├── integrations/      # GitHub OAuth + REST client (timeouts, retries, caching)
│   ├── models/            # SQLAlchemy models + enums
│   ├── repositories/      # query layer (incl. leaderboard aggregation)
│   ├── schemas/           # Pydantic request/response models
│   ├── services/          # auth, users, challenges, submissions, evaluation, leaderboard, badges, admin, audit
│   └── main.py            # app factory, middleware, error handlers
├── migrations/            # Alembic environment + revisions
├── scripts/               # seed_badges, seed_e2e, promote_admin
├── tests/                 # pytest suite (models, migrations, API, security)
├── Dockerfile
├── alembic.ini
├── pyproject.toml
└── .env.example
```

## Known limitations

- Evaluations run synchronously in the API process (`SynchronousExecutor`).
  The state machine and executor seam are queue-ready, but no worker is
  shipped — long GitHub API calls occupy the request.
- The in-process rate limiter is per instance (see above).
- Live GitHub OAuth is unverified: the flow has only run against the mocked
  transport used by the test suite. Repository metadata reads *have* been
  exercised locally against the public GitHub API — including a real
  evaluation — but not from a deployed environment.
- Private repositories are not read; evaluation expects public repositories
  unless a `GITHUB_API_TOKEN` with access is configured.
- Manual-review check types and CSV/PDF exports are out of scope for v1.

## License

No license has been chosen yet — flagged for the project owner (see the root
[`README.md`](../README.md#license)).
