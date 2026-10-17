"""FastAPI dependencies: settings, database, authentication, authorization."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.errors import Forbidden, NotAuthenticated, RateLimited
from app.core.ratelimit import client_ip, rate_limiter
from app.core.security import hash_token
from app.db.session import get_db
from app.integrations.github import GitHubClient
from app.models import User, UserRole
from app.repositories.audit import SessionRepository
from app.repositories.users import UserRepository


def get_settings_dependency() -> Settings:
    """Injectable settings (overridable in tests via ``app.dependency_overrides``)."""
    return get_settings()


SettingsDep = Annotated[Settings, Depends(get_settings_dependency)]
DbDep = Annotated[Session, Depends(get_db)]


def rate_limit_dependency(
    scope: str,
    limit_getter: Callable[[Settings], tuple[int, int]],
) -> Callable[[Request, Settings], None]:
    """Build a FastAPI dependency enforcing ``limit_getter(settings)`` per client IP."""

    def dependency(request: Request, settings: SettingsDep) -> None:
        if not settings.rate_limits_enabled:
            return
        limit, window_seconds = limit_getter(settings)
        key = f"{scope}:{client_ip(request, settings)}"
        allowed, retry_after = rate_limiter.check(key, limit, window_seconds)
        if not allowed:
            raise RateLimited(
                "Too many requests. Please slow down and retry shortly.",
                details=[{"retry_after_seconds": retry_after}],
            )

    return dependency


def get_github_client(settings: SettingsDep) -> Iterator[GitHubClient]:
    """Server-side GitHub API client (never carries user credentials)."""
    client = GitHubClient(
        base_url=settings.github_api_base_url,
        token=settings.github_api_token_value or None,
        timeout_seconds=settings.github_api_timeout_seconds,
    )
    try:
        yield client
    finally:
        client.close()


GitHubClientDep = Annotated[GitHubClient, Depends(get_github_client)]


@dataclass(frozen=True)
class AuthContext:
    """How the current request authenticated (cookie vs bearer)."""

    user: User
    via_cookie: bool
    session_token: str | None = None


def _extract_token(request: Request, settings: Settings) -> tuple[str | None, bool]:
    header = request.headers.get("authorization")
    if header and header.lower().startswith("bearer "):
        token = header[7:].strip()
        if token:
            return token, False
    cookie_token = request.cookies.get(settings.session_cookie_name)
    if cookie_token:
        return cookie_token, True
    return None, False


def get_auth_context_optional(
    request: Request, db: DbDep, settings: SettingsDep
) -> AuthContext | None:
    token, via_cookie = _extract_token(request, settings)
    if not token:
        return None
    auth_session = SessionRepository(db).get_valid_by_token_hash(hash_token(token))
    if auth_session is None:
        return None
    user = UserRepository(db).get_by_id(auth_session.user_id)
    if user is None or not user.is_active:
        return None
    return AuthContext(user=user, via_cookie=via_cookie, session_token=token)


def get_current_user(
    context: Annotated[AuthContext | None, Depends(get_auth_context_optional)],
) -> User:
    if context is None:
        raise NotAuthenticated("Authentication required.")
    return context.user


CurrentUserDep = Annotated[User, Depends(get_current_user)]


def get_current_context(
    context: Annotated[AuthContext | None, Depends(get_auth_context_optional)],
) -> AuthContext:
    if context is None:
        raise NotAuthenticated("Authentication required.")
    return context


CurrentContextDep = Annotated[AuthContext, Depends(get_current_context)]


def require_roles(*roles: UserRole):
    allowed = set(roles)

    def dependency(user: CurrentUserDep) -> User:
        if user.role not in allowed:
            raise Forbidden("You do not have permission to perform this action.")
        return user

    return dependency


RequireStaffDep = Annotated[User, Depends(require_roles(UserRole.MODERATOR, UserRole.ADMIN))]
RequireAdminDep = Annotated[User, Depends(require_roles(UserRole.ADMIN))]


@dataclass(frozen=True)
class Pagination:
    page: int
    page_size: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


def get_pagination(
    settings: SettingsDep,
    page: Annotated[int, Query(ge=1, le=10_000)] = 1,
    page_size: Annotated[int | None, Query(ge=1)] = None,
) -> Pagination:
    """Clamp page sizes to the configured maximum (never trust client limits)."""
    requested = page_size or settings.default_page_size
    return Pagination(page=page, page_size=min(requested, settings.max_page_size))


PaginationDep = Annotated[Pagination, Depends(get_pagination)]


def get_client_ip(request: Request, settings: SettingsDep) -> str:
    return client_ip(request, settings)
