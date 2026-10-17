# Security — GDG TUM Build Arena backend

## Reporting a vulnerability

Please report suspected vulnerabilities **privately**:

- Use GitHub **Security → Report a vulnerability** (Security Advisories) on this
  repository, or contact the maintainers through the organization's GitHub
  presence.
- Do **not** open a public issue for a security report.

A useful report includes: what the issue is, where it lives, reproduction
steps, and the impact you believe it has. There is no bug-bounty program; the
maintainers will acknowledge reports as capacity allows and can credit
reporters who wish to be named.

When testing, please:

- Only use test accounts and data you created yourself.
- Do not access, modify or exfiltrate other users' data.
- Do not run denial-of-service or resource-exhaustion tests against shared
  infrastructure.

## Supported versions

The project has no released versions yet; security fixes land on the `main`
branch. There are no production deployments maintained by this repository.

## Security model (implemented)

| Control | Implementation |
| --- | --- |
| Sign-in | GitHub OAuth with `state` + PKCE; state and verifier stored in short-lived HttpOnly cookies; constant-time comparison |
| GitHub token handling | The OAuth access token is used once to read the identity, then discarded — never stored or logged |
| Sessions | Database-backed; only a SHA-256 hash of the session token is stored; logout and deactivation revoke tokens immediately |
| Cookies | `HttpOnly`, `SameSite=Lax`, `Secure` by default in production |
| CSRF | Double-submit token (`X-CSRF-Token` must match the `ba_csrf` cookie) for cookie-authenticated mutations; Bearer clients are exempt; browser Origin checks |
| CORS | Explicit origin allowlist with credentials; wildcard origins are rejected in production |
| Authorization | Role checks (`student` → `moderator` → `admin`) plus per-resource ownership; unauthorized access to others' submissions returns `404` to avoid existence leaks |
| Rate limiting | Per-IP sliding window on auth/submission/evaluation endpoints plus per-user cooldown and daily caps; `Retry-After` returned on `429` |
| Logging | Structured logs redact authorization headers, cookies and tokens |
| Audit trail | Every privileged or score-affecting action writes a sanitized `audit_logs` row (sensitive keys redacted, payloads capped) |
| Code execution | None — evaluations read public GitHub metadata only; repositories are never cloned and student code is never executed |
| Configuration | Production settings are validated at startup (debug off, secure cookies, no wildcard origins, OAuth configured); optional `ALLOWED_HOSTS` host-header enforcement |

## Secret handling

- `.env` files are git-ignored; `.env.example` contains placeholders only.
  Never commit real credentials, tokens or database dumps.
- `GITHUB_API_TOKEN` (optional) should be a read-only token used only for
  raising GitHub API rate limits during evaluations; it is never exposed to
  users and is not returned by any endpoint.
- Sessions and CSRF tokens are bearer-equivalent secrets: treat them like
  passwords. Cookies are used by browsers; avoid pasting them into logs,
  screenshots or issues.
- If a credential may have leaked, rotate it (GitHub OAuth app secret, API
  token, database password) and revoke affected sessions rather than assuming
  deletion from a file or a `.gitignore` entry is sufficient (it is not, once a
  secret has entered Git history or any log).

## Operational hardening

- Set `ENVIRONMENT=production` in deployed environments — it enables secure
  cookies and strict configuration validation.
- Set `TRUST_PROXY_HEADERS=true` **only** behind a trusted reverse proxy that
  overwrites `X-Forwarded-For`; otherwise client IPs can be spoofed and the
  rate limiter evaded.
- Apply platform-level rate limits and TLS termination at the platform/proxy
  layer when scaling beyond a single instance (the in-process limiter is per
  worker).
- Back up PostgreSQL and restrict network access to it; the application expects
  a trusted network path to the database.
- Review `audit_logs` periodically; it contains actor usernames and action
  metadata and should be treated as sensitive operational data.

## Known security limitations (MVP)

- The rate limiter is in-process and therefore per instance/worker; horizontal
  scaling needs platform-level limits.
- Evaluations run synchronously inside the API process; very slow GitHub calls
  occupy a request (bounded by timeouts/retries).
- Authentication is GitHub-only — there is no email/password flow, no 2FA of
  its own, and no session-management UI beyond logout/revocation.
- Score overrides, disqualifications and role changes are trusted staff actions;
  they are audited but not dual-approved.
- No WAF, DDoS protection, or database-at-rest encryption is shipped — those
  are platform/operations concerns.
- Private-repository evaluation is not implemented; a token with broader scope
  than needed is not required by the MVP flow.
