"""GitHub integration: safe repo-URL parsing, OAuth token exchange, API client.

Security notes:
- Only ``https://github.com/<owner>/<name>`` repository URLs are accepted.
- Credentials embedded in URLs, other hosts, ports, query strings and extra
  path segments are rejected before any network call happens.
- Outbound requests use fixed, configured GitHub hosts with strict timeouts.
  User-supplied URLs are never fetched directly.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from urllib.parse import urlsplit

import httpx

from app.core.logging import get_logger

logger = get_logger(__name__)

GITHUB_HOST = "github.com"
USER_AGENT = "gdg-tum-build-arena-backend"
API_VERSION = "2022-11-28"
MAX_README_CHARS = 100_000
MAX_COMMITS_PER_PAGE = 100


class InvalidRepoUrlError(ValueError):
    """Raised when a submitted repository URL is not a safe GitHub repo URL."""


class GitHubError(RuntimeError):
    """Base class for GitHub integration failures."""

    code = "github_error"


class GitHubUnavailable(GitHubError):
    code = "github_unavailable"


class GitHubRateLimited(GitHubError):
    code = "github_rate_limited"

    def __init__(self, message: str, retry_after_seconds: int | None = None) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class GitHubAuthError(GitHubError):
    code = "github_auth_failed"


@dataclass(frozen=True)
class RepoRef:
    owner: str
    name: str

    @property
    def full_name(self) -> str:
        """Normalized, lowercase ``owner/name`` identifier."""
        return f"{self.owner}/{self.name}".lower()

    @property
    def canonical_url(self) -> str:
        return f"https://{GITHUB_HOST}/{self.owner}/{self.name}"

    @property
    def api_path(self) -> str:
        return f"/repos/{self.owner}/{self.name}"


@dataclass(frozen=True)
class GitHubUser:
    id: int
    login: str
    avatar_url: str | None = None
    name: str | None = None


@dataclass(frozen=True)
class RepoMetadata:
    full_name: str
    private: bool
    default_branch: str
    html_url: str
    archived: bool = False
    fork: bool = False
    description: str | None = None
    size_kb: int = 0
    stars: int = 0
    pushed_at: datetime | None = None


@dataclass(frozen=True)
class FileEntry:
    path: str
    kind: str  # "file" | "dir" | "symlink" | "submodule"
    size: int = 0


@dataclass
class _CacheEntry:
    value: Any
    stored_at: float = field(default_factory=time.monotonic)


def parse_repo_url(raw: str) -> RepoRef:
    """Parse a GitHub HTTPS repository URL or raise :class:`InvalidRepoUrlError`."""
    if not isinstance(raw, str):
        raise InvalidRepoUrlError("repository URL must be a string")
    value = raw.strip()
    if not value:
        raise InvalidRepoUrlError("repository URL is required")
    if len(value) > 300:
        raise InvalidRepoUrlError("repository URL is too long")
    if "%" in value:
        raise InvalidRepoUrlError("percent-encoded characters are not allowed in repository URLs")
    if any(char.isspace() for char in value) or any(ord(char) < 32 for char in value):
        raise InvalidRepoUrlError("repository URL contains whitespace or control characters")

    try:
        parts = urlsplit(value)
    except ValueError as exc:  # malformed IPv6 etc.
        raise InvalidRepoUrlError("repository URL is malformed") from exc

    if parts.scheme.lower() != "https":
        raise InvalidRepoUrlError("only https:// GitHub repository URLs are accepted")
    if parts.username or parts.password:
        raise InvalidRepoUrlError("repository URLs must not contain embedded credentials")
    if parts.port is not None:
        raise InvalidRepoUrlError("repository URLs must not specify a port")
    if parts.query or parts.fragment:
        raise InvalidRepoUrlError("repository URLs must not contain query strings or fragments")

    host = parts.hostname or ""
    if host.lower() != GITHUB_HOST:
        raise InvalidRepoUrlError("repository URL must point to github.com")

    segments = [segment for segment in parts.path.split("/") if segment]
    if len(segments) != 2:
        raise InvalidRepoUrlError(
            "repository URL must be of the form https://github.com/owner/repo"
        )

    owner, name = segments
    if name.lower().endswith(".git"):
        name = name[: -len(".git")]
    ref = RepoRef(owner=owner, name=name)
    if not _is_valid_owner(owner):
        raise InvalidRepoUrlError("repository owner is not a valid GitHub account name")
    if not _is_valid_name(name):
        raise InvalidRepoUrlError("repository name is not valid")
    if ref.full_name.count("/") != 1:
        raise InvalidRepoUrlError("repository URL is malformed")
    return ref


def _is_valid_owner(owner: str) -> bool:
    if not owner or len(owner) > 39:
        return False
    if owner.startswith("-") or owner.endswith("-"):
        return False
    return all(char.isalnum() or char == "-" for char in owner)


def _is_valid_name(name: str) -> bool:
    if not name or len(name) > 100 or name in {".", ".."}:
        return False
    return all(char.isalnum() or char in "._-" for char in name)


class GitHubClient:
    """Thin, defensive wrapper around the GitHub REST API."""

    def __init__(
        self,
        *,
        base_url: str = "https://api.github.com",
        token: str | None = None,
        timeout_seconds: float = 10.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": API_VERSION,
            "User-Agent": USER_AGENT,
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._client = httpx.Client(
            base_url=base_url,
            headers=headers,
            timeout=httpx.Timeout(timeout_seconds),
            transport=transport,
            follow_redirects=False,
        )
        self._cache: dict[str, _CacheEntry] = {}

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> GitHubClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    # --- OAuth -----------------------------------------------------------------
    def exchange_oauth_code(
        self,
        *,
        token_url: str,
        client_id: str,
        client_secret: str,
        code: str,
        redirect_uri: str,
        code_verifier: str,
    ) -> str:
        """Exchange an authorization code for an access token (server-side only)."""
        try:
            response = self._client.post(
                token_url,
                headers={"Accept": "application/json"},
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "code_verifier": code_verifier,
                },
            )
        except httpx.HTTPError as exc:
            raise GitHubUnavailable("GitHub token endpoint is unreachable") from exc

        if response.status_code >= 500:
            raise GitHubUnavailable("GitHub token endpoint returned a server error")
        if response.status_code >= 400:
            raise GitHubAuthError("GitHub rejected the OAuth code exchange")
        try:
            payload = response.json()
        except ValueError as exc:
            raise GitHubAuthError("GitHub returned a malformed token response") from exc
        if not isinstance(payload, dict):
            raise GitHubAuthError("GitHub returned a malformed token response")
        if payload.get("error"):
            description = str(payload.get("error_description") or payload["error"])
            raise GitHubAuthError(f"GitHub OAuth error: {description}")
        token = payload.get("access_token")
        if not isinstance(token, str) or not token:
            raise GitHubAuthError("GitHub did not return an access token")
        return token

    # --- API ---------------------------------------------------------------------
    def get_authenticated_user(self, access_token: str) -> GitHubUser:
        payload = self._request("GET", "/user", access_token=access_token)
        if not isinstance(payload, dict) or "id" not in payload or "login" not in payload:
            raise GitHubAuthError("GitHub returned an unexpected user payload")
        return GitHubUser(
            id=int(payload["id"]),
            login=str(payload["login"]),
            avatar_url=payload.get("avatar_url"),
            name=payload.get("name"),
        )

    def get_repository(self, ref: RepoRef) -> RepoMetadata | None:
        payload = self._request("GET", ref.api_path, cache_key=f"repo:{ref.full_name}")
        if payload is None:
            return None
        if not isinstance(payload, dict):
            raise GitHubUnavailable("GitHub returned an unexpected repository payload")
        pushed_at = None
        raw_pushed = payload.get("pushed_at")
        if isinstance(raw_pushed, str):
            try:
                pushed_at = datetime.fromisoformat(raw_pushed.replace("Z", "+00:00"))
            except ValueError:
                pushed_at = None
        return RepoMetadata(
            full_name=str(payload.get("full_name") or ref.full_name),
            private=bool(payload.get("private")),
            default_branch=str(payload.get("default_branch") or "main"),
            html_url=str(payload.get("html_url") or ref.canonical_url),
            archived=bool(payload.get("archived")),
            fork=bool(payload.get("fork")),
            description=payload.get("description"),
            size_kb=int(payload.get("size") or 0),
            stars=int(payload.get("stargazers_count") or 0),
            pushed_at=pushed_at,
        )

    def get_contents(self, ref: RepoRef, path: str) -> FileEntry | None:
        """Return metadata for a path, or ``None`` when it does not exist."""
        clean = path.strip().strip("/")
        if not clean:
            return FileEntry(path="", kind="dir")
        payload = self._request(
            "GET",
            f"{ref.api_path}/contents/{clean}",
            cache_key=f"contents:{ref.full_name}:{clean}",
        )
        if payload is None:
            return None
        if isinstance(payload, list):
            return FileEntry(path=clean, kind="dir", size=0)
        if not isinstance(payload, dict):
            raise GitHubUnavailable("GitHub returned an unexpected contents payload")
        kind = str(payload.get("type") or "file")
        if kind not in {"file", "dir", "symlink", "submodule"}:
            kind = "file"
        return FileEntry(
            path=str(payload.get("path") or clean), kind=kind, size=int(payload.get("size") or 0)
        )

    def get_readme(self, ref: RepoRef) -> str | None:
        """Return decoded README text (possibly empty), or ``None`` when absent."""
        payload = self._request(
            "GET", f"{ref.api_path}/readme", cache_key=f"readme:{ref.full_name}"
        )
        if payload is None:
            return None
        if not isinstance(payload, dict):
            raise GitHubUnavailable("GitHub returned an unexpected README payload")
        content = payload.get("content")
        if not isinstance(content, str) or not content:
            return ""
        import base64
        import binascii

        try:
            decoded = base64.b64decode(content, validate=False).decode("utf-8", errors="replace")
        except (binascii.Error, ValueError):
            return ""
        return decoded[:MAX_README_CHARS]

    def count_commits(self, ref: RepoRef, limit: int) -> int:
        """Count commits on the default branch, capped at ``limit`` (<=100)."""
        capped = max(1, min(limit, MAX_COMMITS_PER_PAGE))
        payload = self._request(
            "GET",
            f"{ref.api_path}/commits",
            params={"per_page": capped},
            cache_key=f"commits:{ref.full_name}:{capped}",
        )
        if payload is None or not isinstance(payload, list):
            return 0
        return len(payload)

    def has_license(self, ref: RepoRef) -> bool:
        payload = self._request(
            "GET", f"{ref.api_path}/license", cache_key=f"license:{ref.full_name}"
        )
        return payload is not None

    def get_languages(self, ref: RepoRef) -> dict[str, int]:
        payload = self._request(
            "GET", f"{ref.api_path}/languages", cache_key=f"languages:{ref.full_name}"
        )
        if not isinstance(payload, dict):
            return {}
        languages: dict[str, int] = {}
        for name, size in payload.items():
            try:
                languages[str(name)] = int(size)
            except (TypeError, ValueError):
                continue
        return languages

    # --- Internals -----------------------------------------------------------------
    def _request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        access_token: str | None = None,
        cache_key: str | None = None,
        retries: int = 1,
    ) -> Any | None:
        if cache_key is not None and cache_key in self._cache:
            return self._cache[cache_key].value

        headers = {"Authorization": f"Bearer {access_token}"} if access_token else None
        last_error: Exception | None = None
        for attempt in range(retries + 1):
            try:
                response = self._client.request(method, url, params=params, headers=headers)
            except httpx.HTTPError as exc:
                last_error = exc
                logger.warning(
                    "github request failed", extra={"context": {"url": url, "attempt": attempt}}
                )
                continue

            if response.status_code == 404:
                value = None
            elif response.status_code == 401:
                raise GitHubAuthError("GitHub rejected the API credentials")
            elif response.status_code in (403, 429) and self._is_rate_limited(response):
                retry_after = self._retry_after_seconds(response)
                raise GitHubRateLimited(
                    "GitHub API rate limit exceeded", retry_after_seconds=retry_after
                )
            elif response.status_code >= 500:
                last_error = GitHubUnavailable("GitHub API returned a server error")
                continue
            elif response.status_code >= 400:
                raise GitHubUnavailable(f"GitHub API returned status {response.status_code}")
            else:
                try:
                    value = response.json()
                except ValueError as exc:
                    raise GitHubUnavailable("GitHub API returned malformed JSON") from exc

            if cache_key is not None:
                self._cache[cache_key] = _CacheEntry(value=value)
            return value

        raise GitHubUnavailable("GitHub API is unavailable") from last_error

    @staticmethod
    def _is_rate_limited(response: httpx.Response) -> bool:
        if response.headers.get("x-ratelimit-remaining") == "0":
            return True
        try:
            body = response.json()
        except ValueError:
            return False
        message = str(body.get("message", "")) if isinstance(body, dict) else ""
        return "rate limit" in message.lower() or "secondary rate" in message.lower()

    @staticmethod
    def _retry_after_seconds(response: httpx.Response) -> int | None:
        retry_after = response.headers.get("retry-after")
        if retry_after and retry_after.isdigit():
            return int(retry_after)
        reset = response.headers.get("x-ratelimit-reset")
        if reset and reset.isdigit():
            return max(int(reset) - int(time.time()), 1)
        return None
