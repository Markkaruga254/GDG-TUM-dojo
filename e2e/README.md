# Build Arena — end-to-end suite

Playwright drives the real stack — FastAPI backend, React frontend and a
disposable PostgreSQL database — on dedicated ports, so it never collides with
a running development server:

| Component                  | URL                           | Notes                               |
| -------------------------- | ----------------------------- | ----------------------------------- |
| Frontend (Vite dev server) | http://127.0.0.1:5174         | proxies `/api` to the backend       |
| Backend (FastAPI)          | http://127.0.0.1:8002         | `ENVIRONMENT=test`, rate limits off |
| Mock GitHub API            | http://127.0.0.1:8990         | canned repo `e2e-labs/cloud-notes`  |
| PostgreSQL                 | `buildarena_e2e` on port 5433 | disposable, reset by every seed     |

Evaluations run against the mock GitHub API (`scripts/mock-github.mjs`), so the
suite is deterministic and offline: the canned repository satisfies every check
of the seeded challenge, and the student submission is expected to score
100/100.

## Prerequisites

- Node 24+ and the frontend dependencies (`cd ../frontend && npm ci`);
- the backend virtualenv with dev dependencies
  (`cd ../backend && python -m venv .venv && .venv/bin/pip install -e ".[dev]"`);
- PostgreSQL reachable on port 5433 — the `buildarena_e2e` database is created
  on the first `npm run seed` (the role needs CREATEDB).

## First-time setup

```bash
cd e2e
npm ci
npx playwright install chromium   # once per machine
npm run seed                      # create + migrate + seed the disposable database
npm test
```

`npm run seed` is idempotent: it truncates the `*_e2e` database and reseeds
the deterministic fixtures (users, sessions, challenges, one evaluated
submission). Re-run it whenever a full run needs fresh state — the suite's
tests share one seeded database and run in order (01 → 04).

GitHub OAuth cannot run locally or in CI, so the seed mints session cookies
that the suite injects into the browser (`support/sessions.ts`). The tokens are
written to `.sessions.json` (gitignored) and never printed.

## What the suite covers

- `01-anonymous.spec.ts` — the catalogue excludes drafts, the challenge detail
  page, the sign-in boundary on protected routes, the leaderboard.
- `02-student-submission.spec.ts` — submission through the form, automatic
  evaluation against the mock GitHub API, the results page (100/100), My
  submissions, leaderboard credit.
- `03-staff-moderation.spec.ts` — the staff moderation queue, a forced
  evaluation re-run, disqualify with reason, reinstate.
- `04-staff-authoring.spec.ts` — create a challenge, verify the draft is
  invisible to anonymous visitors, publish it, verify the public page.

## Commands

| Command                                       | Purpose                                           |
| --------------------------------------------- | ------------------------------------------------- |
| `npm run seed`                                | create + migrate + seed the disposable database   |
| `npm test`                                    | run the suite headless (starts all three servers) |
| `npm run test:headed`                         | watch the suite with a visible browser            |
| `npm run report`                              | open the HTML report of the last run              |
| `npm run lint` / `format:check` / `typecheck` | static checks                                     |

## Environment overrides

| Variable              | Default                                                                    | Purpose                                      |
| --------------------- | -------------------------------------------------------------------------- | -------------------------------------------- |
| `E2E_DATABASE_URL`    | `postgresql+psycopg://buildarena:buildarena@127.0.0.1:5433/buildarena_e2e` | disposable database                          |
| `E2E_SESSIONS_FILE`   | `e2e/.sessions.json`                                                       | where seeded session tokens are written/read |
| `E2E_BASE_URL`        | `http://127.0.0.1:5174`                                                    | frontend origin                              |
| `E2E_BACKEND_URL`     | `http://127.0.0.1:8002`                                                    | backend origin                               |
| `E2E_MOCK_GITHUB_URL` | `http://127.0.0.1:8990`                                                    | mock GitHub API                              |
| `E2E_LOG_LEVEL`       | `WARNING`                                                                  | backend log level while testing              |

## CI

The `e2e` job in `.github/workflows/ci.yml` runs the same steps against a
PostgreSQL service database and uploads the Playwright report when anything
fails.
