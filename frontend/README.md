# Build Arena — Frontend

Single-page app for **GDG TUM Build Arena**: browse challenges, submit a
repository for evaluation, watch scores, badges and leaderboard positions
update — plus the staff console for moderators and admins.

Built with **Vite + React 19 + TypeScript** against the FastAPI backend in
[`../backend`](../backend/README.md).

> **Status.** The student flows and the staff console are implemented and were
> verified end-to-end against a local backend with seeded demo data (unit tests
> plus a local Playwright smoke run across the major routes). Live GitHub OAuth
> has **not** been exercised with real credentials yet — locally, sign-in was
> simulated with backend-minted session cookies. See
> [Known limitations](#known-limitations).

## Stack

| Layer            | Choice                                                                     |
| ---------------- | -------------------------------------------------------------------------- |
| Build tool       | Vite 8 (`@vitejs/plugin-react`), target `es2022`                           |
| Framework        | React 19, TypeScript (strict, `erasableSyntaxOnly`)                        |
| Styling          | Tailwind CSS v4 via `@tailwindcss/vite`, CSS custom-property design tokens |
| Routing          | React Router 8, route-level code splitting (`React.lazy`)                  |
| Server state     | TanStack Query v5                                                          |
| UI primitives    | Radix UI (dialog, alert-dialog, dropdown-menu, tabs, tooltip)              |
| Icons / toasts   | lucide-react / sonner                                                      |
| Variants & merge | class-variance-authority, clsx, tailwind-merge                             |
| Fonts            | `@fontsource-variable` Inter (UI) + JetBrains Mono (code/IDs)              |
| Tests            | Vitest + Testing Library (jsdom)                                           |
| Quality          | oxlint + Prettier                                                          |

## Quick start

The SPA needs a running API. Start the backend first (see
[`../backend/README.md`](../backend/README.md)), then:

```bash
cd frontend
npm install
cp .env.example .env.local        # optional — see Configuration
npm run dev                       # http://localhost:5173
```

In development the Vite dev server proxies `/api` to the backend, so the
browser sees a single origin and session cookies work without any CORS setup
(`changeOrigin` is on; the proxy target defaults to `http://localhost:8000`).

```bash
VITE_API_PROXY_TARGET=http://localhost:8001 npm run dev   # API on another port
```

## Configuration

Settings are read at build/dev-server start time (Vite env rules apply —
`.env.local` is git-ignored):

| Variable                | Purpose                                                                                                           | Default                 |
| ----------------------- | ----------------------------------------------------------------------------------------------------------------- | ----------------------- |
| `VITE_API_BASE_URL`     | Absolute API origin used by the browser. Leave empty when the SPA and API share an origin (dev proxy handles it). | empty                   |
| `VITE_API_PROXY_TARGET` | Where the dev server proxies `/api` requests (development only).                                                  | `http://localhost:8000` |

For a production build, set `VITE_API_BASE_URL` when the API lives on a
different origin, e.g. `VITE_API_BASE_URL=https://api.example.org npm run build`.

## Scripts

```bash
npm run dev          # Vite dev server on :5173 (with /api proxy)
npm run build        # tsc -b (strict typecheck) + production bundle in dist/
npm run preview      # serve the built bundle locally
npm run lint         # oxlint
npm run format       # Prettier — write
npm run format:check # Prettier — check
npm run typecheck    # tsc -b only
npm test             # Vitest run
npm run test:watch   # Vitest watch mode
```

## Project structure

```
frontend/
├── index.html                 # entry document; inline pre-paint theme bootstrap
├── vite.config.ts             # aliases, dev proxy, build target
├── vitest.config.ts           # merges the Vite config; jsdom environment
└── src/
    ├── main.tsx               # fonts + globals, mounts <App/>
    ├── App.tsx                # providers, router, route-level code splitting
    ├── api/                   # typed API modules mirroring the backend contract
    │   ├── types.ts           # hand-kept types for every schema the UI uses
    │   ├── auth.ts users.ts challenges.ts submissions.ts leaderboard.ts
    │   ├── badges.ts admin.ts
    ├── components/
    │   ├── ui/                # design-system primitives (button, card, dialog, …)
    │   ├── common/            # guards, sign-in button, theme toggle, user menu, …
    │   ├── domain/            # challenge card, status badges, badge tile, stat card
    │   └── layout/            # app shell, navbar, footer, page container
    ├── hooks/                 # session, theme, queries (react-query), debounce, …
    ├── lib/                   # fetch client + query keys + utils + repo parsing
    ├── pages/                 # one module per route (staff pages in pages/staff/)
    ├── styles/globals.css     # Tailwind entry + design tokens + animations
    └── test/setup.ts          # jsdom polyfills + jest-dom matchers
```

## Design system

- **Dark-first.** The theme is applied before first paint by an inline script
  in `index.html`; `localStorage["ba-theme"] === "light"` switches to the light
  theme, anything else keeps dark. The toggle lives in the navbar.
- **Tokens, not raw colors.** `globals.css` defines named CSS custom
  properties (`--ba-bg`, `--ba-surface`, `--ba-ink`, `--ba-primary`, …) mapped
  to Tailwind theme values (`bg-surface`, `text-ink`, `border-line`, …), with a
  full light-mode override block. Both themes are first-class; new UI should
  use token classes only.
- **Palette.** Google-blue accent (`#1a73e8` light / `#8ab4f8` dark) with a
  warm accent for highlights; success/warning/danger families each ship a soft
  background variant for badges and alerts.
- **Motion.** Small, purposeful animations (`fade-up`, `fade-in`, `scale-in`,
  `slide-in`, `drift`) gated behind `prefers-reduced-motion`.
- **Accessibility.** Radix primitives back all dialogs/menus/tabs/tooltips;
  the shell has a skip link; icon-only controls carry labels; focus rings are
  deliberately tokenized.

## API client and auth

- `src/lib/api.ts` is the single fetch wrapper:
  - `credentials: "include"` — the session is a pair of cookies (`ba_session`,
    `ba_csrf`) set by the backend; the SPA never touches tokens directly.
  - **CSRF double-submit**: non-GET requests mirror the `ba_csrf` cookie into
    the `X-CSRF-Token` header, matching the backend middleware.
  - Every failure is normalized to `ApiError { status, code, message, details }`
    from the backend's `{"error": {...}}` envelope, so UI code branches on codes
    instead of raw HTTP text.
- `src/api/types.ts` mirrors the backend Pydantic schemas by hand — when the
  API changes, update this file first and follow the type errors.
- React Query defaults (`App.tsx`): 20 s stale time; retries skip 4xx client
  errors. Submission results poll while an evaluation is pending/queued/running.
- **Sign-in** redirects to `GET /api/v1/auth/github/login`; the backend returns
  to `/auth/callback?status=ok&code=…` and the page then confirms the session
  via `/users/me`.
- **Staff challenge editing** is conservative by design: the API does not
  return stored evaluation parameters, so the edit form preserves the current
  configuration unless you explicitly flip _Replace evaluation configuration_.

## Testing

```bash
npm test
```

Vitest runs in jsdom with Testing Library. The committed suite covers the
high-risk helpers: the API client (envelope → `ApiError`, CSRF header, network
failure, 204 handling), URL utils (formatting, deadlines, avatars), GitHub
repo-URL parsing, and the button primitive.

End-to-end verification was a local Playwright smoke run (not committed):
backend + seeded demo database, session cookies injected into the browser
context, every route screenshotted and asserted free of console/page errors —
including a real submission POST and its auto-triggered evaluation.

## Known limitations

- **Live GitHub OAuth is unverified** (no OAuth app credentials have been used
  against this UI yet) — and no deployment exists, so cookie attributes and
  origins have only been exercised on localhost.
- The app is fully client-rendered: no SSR/SSG, and static hosts must rewrite
  unknown paths to `index.html` for client-side routing.
- No committed end-to-end suite or CI pipeline for the frontend yet.
- Search-facet options (tracks/tags) are derived from a bounded `page_size=100`
  fetch of the catalogue — fine for the expected catalogue size, but it will
  need a dedicated facets endpoint if the catalogue grows.

## License

No license has been chosen yet — flagged for the project owner. Until a license
is added, default copyright rules apply; contact the maintainers before reusing
the code outside this project.
