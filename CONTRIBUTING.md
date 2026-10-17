# Contributing to GDG TUM Build Arena

Thanks for helping build the platform. This project is in active development
and the backend MVP is the current focus — keep pull requests focused and small.

## Development setup

Follow [`backend/README.md`](backend/README.md). The fastest path is
Docker Compose from the repository root:

```bash
cp backend/.env.example .env    # optional — add GitHub OAuth credentials
docker compose up --build
```

For a plain-Python setup (needed to run the test suite), see
[Local setup](backend/README.md#local-setup-no-docker) in the backend guide.

## Before you open a pull request

Run the same checks CI would run (from `backend/`):

```bash
.venv/bin/pytest            # requires TEST_DATABASE_URL (and optionally TEST_MIGRATION_DATABASE_URL)
.venv/bin/ruff check app tests scripts migrations
.venv/bin/ruff format --check app tests scripts migrations
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
| Tests | `backend/tests/` (fixtures in `conftest.py`, data builders in `factories.py`) |
| Migrations | `backend/migrations/versions/` |
| Operational scripts | `backend/scripts/` |

## Code style

- Ruff enforces lint and formatting (line length 100); run it before pushing.
- SQLAlchemy 2.x style with explicit types; FastAPI handlers are synchronous
  `def` functions backed by the synchronous SQLAlchemy session.
- Prefer small service functions with explicit parameters over hidden globals;
  keep HTTP concerns in routers and SQL out of them.
- New behavior needs tests. Use the existing fixtures and factories; tests run
  against a disposable PostgreSQL database and must not touch the network
  (GitHub calls are mocked).

## Security

- Never commit real credentials, tokens, `.env` files or database dumps.
  Fixtures may contain obvious fake tokens only.
- Report vulnerabilities privately — see [`docs/SECURITY.md`](docs/SECURITY.md).
- Privileged actions must be audited (`audit_logs`) and authorization checks
  must follow the existing role/ownership patterns.

## License

The project license is not yet decided (see the root
[`README.md`](README.md#license)). Until the owner selects a license,
contributions are accepted at the maintainers' discretion and the code should
not be redistributed outside the project.
