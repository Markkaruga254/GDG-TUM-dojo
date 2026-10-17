# GDG TUM Build Arena

**Build. Ship. Prove.**

Competitive developer-learning and portfolio platform run by **Google Developer
Groups on Campus — Technical University of Mombasa (GDG TUM)**. Students
discover engineering challenges, submit a GitHub repository for each challenge,
receive an automated evaluation, earn points and badges, and compete on public
leaderboards while building a verifiable portfolio.

> **Project status: active development — backend MVP.**
> The FastAPI/PostgreSQL backend in this repository is implemented, tested and
> documented. The frontend has not been started; GitHub OAuth has been exercised
> end-to-end only against a mocked GitHub transport in the test suite, not yet
> against live GitHub credentials; and no production or staging deployment
> exists yet. See [Known limitations and next steps](#known-limitations-and-next-steps).

## Intended users

- **Students / builders** — browse the challenge catalogue, submit project
  repositories, track scores, badges and leaderboard position.
- **Moderators / track leads** — curate challenges, review submissions, run and
  re-run evaluations.
- **Organizers / admins** — manage roles, scores, badges, platform settings and
  the audit trail.

## Key capabilities

| Area | What the backend MVP provides |
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

## Architecture

The backend is a single FastAPI service that keeps all state in PostgreSQL and
talks to GitHub for OAuth and repository metadata. Evaluations run behind an
`EvaluationExecutor` seam: the shipped implementation is synchronous, so no
Redis or worker process is required for the MVP (a queue-backed executor can be
added later without changing the API).

```mermaid
flowchart LR
    student["Students & staff<br/>(browser)"] --> middleware
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
├── docs/
│   ├── ARCHITECTURE.md      # components, flows, data model, deployment topology
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

## Prerequisites

- Python **3.12+**
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

## Configuration

Two `.env` files are used, both starting from
[`backend/.env.example`](backend/.env.example):

- **repo root `.env`** — read by Docker Compose for `${VAR}` interpolation
  (optional; the compose file ships sensible development defaults);
- **`backend/.env`** — read by the application when running outside Docker.

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

## API overview

All endpoints are served under `/api/v1`, with built-in documentation:

- Swagger UI — `/docs`
- ReDoc — `/redoc`
- OpenAPI JSON — `/openapi.json` (35 paths / 37 operations in the current MVP)

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
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — components, request flows,
  data model, deployment topology, extension points.
- [`docs/SECURITY.md`](docs/SECURITY.md) — security model, secret handling and
  vulnerability reporting.
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — contribution workflow and checks.

## Known limitations and next steps

Current limitations (MVP scope — documented deliberately rather than hidden):

- **No frontend** yet; the API is usable via its OpenAPI docs, curl or scripts.
- **Evaluations are synchronous** in the API process (`SynchronousExecutor`
  behind an `EvaluationExecutor` seam — queue-ready, but no worker is shipped).
- **The rate limiter is in-process** and therefore per instance/worker; apply
  platform-level limits when scaling horizontally.
- **Live GitHub integration is not yet verified** outside the mocked tests:
  OAuth against real credentials and repository metadata through the live
  GitHub API have not been exercised in a deployed environment.
- Private repositories are not read; evaluations expect public repositories (a
  `GITHUB_API_TOKEN` can raise API rate limits but grants no extra access in
  the MVP flow).
- Manual-review check types and CSV/PDF exports are out of scope.
- No staging or production deployment exists yet.

Next milestones (not yet implemented):

1. Build the frontend and connect it to these APIs (CORS allowlist and cookie
   flows are already prepared).
2. Verify live GitHub OAuth (real OAuth app credentials) end-to-end.
3. Deploy a staging environment (Render or equivalent) with release-step
   migrations, then production.
4. Add a background worker/queue behind the executor seam and Redis-backed rate
   limiting if scale requires it.

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
