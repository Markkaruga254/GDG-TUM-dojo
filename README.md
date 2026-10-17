# GDG TUM Build Arena

**Build. Ship. Prove.**

Competitive developer-learning and portfolio platform run by **Google Developer
Groups on Campus — Technical University of Mombasa (GDG TUM)**. Students
discover engineering challenges, submit a GitHub repository for each challenge,
receive an automated evaluation, earn points and badges, and compete on public
leaderboards while building a verifiable portfolio.

> **Project status — v1 feature-complete; verification and deployment are next.**
> The FastAPI/PostgreSQL API and the React single-page app are implemented,
> tested and documented, and they have been exercised together locally. What
> remains before a public launch: live GitHub OAuth with real credentials, a
> committed end-to-end suite and CI, a staging → production deployment, and the
> license decision. The phase-by-phase plan lives in
> [`docs/ROADMAP.md`](docs/ROADMAP.md); current limitations are listed
> [below](#known-limitations).

## Current status

**Phase 2 of 5 complete — the platform is feature-complete for its v1 scope.
Phase 3 (verification and hardening) is next.**

| Area | State | Notes |
| --- | --- | --- |
| Backend API | ✅ Complete | FastAPI + PostgreSQL; 35 paths / 37 operations; evaluation engine, leaderboard and badge policies, audit trail |
| Frontend SPA | ✅ Complete | React 19 + Vite; 20 route entries covering the student flows and the staff console; dark/light themes |
| Automated tests | ✅ Passing | 209 backend pytest tests · 37 frontend Vitest tests |
| Local full-stack run | ✅ Verified | Cookie session + CSRF, submission → auto-evaluation → results, staff moderation; all major routes exercised in a Playwright smoke run |
| Live GitHub OAuth | ⚠️ Unverified | Exercised only against the mocked transport; no real OAuth app credentials yet |
| Live GitHub metadata | ✅ Exercised locally | Repository checks ran against the public GitHub API in the local smoke run; not yet exercised from a deployment |
| CI pipeline | ⛔ Not started | Checks currently run locally |
| Staging / production | ⛔ Not started | Deployment topology and the Render guide are documented, but unexercised |
| License | ⛔ Undecided | Owner decision required |

Planned work, acceptance criteria and explicit non-goals are in
[`docs/ROADMAP.md`](docs/ROADMAP.md).

## Intended users

- **Students / builders** — browse the challenge catalogue, submit project
  repositories, track scores, badges and leaderboard position.
- **Moderators / track leads** — curate challenges, review submissions, run and
  re-run evaluations.
- **Organizers / admins** — manage roles, scores, badges, platform settings and
  the audit trail.

## Key capabilities

| Area | What the platform provides |
| --- | --- |
| Authentication | GitHub OAuth (`state` + PKCE), database-backed sessions (only token hashes stored), HttpOnly cookies, CSRF double-submit protection, roles `student` → `moderator` → `admin` |
| Challenges | Draft → published → archived lifecycle, tracks, difficulty, schedules, validated per-challenge evaluation configs |
| Submissions | Public repository URL + evidence links, duplicate detection, per-user cooldown and daily attempt caps, owner/staff-only visibility |
| Evaluation | Metadata-only checks (README, files, directories, commits, license, languages), partial credit, required-check gating, idempotent triggers, staff re-runs, full audit trail |
| Scoring | Best-attempt-per-challenge policy, admin score overrides, disqualification support, deterministic tie-breaks |
| Leaderboard | Overall and per-track rankings plus a personal rank summary |
| Badges | Seeded catalogue, data-driven server-side rules, idempotent auto-awarding, manual grants |
| Admin | User roles and status, submission moderation, score overrides, badge management, audit log |
| Operations | Alembic migrations, `/health` + `/ready` probes, structured logs with redaction, rate limiting, Docker + Docker Compose, pytest suite, Ruff |

**Student code is never executed.** Evaluations read public GitHub repository
metadata through the GitHub REST API; the application never clones or runs
submitted code.

### Frontend experience

The single-page app in [`frontend/`](frontend/README.md) covers the full student
journey and the staff console:

- **Students** — landing page, challenge catalogue with search, track/difficulty/
  tag filters and pagination, challenge detail, the submission flow with repo
  validation, evaluation results with a per-check breakdown, personal submission
  history, leaderboards, the badge case, public profiles and profile settings.
- **Staff (moderator/admin)** — console with overview metrics, challenge
  authoring including the full evaluation-config editor, submission moderation
  (disqualify, reinstate, score overrides, forced re-runs), user/role/status
  management, badge management and the audit log.
- **UX** — dark-first theme with a light mode toggle, responsive layout down to
  mobile widths, skeleton loading states, toast feedback and accessible dialogs
  and menus built on Radix primitives.

## Architecture

The backend is a single FastAPI service that keeps all state in PostgreSQL and
talks to GitHub for OAuth and repository metadata. The frontend is a Vite +
React single-page app that consumes the API over cookie-based sessions and holds
no business logic of its own. Evaluations run behind an `EvaluationExecutor`
seam: the shipped implementation is synchronous, so no Redis or worker process
is required for v1 (a queue-backed executor can be added later without
changing the API).

```mermaid
flowchart LR
    spa["Students & staff<br/>React SPA — frontend/"] --> middleware
    clients["API clients<br/>(curl, scripts)"] --> middleware

    subgraph api["FastAPI service — /api/v1"]
        middleware["Middleware<br/>CORS · CSRF · rate limits · error envelope"]
        routers["Routers<br/>health · auth · users · challenges · submissions · leaderboard · badges · admin"]
        services["Services<br/>auth · submissions · evaluation · leaderboard · badges · admin · audit"]
        database[("PostgreSQL<br/>SQLAlchemy 2.x · Alembic")]
        middleware --> routers --> services --> database
    end

    services -- "OAuth exchange · repo metadata reads<br/>(student code never executed)" --> github["GitHub<br/>OAuth + REST API"]
```

Detailed component breakdowns, request flows and the data model live in
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md); the security design is in
[`docs/SECURITY.md`](docs/SECURITY.md).

## Repository structure

```
cloud-track-dojo/
├── backend/                 # FastAPI service — see backend/README.md
│   ├── app/                 # api/v1, core, db, evaluation, integrations, models, repositories, schemas, services
│   ├── migrations/          # Alembic environment + revisions
│   ├── scripts/             # seed_badges, promote_admin
│   ├── tests/               # pytest suite (real PostgreSQL, mocked GitHub)
│   ├── Dockerfile           # production image (unprivileged user, healthcheck)
│   ├── pyproject.toml       # dependencies, Ruff and pytest configuration
│   └── .env.example         # configuration template (placeholders only)
├── frontend/                # React SPA — see frontend/README.md
│   ├── src/                 # api, components, hooks, lib, pages, styles, test
│   ├── public/              # favicon
│   ├── index.html           # entry document + pre-paint theme bootstrap
│   ├── package.json         # scripts: dev, build, lint, format, typecheck, test
│   └── .env.example         # API base URL / dev proxy target
├── docs/
│   ├── ARCHITECTURE.md      # components, flows, data model, deployment topology
│   ├── ROADMAP.md           # current phase, next work, acceptance criteria, non-goals
│   └── SECURITY.md          # security model, secret handling, vulnerability reporting
├── CONTRIBUTING.md
├── docker-compose.yml       # PostgreSQL + API for local development
└── README.md
```

## Technology stack

| Layer | Choice |
| --- | --- |
| Runtime | Python 3.12+ (project requires `>=3.12`) |
| API framework | FastAPI, served under `/api/v1` |
| Database | PostgreSQL 14+ (16 in Docker Compose), SQLAlchemy 2.x, Alembic migrations |
| Validation / config | Pydantic v2 + pydantic-settings |
| HTTP client | HTTPX (GitHub OAuth + REST API) |
| Tests | pytest + HTTPX TestClient, against a real disposable PostgreSQL database |
| Quality | Ruff (lint + format, line length 100) |
| Packaging | `pyproject.toml` (hatchling), editable install |
| Containerization | Docker / Docker Compose, Uvicorn |

Frontend (`frontend/`):

| Layer | Choice |
| --- | --- |
| Runtime | Node.js `^20.19` or `>=22.12` (Vite 8 requirement) |
| Framework | React 19 + TypeScript (strict), built with Vite 8 |
| Styling | Tailwind CSS v4 with CSS custom-property design tokens (dark-first + light theme) |
| Routing | React Router 8, route-level code splitting |
| Data fetching | TanStack Query v5 over a typed `fetch` client that mirrors the API contract |
| UI primitives | Radix UI (dialog, alert-dialog, dropdown-menu, tabs, tooltip), lucide-react icons, sonner toasts |
| Tests | Vitest + Testing Library (jsdom) |
| Quality | oxlint + Prettier |

## Prerequisites

- Python **3.12+**
- Node.js **`^20.19` or `>=22.12`** (Vite 8 requirement) + npm (for the frontend)
- PostgreSQL **14+** (16 recommended; Docker Compose runs 16)
- Docker + Docker Compose (optional — only for the containerized workflow)
- A GitHub OAuth App (only needed to exercise sign-in flows locally)

## Quick start (Docker Compose)

```bash
git clone <repository-url>
cd cloud-track-dojo

cp backend/.env.example .env      # optional: add GitHub OAuth credentials
docker compose up --build         # db → migrations + badge seed → API
```

- API: <http://localhost:8000> · Swagger UI: `/docs` · ReDoc: `/redoc`
- Liveness: <http://localhost:8000/health> · Readiness: <http://localhost:8000/ready>
- The `api` container applies migrations and seeds the badge catalogue on
  startup (development convenience — in production, run migrations as a
  separate release step).
- Port clashes are expected on developer machines; both ports are overridable:

  ```bash
  POSTGRES_PORT=5433 API_PORT=8001 docker compose up --build
  ```

## Quick start (plain Python)

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
cp .env.example .env            # set DATABASE_URL + GitHub OAuth values
.venv/bin/alembic upgrade head
.venv/bin/python -m scripts.seed_badges
.venv/bin/uvicorn app.main:app --reload
```

See [`backend/README.md`](backend/README.md) for the full setup guide.

## Quick start (frontend)

The SPA expects a running API (defaults to `http://localhost:8000`):

```bash
cd frontend
npm install
cp .env.example .env.local       # optional — see Configuration
npm run dev                      # http://localhost:5173, /api proxied to the API
```

Production build:

```bash
npm run build                    # typecheck + static bundle in frontend/dist/
npm run preview                  # serve the built bundle locally
```

When the API is not on `localhost:8000`, set `VITE_API_PROXY_TARGET` for the dev
server. For a deployed build, set `VITE_API_BASE_URL` to the API origin (leave
it empty when the SPA and API share an origin). See
[`frontend/README.md`](frontend/README.md) for the full guide.

## Configuration

Environment files are never committed; example files ship placeholders only:

- **repo root `.env`** — read by Docker Compose for `${VAR}` interpolation
  (optional; the compose file ships sensible development defaults);
- **`backend/.env`** — read by the application when running outside Docker
  (template: [`backend/.env.example`](backend/.env.example));
- **`frontend/.env.local`** — optional build-time settings for the SPA
  (template: [`frontend/.env.example`](frontend/.env.example)).

All values in `.env.example` are placeholders; never commit a filled-in `.env`
(it is git-ignored). The most important variables:

| Variable | Purpose | Default |
| --- | --- | --- |
| `ENVIRONMENT` | `development` \| `test` \| `production` | `development` |
| `DATABASE_URL` | `postgresql+psycopg://user:pass@host:port/db` | local dev URL |
| `BACKEND_BASE_URL` | Public API URL; OAuth redirect-URI base | `http://localhost:8000` |
| `FRONTEND_ORIGINS` | Comma-separated CORS allowlist | `http://localhost:5173` |
| `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET` | GitHub OAuth app credentials | empty (auth endpoints return `503` until set) |
| `GITHUB_API_TOKEN` | Optional token raising GitHub API limits for evaluations | empty |
| `ADMIN_GITHUB_USERNAMES` | Usernames promoted to admin on first login | empty |
| `RATE_LIMIT_ENABLED` | Master switch for the in-process limiter | `true` |

The complete list with descriptions is in
[`backend/README.md#configuration`](backend/README.md#configuration) and
[`.env.example`](backend/.env.example).

## Database migrations and seeds

```bash
cd backend

# Apply migrations / inspect drift
.venv/bin/alembic upgrade head
.venv/bin/alembic check

# Seed the default badge catalogue (idempotent — safe to re-run)
.venv/bin/python -m scripts.seed_badges

# Promote an existing account (must have signed in at least once) to admin
.venv/bin/python -m scripts.promote_admin <github_username>
```

Never run migration experiments against a database containing real data; the
test suite uses explicitly disposable databases.

## Tests and quality checks

The suite requires two throwaway PostgreSQL databases (it creates, drops and
rolls back its own data):

```bash
cd backend
createdb buildarena_test
createdb buildarena_mig

TEST_DATABASE_URL=postgresql+psycopg://user:pass@127.0.0.1:5432/buildarena_test \
TEST_MIGRATION_DATABASE_URL=postgresql+psycopg://user:pass@127.0.0.1:5432/buildarena_mig \
.venv/bin/pytest

.venv/bin/ruff check app tests scripts migrations
.venv/bin/ruff format --check app tests scripts migrations
```

- GitHub API calls are mocked in tests — the suite never touches the network.
- Migration tests (`tests/test_migrations.py`) are skipped unless
  `TEST_MIGRATION_DATABASE_URL` is set.

Frontend (from `frontend/`):

```bash
npm test              # Vitest + Testing Library (jsdom)
npm run lint          # oxlint
npm run format:check  # Prettier
npm run typecheck     # tsc -b (strict)
npm run build         # typecheck + production bundle
```

### Verification snapshot

At the current commit, the following has been verified:

- **Backend** — 209 pytest tests pass against disposable PostgreSQL databases;
  Ruff lint and format are clean.
- **Frontend** — 37 Vitest tests pass; oxlint, Prettier, `tsc -b` and the
  production build are clean.
- **Local integration** — the backend, a seeded PostgreSQL database and the Vite
  dev server run together. A Playwright smoke run covered the major routes,
  created a real submission, observed its auto-triggered evaluation (including
  repository metadata read live from the public GitHub API) and reported no
  console or page errors. The smoke script is not committed and is not part of
  CI; see Phase 3 in the [roadmap](docs/ROADMAP.md).

## API overview

All endpoints are served under `/api/v1`, with built-in documentation:

- Swagger UI — `/docs`
- ReDoc — `/redoc`
- OpenAPI JSON — `/openapi.json` (35 paths / 37 operations in the current v1 API)

Errors use a machine-readable envelope
(`{"error": {"code", "message", "details"}}`) and list endpoints return
`{"items", "total", "page", "page_size", "pages"}`. Endpoint groups (details and
examples in [`backend/README.md#api-overview`](backend/README.md#api-overview)):

| Group | Examples | Access |
| --- | --- | --- |
| Health | `GET /health`, `GET /ready`, `GET /api/v1/health` | public |
| Auth | `GET /auth/github/login`, `GET /auth/github/callback`, `GET /auth/me`, `POST /auth/logout` | public / session |
| Users | `GET/PATCH /users/me`, `GET /users/{username}/profile`, `GET /users/{username}/portfolio` | session / public |
| Challenges | `GET /challenges`, `GET /challenges/{slug}`, staff create/update/publish/archive | public reads / staff writes |
| Submissions | create, list mine, detail, results, `POST /submissions/{id}/evaluate` | owner or staff |
| Leaderboard | `GET /leaderboard`, `GET /leaderboard/me` | public / session |
| Badges | `GET /badges`, `GET /users/{username}/badges` | public |
| Admin | roles, user status, moderation, score overrides, badges, audit logs | moderator / admin |

## Project documentation

- [`backend/README.md`](backend/README.md) — complete backend guide (setup,
  configuration, migrations, OAuth, API, evaluation/leaderboard policies, rate
  limits, operations, deployment, troubleshooting).
- [`frontend/README.md`](frontend/README.md) — frontend guide (setup, scripts,
  project structure, design system, API client and auth notes, testing).
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — full-stack components,
  request flows, frontend architecture, data model, deployment topology,
  extension points.
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — current phase, Phase 3–5 work,
  acceptance criteria, non-goals and open decisions.
- [`docs/SECURITY.md`](docs/SECURITY.md) — API and client-side security model,
  secret handling and vulnerability reporting.
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — contribution workflow and checks.

## Known limitations

Current limitations (v1 scope — documented deliberately rather than hidden):

- **No CI pipeline or committed end-to-end suite yet**: backend tests and
  frontend unit tests run locally, and end-to-end verification was a one-off
  local Playwright smoke run (the script is not committed).
- **Evaluations are synchronous** in the API process (`SynchronousExecutor`
  behind an `EvaluationExecutor` seam — queue-ready, but no worker is shipped).
- **The rate limiter is in-process** and therefore per instance/worker; apply
  platform-level limits when scaling horizontally.
- **Live GitHub OAuth is not yet verified**: sign-in has only run against the
  mocked transport in the test suite, never with real OAuth app credentials.
  Repository metadata reads against the public GitHub API *have* been exercised
  locally (including a real evaluation), but not in a deployed environment.
- Private repositories are not read; evaluations expect public repositories (a
  `GITHUB_API_TOKEN` can raise API rate limits but grants no extra access in
  the v1 flow).
- **No Content-Security-Policy yet.** The API sends baseline security headers
  (nosniff, frame denial, referrer and permissions policies), but the SPA host
  must add CSP/HSTS. Session cookies are `SameSite=Lax`, so the SPA and API
  should share a site unless the backend cookie configuration is extended.
- Manual-review check types and CSV/PDF exports are out of scope.
- No staging or production deployment exists yet.

## Roadmap

Phase-by-phase scope, acceptance criteria and explicit non-goals live in
[`docs/ROADMAP.md`](docs/ROADMAP.md). In short:

| Phase | Focus | State |
| --- | --- | --- |
| 1 | Backend API, evaluation, leaderboard, badges, audit | ✅ Done |
| 2 | Student SPA and staff console | ✅ Done |
| 3 | Live OAuth, committed E2E + CI, browser/security hardening, observability | ⏭ Next |
| 4 | Staging → production launch: managed PostgreSQL, static SPA, OAuth apps, backups, runbook | Planned |
| 5 | Queue-backed evaluation, Redis rate limiting, notifications, manual review, exports, catalogue facets | Later (candidates) |

Immediate next actions (Phase 3):

1. Create a GitHub OAuth App and verify login, logout and session revocation on
   a staging URL.
2. Commit the Playwright end-to-end suite and wire backend + frontend checks
   into CI.
3. Add CSP/security headers at the hosting layer, then run accessibility and
   dependency audits.

## Security notes

- OAuth `state` + PKCE, hashed session tokens, HttpOnly cookies, CSRF
  double-submit, CORS allowlist, rate limits and redacted logs are built in —
  see [`docs/SECURITY.md`](docs/SECURITY.md).
- Never commit real credentials. `.env` files are git-ignored; `.env.example`
  contains placeholders only.
- Student code is never executed and repositories are never cloned; only public
  GitHub metadata is read.
- Report vulnerabilities privately; do not open public issues for security
  reports (process in [`docs/SECURITY.md`](docs/SECURITY.md)).

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). In short: branch from `main`, keep
changes focused, run the test and lint commands above, and open a pull request.

## License

No license has been chosen yet — this is flagged for the project owner. Until a
license is added, default copyright rules apply: contact the maintainers before
reusing the code outside this project.
