"""Authentication service: GitHub OAuth (authorization code + PKCE) and sessions.

GitHub access tokens are used once to read the user's identity and are then
discarded — they are never persisted and never sent to the browser.
"""

from __future__ import annotations

import urllib.parse
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import Conflict, ExternalServiceError
from app.core.security import (
    create_pkce_pair,
    generate_token,
    hash_token,
    now_utc,
)
from app.integrations.github import GitHubAuthError, GitHubClient, GitHubUser
from app.models import User, UserRole
from app.repositories.audit import SessionRepository
from app.repositories.users import UserRepository


@dataclass(frozen=True)
class LoginStart:
    authorization_url: str
    state: str
    code_verifier: str
    expires_in: int


@dataclass(frozen=True)
class LoginResult:
    user: User
    session_token: str
    csrf_token: str
    expires_at: datetime


def require_oauth_configured(settings: Settings) -> None:
    """Fail fast (503) whenever GitHub OAuth is not configured server-side."""
    if not settings.github_oauth_configured:
        raise ExternalServiceError(
            "GitHub OAuth is not configured on this server.",
            code="auth_not_configured",
            status_code=503,
        )


class AuthService:
    def __init__(self, db: Session, settings: Settings, client: GitHubClient) -> None:
        self.db = db
        self.settings = settings
        self.client = client
        self.users = UserRepository(db)
        self.sessions = SessionRepository(db)

    def start_login(self) -> LoginStart:
        require_oauth_configured(self.settings)
        state = generate_token(24)
        code_verifier, code_challenge = create_pkce_pair()
        query = urllib.parse.urlencode(
            {
                "client_id": self.settings.github_client_id,
                "redirect_uri": self.settings.github_redirect_uri,
                "scope": self.settings.github_oauth_scopes,
                "state": state,
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
                "allow_signup": "true",
            }
        )
        return LoginStart(
            authorization_url=f"{self.settings.github_oauth_authorize_url}?{query}",
            state=state,
            code_verifier=code_verifier,
            expires_in=self.settings.oauth_state_ttl_seconds,
        )

    def complete_login(
        self,
        *,
        code: str,
        code_verifier: str,
        user_agent: str | None,
    ) -> LoginResult:
        require_oauth_configured(self.settings)
        try:
            access_token = self.client.exchange_oauth_code(
                token_url=self.settings.github_oauth_token_url,
                client_id=self.settings.github_client_id,
                client_secret=self.settings.github_client_secret.get_secret_value(),
                code=code,
                redirect_uri=self.settings.github_redirect_uri,
                code_verifier=code_verifier,
            )
            github_user = self.client.get_authenticated_user(access_token)
        except GitHubAuthError as exc:
            raise ExternalServiceError(
                "GitHub rejected this sign-in attempt. Please start again.",
                code="oauth_exchange_failed",
                status_code=502,
            ) from exc

        user = self._upsert_user(github_user)
        raw_token = generate_token(32)
        expires_at = now_utc() + timedelta(hours=self.settings.session_ttl_hours)
        self.sessions.create(
            user_id=user.id,
            token_hash=hash_token(raw_token),
            expires_at=expires_at,
            user_agent=user_agent,
        )
        self.db.flush()
        return LoginResult(
            user=user,
            session_token=raw_token,
            csrf_token=generate_token(24),
            expires_at=expires_at,
        )

    def logout(self, session_token: str) -> None:
        revoke_session(self.db, session_token)

    # --- internals ------------------------------------------------------------------
    def _upsert_user(self, github_user: GitHubUser) -> User:
        login = github_user.login.strip()
        existing = self.users.get_by_github_id(github_user.id)
        bootstrap_admin = login.lower() in self.settings.admin_usernames_normalized

        if existing is None:
            claimed = self.users.get_by_username(login)
            if claimed is not None and claimed.github_id != github_user.id:
                raise Conflict(
                    "This GitHub username is already linked to another account. "
                    "Please contact an administrator."
                )
            user = User(
                github_id=github_user.id,
                github_username=login,
                avatar_url=github_user.avatar_url,
                display_name=github_user.name or login,
                role=UserRole.ADMIN if bootstrap_admin else UserRole.STUDENT,
            )
            self.users.add(user)
            self.db.flush()
            return user

        if existing.github_username != login:
            claimed = self.users.get_by_username(login)
            if claimed is not None and claimed.id != existing.id:
                raise Conflict(
                    "Your GitHub username is already linked to another account. "
                    "Please contact an administrator."
                )
            existing.github_username = login
        if github_user.avatar_url:
            existing.avatar_url = github_user.avatar_url
        if not existing.display_name and github_user.name:
            existing.display_name = github_user.name
        if bootstrap_admin and existing.role is not UserRole.ADMIN:
            existing.role = UserRole.ADMIN
        self.db.flush()
        return existing


def revoke_session(db: Session, session_token: str) -> bool:
    """Revoke a single session by its raw token. Returns True when one was revoked."""
    repository = SessionRepository(db)
    auth_session = repository.get_valid_by_token_hash(hash_token(session_token))
    if auth_session is None:
        return False
    repository.revoke(auth_session)
    db.flush()
    return True
