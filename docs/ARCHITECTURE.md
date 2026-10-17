# Architecture — GDG TUM Build Arena

How the full-stack platform is put together: the FastAPI API, the React SPA,
how requests flow through them, and where the extension points are. Setup
instructions live in [`backend/README.md`](../backend/README.md) and
[`frontend/README.md`](../frontend/README.md); the security design lives in
[`SECURITY.md`](SECURITY.md) and the current phase and planned work in
[`ROADMAP.md`](ROADMAP.md).

## System context

A single FastAPI service owns all business logic and persistence. The React SPA
in [`frontend/`](../frontend/README.md) is the browser client: it holds
presentation and client-side state only, and every authorization or scoring rule
is enforced by the API. PostgreSQL is the only stateful dependency; GitHub is an
external dependency for OAuth and repository metadata used by evaluations. There
is no Redis, message broker or worker process in v1.

```mermaid
flowchart TB
    subgraph clients["Clients"]
        browser["React SPA — frontend/<br/>(browser clients)"]
        curl["curl / API scripts"]
    end

    subgraph fastapi["FastAPI application (backend/app)"]
        mw["core/<br/>config · security · errors · logging · rate limit · middleware · dependencies"]
        api["api/v1/<br/>health · auth · users · challenges · submissions · leaderboard · badges · admin"]
        svc["services/<br/>auth · users · challenges · submissions · evaluation · leaderboard · badges · admin · audit"]
        repo["repositories/<br/>SQLAlchemy 2.x queries incl. leaderboard aggregation"]
        ev["evaluation/<br/>check rules · GitHub probe · runner · executor seam"]
        session["db/<br/>engine + session factory"]
        models["models/ + schemas/<br/>8 tables · Pydantic v2 contracts"]
    end

    pg[("PostgreSQL")]
    gh["GitHub REST API"]
    scripts["scripts/<br/>seed_badges · promote_admin"]
    alembic["Alembic migrations"]

    browser --> mw
    curl --> mw
    mw --> api --> svc
    svc --> repo
    svc --> ev
    api --> models
    repo --> session
    session --> pg
    ev -- "metadata-only reads" --> gh
    svc -- "OAuth token exchange + identity" --> gh
    scripts --> session
    alembic --> pg
```

Module responsibilities:

| Path | Responsibility |
| --- | --- |
| `app/main.py` | App factory, middleware stack, error handlers (including the 404 envelope) |
| `app/api/v1/` | HTTP surface: validation, dependencies, status codes; one module per resource |
| `app/core/` | Settings, security helpers (hashing, cookies), session/user dependencies, RBAC, rate limiting, logging, middleware, error envelope |
| `app/services/` | Business rules and orchestration (auth, users, challenges, submissions, evaluation, leaderboard, badges, admin, audit) |
| `app/repositories/` | Database queries, including the atomic submission claim and the leaderboard aggregation |
| `app/evaluation/` | Check definitions (`rules.py`), GitHub metadata probe (`probe.py`), scoring runner (`runner.py`), executor seam (`executor.py`) |
| `app/integrations/github.py` | GitHub OAuth + REST client (timeouts, bounded retries, per-request caching) |
| `app/models/` | SQLAlchemy models, enums and status groupings |
| `app/schemas/` | Pydantic request/response contracts and the shared page/error envelopes |
| `migrations/` | Alembic environment and revisions (initial revision `b3eafbacb03b`) |
| `scripts/` | Operational scripts (`seed_badges`, `promote_admin`) |

## Backend request flow

1. Uvicorn passes the request to the ASGI app built by `create_app()`
   (`app/main.py`). Middleware applies CORS, host checks, CSRF verification for
   cookie-authenticated mutations, rate limiting and request logging.
2. Router dependencies resolve the caller: session cookie (or
   `Authorization: Bearer` for API clients) → session record → user; role and
   ownership checks happen per endpoint.
3. Routers delegate to services; services use repositories for persistence and
   the evaluation subsystem for scoring work.
4. Responses are Pydantic schemas: lists use the page envelope
   (`items`/`total`/`page`/`page_size`/`pages`); every error – including 404s
   for unknown routes – uses the machine-readable error envelope.
5. Every privileged or score-affecting mutation writes an `audit_logs` row with
   sanitized metadata.

## Authentication flow (GitHub OAuth)

The callback exchanges the authorization code with PKCE and immediately
discards the GitHub access token; only the identity is read.

```mermaid
sequenceDiagram
    autonumber
    actor Student
    participant Browser
    participant API as FastAPI /auth
    participant GH as GitHub
    participant DB as PostgreSQL

    Student->>Browser: Click "Sign in with GitHub"
    Browser->>API: GET /api/v1/auth/github/login
    API-->>Browser: 302 to GitHub + short-lived state & PKCE cookies
    Browser->>GH: Consent screen (state, code_challenge)
    GH-->>Browser: Redirect back with code + state
    Browser->>API: GET /api/v1/auth/github/callback
    API->>API: Compare state (constant time), check PKCE
    API->>GH: Exchange code + code_verifier
    GH-->>API: Access token (used once, then discarded)
    API->>GH: GET /user (identity)
    GH-->>API: Profile payload
    API->>DB: Upsert user, store session token hash
    API-->>Browser: Set HttpOnly session + CSRF cookies, redirect to frontend
```

## Frontend architecture

The SPA is a static Vite build in [`frontend/`](../frontend/README.md). It
contains no business rules: routes render data fetched from the API, and the
server remains the authority for authorization, scoring and state transitions.

| Concern | Implementation |
| --- | --- |
| Build | Vite 8 + React 19 + TypeScript (strict); hashed assets in `frontend/dist` |
| Routing | React Router 8, `BrowserRouter`; `React.lazy` code-splits every page except Home/NotFound |
| Access gates | `RequireAuth`, `RequireStaff`, `RequireAdmin` wrap routes and render sign-in/forbidden states — UX only; the API re-checks every request |
| Server state | TanStack Query v5 — 20 s stale time, no retries on 4xx, a query-key factory per resource |
| API access | `src/lib/api.ts` — `credentials: "include"`, CSRF header mirroring, `ApiError` normalization |
| Theme | Tailwind v4 + CSS custom-property tokens; pre-paint `localStorage` bootstrap, dark default, full light override |
| Feedback | Skeletons, empty/error states, sonner toasts, Radix dialogs/menus/tabs/tooltips |

### Route map

| Route | Access | Purpose |
| --- | --- | --- |
| `/` | public | Landing page and highlights |
| `/challenges`, `/challenges/:slug` | public | Catalogue and challenge detail |
| `/leaderboard`, `/badges`, `/u/:username` | public | Rankings, badge catalogue, public portfolio |
| `/challenges/:slug/submit` | signed in | Submission form |
| `/submissions`, `/submissions/:id` | signed in | Personal history and evaluation results |
| `/settings` | signed in | Profile and session |
| `/auth/callback` | public | OAuth completion; confirms `/auth/me`, then redirects |
| `/staff` | staff | Console overview |
| `/staff/challenges`, `/staff/challenges/new`, `/staff/challenges/:slug/edit` | staff | Challenge authoring |
| `/staff/submissions`, `/staff/users`, `/staff/badges` | staff | Moderation, people, badge catalogue |
| `/staff/audit` | admin | Audit log |
| `*` | public | 404 page |

### Browser request flow

1. On load, `fetchMe()` calls `GET /api/v1/auth/me`; `401` maps to a signed-out
   state rather than an error. Route gates render a loading state first.
2. Reads go through React Query hooks; list responses use the backend page
   envelope. The catalogue's facet options come from a bounded
   `page_size=100` fetch of the visible catalogue.
3. Writes go through the single fetch wrapper, which mirrors the readable
   `ba_csrf` cookie into `X-CSRF-Token` and includes credentials.
4. Creating a submission navigates to `/submissions/:id`. When the result is
   `pending` with zero attempts, the results page triggers
   `POST /submissions/{id}/evaluate` once (guarded against re-entry) and polls
   while the status is `pending`/`queued`/`running`.
5. `ApiError` preserves the backend code, message and details so pages can render
   specific states (for example duplicate submission or rate-limit retry).

### Staff authoring semantics

The public challenge payload does not expose stored check parameters, so the
edit form preserves the existing evaluation configuration unless the author
explicitly flips **Replace evaluation configuration**. Replacing rebuilds the
checks from the public summaries with default parameters, and the UI warns about
the reset. This avoids silently overwriting parameters the client cannot see.

## Evaluation pipeline

Evaluations are metadata-only. The engine reads repository metadata (existence,
visibility, files, README, commits, license, languages) through the GitHub REST
API. Student code is never cloned or executed.

```mermaid
sequenceDiagram
    autonumber
    actor User as Owner / staff
    participant API as POST /submissions/{id}/evaluate
    participant Svc as EvaluationService
    participant Repo as Submissions repository
    participant Probe as GitHub probe
    participant Rules as Check runner
    participant DB as PostgreSQL

    User->>API: Trigger evaluation (staff may pass ?force=true)
    API->>Svc: evaluate(submission_id)
    Svc->>Repo: claim_for_evaluation (atomic UPDATE ... WHERE status ...)
    Repo-->>Svc: claimed / already final (returns 202)
    Svc->>Probe: Fetch repository metadata
    Probe-->>Svc: Files, README, commits, license, languages
    Svc->>Rules: Run configured checks (points, required flags)
    Rules-->>Svc: passed / failed / partial / error results
    Svc->>DB: Persist evaluation + submission status + attempts
    Svc->>DB: Evaluate badge awards (idempotent)
    Svc-->>API: Evaluation summary
    API-->>User: 200 with scores and check results
```

Key properties:

- **Idempotent triggers** — a submission with an evaluation in flight
  (`queued`/`running`) returns `202` instead of double-running; staff can force
  a re-run of a final submission (`?force=true`, audited).
- **Statuses** — submissions move through
  `pending → (queued) → running → passed | failed | error`; `queued` exists for
  a future queue-backed executor. Evaluations are `running → completed | error`.
- **Scoring** — partial credit sums passed check points; required checks gate a
  `passed` outcome; an errored check marks the run `error`, contributes zero and
  is excluded from the leaderboard but can be re-run.
- **Retries** — multiple attempts per challenge are allowed (cooldown + daily
  cap); each run is a separate `evaluations` row and `evaluation_attempts` is
  incremented on the submission.

Authoritative details for scoring, leaderboard counting (best attempt per user
and challenge, override precedence, tie-breaks) and badges are documented in
[`backend/README.md`](../backend/README.md#scoring-and-evaluation).

## Data model

Eight tables, created by Alembic migration `b3eafbacb03b`. All timestamps are
timezone-aware UTC; enum-like columns are `VARCHAR` with explicit `CHECK`
constraints.

| Table | Purpose | Key constraints & relationships |
| --- | --- | --- |
| `users` | Accounts and roles | `github_id`, `github_username` unique; role/status checks; 1→N sessions, submissions, badges |
| `auth_sessions` | Server-side sessions | Unique SHA-256 `token_hash` (raw token never stored); FK → `users` `CASCADE`; `expires_at`, `revoked_at` |
| `challenges` | Challenge catalogue | Unique `slug`; status/difficulty checks; `max_points` 1–10 000; optional schedule window; JSONB `evaluation_config`; `created_by` FK `SET NULL` |
| `submissions` | Student attempts | FKs → `users`/`challenges` `CASCADE`; lifecycle status; `points_awarded`; JSONB `results`; moderation (disqualification) and score-override fields; `evaluation_attempts` |
| `evaluations` | One row per evaluation run | FK → `submissions` `CASCADE`; JSONB `checks`; `max_score`/`awarded_score`; `evaluator_version` |
| `badges` | Badge catalogue | Unique `slug`/`name`; JSONB `criteria` rule; `is_active` |
| `user_badges` | Awarded badges | Unique `(user_id, badge_id)`; badge FK `RESTRICT`; user FK `CASCADE`; `awarded_by` `SET NULL` |
| `audit_logs` | Privileged-action trail | Sanitized JSONB metadata; actor FK `SET NULL`; indexes by action/actor/target/time |

Deletion policy: deleting a user cascades to their sessions, submissions and
awards (and anonymizes audit references via `SET NULL`); deleting a challenge
cascades to its submissions; deleting a submission cascades to its evaluations.
Badges cannot be deleted while awarded (`RESTRICT`). In normal operation,
accounts are deactivated (`users.is_active = false`) instead of deleted, and
leaderboards exclude inactive users.

## Deployment topology

- **Local development** — `docker compose up --build` starts PostgreSQL 16 and
  the API (migrations, badge seed and Uvicorn on start). The SPA runs separately
  with `npm run dev`, proxying `/api` to the API so the browser sees one origin.
- **Production (planned, documented but not yet exercised)** — a static host/CDN
  serves `frontend/dist` and rewrites unknown paths to `index.html`; one API
  container (or native Python service) serves `/api/v1`; managed PostgreSQL
  stores all state. Set `VITE_API_BASE_URL` at build time, add the SPA origin to
  `FRONTEND_ORIGINS`, run migrations as a release step, target `/health` for
  platform health checks, and set `ENVIRONMENT=production` (secure cookies and
  strict config validation). Set `TRUST_PROXY_HEADERS=true` only behind a
  trusted reverse proxy.
- **Cookie/site constraint** — session and CSRF cookies are `SameSite=Lax`.
  Prefer a same-site topology (`app.example.org` + `api.example.org`). A
  cross-site topology would require extending the backend cookie configuration
  and is not supported by the current implementation.
- **Scaling caveat** — the in-process rate limiter is per instance; apply
  platform-level limits when running more than one instance or worker. The
  leaderboard and evaluation claims are safe under concurrency thanks to the
  atomic claim `UPDATE` and best-attempt aggregation.

## Extension points

Designed-for seams (no behavior change required in the API layer):

1. **`EvaluationExecutor`** — replace `SynchronousExecutor` with a queue-backed
   executor; the atomic claim in the repository already prevents double-runs,
   and `queued` is part of the status model.
2. **Rate limiter** — the sliding-window limiter sits behind a small interface;
   a Redis-backed implementation can replace it when scaling horizontally.
3. **Repositories** — all SQL is isolated from HTTP handlers; query changes
   (indexes, aggregation) do not touch routers.
4. **GitHub client** — timeouts, retries and the optional server-side token are
   centralized in `app/integrations/github.py`.
5. **Frontend modules** — new pages are lazy-loaded routes in
   `frontend/src/App.tsx`; API contracts are kept in
   `frontend/src/api/types.ts`. A backend resource change starts there.

## Non-goals (v1)

- Server-rendered pages — the platform is an API plus a client-side SPA that
  lives in [`frontend/`](../frontend/README.md).
- Executing or sandboxing student code — only metadata is inspected.
- Manual-review check types, exports and notifications.
- Multi-tenant or per-organization isolation.
