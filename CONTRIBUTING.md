# Contributing to GDG TUM Build Arena

Thanks for helping build the platform. The project is a FastAPI + PostgreSQL
backend and a React single-page frontend, both in this repository and both in
scope for contributions. The current phase and planned work are tracked in the
[roadmap](docs/ROADMAP.md).

## Development setup

The fastest backend path is Docker Compose from the repository root:

```bash
cp backend/.env.example .env    # optional — add GitHub OAuth credentials
docker compose up --build
```

For a plain-Python setup (needed to run the backend test suite), see
[Local setup](backend/README.md#local-setup-no-docker) in the backend guide.

Run the frontend against the API in a second terminal:

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173, /api proxied to the backend
```

If the API is not on `http://localhost:8000`, set `VITE_API_PROXY_TARGET`. See
[`frontend/README.md`](frontend/README.md) for configuration details.

## Before you open a pull request

CI runs the same checks on every push to `main` and on every pull request, and
status checks are required before a pull request can be merged — see
[`.github/workflows/ci.yml`](.github/workflows/ci.yml). Run them locally before
pushing.

Backend (from `backend/`):

```bash
.venv/bin/pytest            # requires TEST_DATABASE_URL (and optionally TEST_MIGRATION_DATABASE_URL)
.venv/bin/ruff check app tests scripts migrations
.venv/bin/ruff format --check app tests scripts migrations
```

Frontend (from `frontend/`):

```bash
npm test              # Vitest + Testing Library
npm run lint          # oxlint
npm run format:check  # Prettier
npm run typecheck     # tsc -b (strict)
npm run build         # typecheck + production bundle
```

End-to-end (from `e2e/`; requires PostgreSQL plus the backend virtualenv and the
frontend dependencies):

```bash
npm run seed  # create + migrate + seed the disposable buildarena_e2e database
npm test      # Playwright starts the API, SPA and mock GitHub API on dedicated ports
```

If you changed models or migrations, also verify migration health against a
**disposable** database:

```bash
.venv/bin/alembic upgrade head
.venv/bin/alembic check
```

Never run migration experiments against a database that contains real data.

## Workflow

1. Branch from `main` using a descriptive name (`feat/submission-filters`,
   `fix/leaderboard-tie-break`, `docs/oauth-setup`).
2. Make focused commits. This project uses [Conventional
   Commits](https://www.conventionalcommits.org/) style prefixes:
   `feat:`, `fix:`, `docs:`, `test:`, `chore:`, `ci:`, `refactor:`.
   Example: `feat: cap submissions per challenge per day`.
3. Open a pull request describing **what** changed and **why**; link related
   issues. Keep unrelated changes out of the same PR.
4. Do not force-push shared branches and do not rewrite published history.

## Where things live

| Area | Location |
| --- | --- |
| HTTP routes | `backend/app/api/v1/` (one module per resource) |
| Business rules | `backend/app/services/` |
| Database queries | `backend/app/repositories/` |
| Models / enums | `backend/app/models/` |
| Request/response schemas | `backend/app/schemas/` |
| Evaluation checks | `backend/app/evaluation/` |
| GitHub integration | `backend/app/integrations/github.py` |
| Backend tests | `backend/tests/` (fixtures in `conftest.py`, data builders in `factories.py`) |
| Migrations | `backend/migrations/versions/` |
| Operational scripts | `backend/scripts/` |
| SPA entry / routes | `frontend/src/App.tsx` and `frontend/src/pages/` |
| API client and types | `frontend/src/lib/api.ts`, `frontend/src/api/` |
| Shared components | `frontend/src/components/` (ui, common, domain, layout) |
| Frontend hooks | `frontend/src/hooks/` |
| Design tokens and styles | `frontend/src/styles/globals.css` |
| Frontend tests | `frontend/src/**/*.test.ts(x)` and `frontend/src/test/setup.ts` |
| End-to-end suite | `e2e/` (specs in `e2e/tests/`, fixtures in `e2e/support/`, mock GitHub API in `e2e/scripts/`) |
| CI workflows | `.github/workflows/ci.yml` |

## Code style

Backend:

- Ruff enforces lint and formatting (line length 100); run it before pushing.
- SQLAlchemy 2.x style with explicit types; FastAPI handlers are synchronous
  `def` functions backed by the synchronous SQLAlchemy session.
- Prefer small service functions with explicit parameters over hidden globals;
  keep HTTP concerns in routers and SQL out of them.
- New behavior needs tests. Use the existing fixtures and factories; tests run
  against a disposable PostgreSQL database and must not touch the network
  (GitHub calls are mocked).

Frontend:

- TypeScript is strict; keep `frontend/src/api/types.ts` in sync with the
  backend Pydantic schemas.
- Use design-token classes (`bg-surface`, `text-ink`, `border-line`, …) rather
  than raw colours so both themes keep working.
- Follow the existing React Query patterns (query-key factory, typed API
  modules) instead of ad-hoc fetches; all HTTP goes through `src/lib/api.ts`.
- oxlint and Prettier are enforced; new interactive primitives should be
  keyboard-accessible and covered where practical.

End-to-end:

- Prefer durable assertions (URLs, badges, counters) over toast timing; the
  suite runs one worker against a single seeded database, in file order.
- `e2e/support/env.ts` mirrors the seed data in
  `backend/scripts/seed_e2e.py`; keep both in sync when fixtures change. The
  mock GitHub fixture (`e2e/scripts/mock-github.mjs`) must keep satisfying the
  seeded challenge's checks.

## Documentation

Documentation is part of the deliverable. When behaviour or project status
changes, update the relevant file:

- [`README.md`](README.md) — status, capabilities, quick starts.
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — phases, next work and acceptance
  criteria; move items between phases as they land.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — components, flows, data model.
- [`docs/SECURITY.md`](docs/SECURITY.md) — controls and limitations.
- [`backend/README.md`](backend/README.md) / [`frontend/README.md`](frontend/README.md)
  — area-specific setup and reference material.

Do not describe unverified behaviour as implemented. Mark status explicitly.

## Security

- Never commit real credentials, tokens, `.env` files or database dumps.
  Fixtures may contain obvious fake tokens only.
- Only non-secret `VITE_*` values belong in frontend configuration — the built
  bundle is public.
- Report vulnerabilities privately — see [`docs/SECURITY.md`](docs/SECURITY.md).
- Privileged actions must be audited (`audit_logs`) and authorization checks
  must follow the existing role/ownership patterns.

## License

The project license is not yet decided (see the root
[`README.md`](README.md#license)). Until the owner selects a license,
contributions are accepted at the maintainers' discretion and the code should
not be redistributed outside the project.
