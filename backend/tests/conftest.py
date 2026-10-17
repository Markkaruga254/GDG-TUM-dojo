"""Test configuration and shared fixtures.

Tests run against a dedicated PostgreSQL database — never against production data.
Set ``TEST_DATABASE_URL`` to point at a disposable database, for example:

    createdb buildarena_test
    export TEST_DATABASE_URL=postgresql+psycopg://buildarena:buildarena@localhost:5432/buildarena_test

Each test runs inside a transaction that is rolled back afterwards, so tests are
isolated without truncating tables.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

# Configure the environment *before* importing application modules.
os.environ["ENVIRONMENT"] = "test"
os.environ.setdefault(
    "DATABASE_URL",
    os.environ.get(
        "TEST_DATABASE_URL",
        "postgresql+psycopg://buildarena:buildarena@127.0.0.1:5433/buildarena_test",
    ),
)
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["LOG_LEVEL"] = "WARNING"
os.environ["LOG_JSON"] = "false"
os.environ["SESSION_COOKIE_SECURE"] = "false"
os.environ["FRONTEND_ORIGINS"] = "http://localhost:5173"
os.environ["GITHUB_CLIENT_ID"] = ""
os.environ["GITHUB_CLIENT_SECRET"] = ""

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.core.dependencies import get_github_client, get_settings_dependency
from app.core.security import generate_token, hash_token
from app.db.base import Base
from app.db.session import get_db
from app.integrations.github import GitHubClient
from app.main import create_app
from app.models import AuthSession, User
from app.repositories.audit import SessionRepository
from tests import factories

TEST_DATABASE_URL = os.environ["DATABASE_URL"]


# --- database ------------------------------------------------------------------


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    # Same session timezone as the application engine so timestamp handling is realistic.
    engine = create_engine(
        TEST_DATABASE_URL,
        pool_pre_ping=True,
        connect_args={"options": "-c timezone=UTC"},
    )
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db(engine: Engine) -> Iterator[Session]:
    connection = engine.connect()
    transaction = connection.begin()
    factory = sessionmaker(
        bind=connection,
        autoflush=False,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    session = factory()
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


# --- settings --------------------------------------------------------------------


@pytest.fixture
def settings() -> Settings:
    return Settings(
        _env_file=None, environment="test", github_client_id="", github_client_secret=SecretStr("")
    )


@pytest.fixture
def oauth_settings() -> Settings:
    """Settings with GitHub OAuth configured (fake endpoints, no live calls)."""
    return Settings(
        _env_file=None,
        environment="test",
        github_client_id="test-client-id",
        github_client_secret=SecretStr("test-client-secret"),
        github_oauth_authorize_url="https://github.test/login/oauth/authorize",
        github_oauth_token_url="https://github.test/login/oauth/access_token",
        github_api_base_url="https://api.github.test",
        frontend_auth_redirect_url="http://localhost:5173/auth/callback",
        session_cookie_secure=False,
    )


# --- GitHub client (mocked) ---------------------------------------------------------


@pytest.fixture
def github_transport() -> httpx.MockTransport:
    """Default transport: every GitHub API call 404s unless a test overrides it."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"message": "Not Found"})

    return httpx.MockTransport(handler)


@pytest.fixture
def github_client(github_transport: httpx.MockTransport) -> Iterator[GitHubClient]:
    client = GitHubClient(
        base_url="https://api.github.test", timeout_seconds=2.0, transport=github_transport
    )
    yield client
    client.close()


# --- application and HTTP client --------------------------------------------------------


@pytest.fixture
def app(db: Session, settings: Settings, github_client: GitHubClient):  # type: ignore[no-untyped-def]
    application = create_app(settings)
    application.dependency_overrides[get_db] = lambda: db
    application.dependency_overrides[get_settings_dependency] = lambda: settings
    application.dependency_overrides[get_github_client] = lambda: github_client
    try:
        yield application
    finally:
        application.dependency_overrides.clear()


@pytest.fixture
def client(app) -> Iterator[TestClient]:  # type: ignore[no-untyped-def]
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def oauth_app(db: Session, oauth_settings: Settings, github_client: GitHubClient):  # type: ignore[no-untyped-def]
    application = create_app(oauth_settings)
    application.dependency_overrides[get_db] = lambda: db
    application.dependency_overrides[get_settings_dependency] = lambda: oauth_settings
    application.dependency_overrides[get_github_client] = lambda: github_client
    try:
        yield application
    finally:
        application.dependency_overrides.clear()


@pytest.fixture
def oauth_client(oauth_app) -> Iterator[TestClient]:  # type: ignore[no-untyped-def]
    with TestClient(oauth_app) as test_client:
        yield test_client


# --- authentication helpers ---------------------------------------------------------------


@pytest.fixture
def make_user(db: Session):  # type: ignore[no-untyped-def]
    return lambda **kwargs: factories.make_user(db, **kwargs)


@pytest.fixture
def login(db: Session):  # type: ignore[no-untyped-def]
    """Authenticate a TestClient as ``user`` using a real session record."""

    def _login(client: TestClient, user: User, *, csrf: str | None = None) -> dict[str, str]:
        raw_token = generate_token(16)
        SessionRepository(db).create(
            user_id=user.id, token_hash=hash_token(raw_token), expires_at=factories.future_expiry()
        )
        db.flush()
        csrf_token = csrf or generate_token(12)
        client.headers["Cookie"] = f"ba_session={raw_token}; ba_csrf={csrf_token}"
        client.headers["X-CSRF-Token"] = csrf_token
        return {"session": raw_token, "csrf": csrf_token}

    return _login


@pytest.fixture
def session_exists(db: Session):  # type: ignore[no-untyped-def]
    def _exists(token: str) -> bool:
        return SessionRepository(db).get_valid_by_token_hash(hash_token(token)) is not None

    return _exists


@pytest.fixture
def revoked_session(db: Session):  # type: ignore[no-untyped-def]
    def _revoked(token: str) -> bool:
        session = db.query(AuthSession).filter(AuthSession.token_hash == hash_token(token)).first()
        return session is not None and session.revoked_at is not None

    return _revoked
