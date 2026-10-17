"""Authentication, session and CSRF behaviour."""

from __future__ import annotations

import json

import httpx
from sqlalchemy import select

from app.core.dependencies import get_github_client
from app.integrations.github import GitHubClient
from app.models import AuthSession, User, UserRole
from app.repositories.users import UserRepository


def _mock_github(app, handler) -> None:  # type: ignore[no-untyped-def]
    client = GitHubClient(
        base_url="https://api.github.test",
        timeout_seconds=2.0,
        transport=httpx.MockTransport(handler),
    )
    app.dependency_overrides[get_github_client] = lambda: client


def _happy_handler(*, login: str = "buildmaster", user_id: int = 4242) -> callable:  # type: ignore[valid-type]
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/login/oauth/access_token":
            assert request.headers["accept"] == "application/json"
            body = request.content.decode()
            assert "client_secret=test-client-secret" in body
            return httpx.Response(200, json={"access_token": "gho_secret_token"})
        if request.url.path == "/user":
            assert request.headers["authorization"] == "Bearer gho_secret_token"
            return httpx.Response(
                200,
                json={
                    "id": user_id,
                    "login": login,
                    "avatar_url": "https://avatars.githubusercontent.com/u/4242",
                    "name": "Build Master",
                },
            )
        return httpx.Response(404, json={"message": "Not Found"})

    return handler


# --- configuration safety ---------------------------------------------------------


def test_login_fails_safely_when_oauth_is_not_configured(client):
    response = client.get("/api/v1/auth/github/login")
    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "auth_not_configured"
    assert (
        "GITHUB_CLIENT_ID" in body["error"]["message"] or "configured" in body["error"]["message"]
    )


def test_callback_fails_safely_when_oauth_is_not_configured(client):
    response = client.get(
        "/api/v1/auth/github/callback?code=abc&state=def",
        headers={"Accept": "application/json"},
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "auth_not_configured"


def test_no_authentication_bypass_exists_for_missing_configuration(oauth_client, db):
    response = oauth_client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert db.execute(select(User)).first() is None


# --- login flow ---------------------------------------------------------------------


def test_login_redirects_to_github_with_state_and_pkce(oauth_client):
    response = oauth_client.get("/api/v1/auth/github/login", follow_redirects=False)
    assert response.status_code == 302
    location = response.headers["location"]
    assert location.startswith("https://github.test/login/oauth/authorize?")
    assert "client_id=test-client-id" in location
    assert "code_challenge=" in location
    assert "code_challenge_method=S256" in location
    assert "state=" in location
    assert "scope=read%3Auser" in location
    assert "ba_oauth_state" in response.cookies or "ba_oauth_state" in response.headers.get(
        "set-cookie", ""
    )


def test_login_json_variant_returns_authorization_url(oauth_client):
    response = oauth_client.get("/api/v1/auth/github/login", headers={"Accept": "application/json"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["authorization_url"].startswith("https://github.test/login/oauth/authorize")
    assert payload["expires_in"] > 0


def test_callback_rejects_missing_state(oauth_client):
    response = oauth_client.get(
        "/api/v1/auth/github/callback?code=abc&state=forged",
        headers={"Accept": "application/json"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"


def test_callback_rejects_state_mismatch(oauth_client):
    oauth_client.cookies.set("ba_oauth_state", "expected-state")
    oauth_client.cookies.set("ba_oauth_verifier", "verifier")
    response = oauth_client.get(
        "/api/v1/auth/github/callback?code=abc&state=forged-state",
        headers={"Accept": "application/json"},
    )
    assert response.status_code == 401


def test_callback_surfaces_github_denial(oauth_client):
    response = oauth_client.get(
        "/api/v1/auth/github/callback?error=access_denied",
        headers={"Accept": "application/json"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "oauth_denied"


def test_callback_creates_user_and_session(oauth_app, oauth_client, db):
    _mock_github(oauth_app, _happy_handler())
    oauth_client.cookies.set("ba_oauth_state", "valid-state")
    oauth_client.cookies.set("ba_oauth_verifier", "verifier")

    response = oauth_client.get(
        "/api/v1/auth/github/callback?code=good-code&state=valid-state",
        headers={"Accept": "application/json"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["github_username"] == "buildmaster"
    assert payload["role"] == "student"

    set_cookie = response.headers.get_list("set-cookie")
    assert any("ba_session=" in header and "HttpOnly" in header for header in set_cookie)
    assert any("ba_csrf=" in header for header in set_cookie)
    assert any("SameSite=lax" in header for header in set_cookie)

    user = UserRepository(db).get_by_username("buildmaster")
    assert user is not None
    session_row = db.execute(select(AuthSession).where(AuthSession.user_id == user.id)).scalar_one()
    assert len(session_row.token_hash) == 64  # only the hash is stored
    assert "gho_secret_token" not in json.dumps(payload)


def test_callback_redirects_browser_to_frontend(oauth_app, oauth_client):
    _mock_github(oauth_app, _happy_handler(login="redirecty"))
    oauth_client.cookies.set("ba_oauth_state", "s1")
    oauth_client.cookies.set("ba_oauth_verifier", "v1")
    response = oauth_client.get(
        "/api/v1/auth/github/callback?code=c&state=s1", follow_redirects=False
    )
    assert response.status_code == 302
    assert response.headers["location"] == "http://localhost:5173/auth/callback?status=ok"


def test_duplicate_github_user_reuses_account(oauth_app, oauth_client, db):
    _mock_github(oauth_app, _happy_handler(login="repeatuser", user_id=777))
    for state in ("a", "b"):
        oauth_client.cookies.set("ba_oauth_state", state)
        oauth_client.cookies.set("ba_oauth_verifier", "v")
        response = oauth_client.get(
            f"/api/v1/auth/github/callback?code=c&state={state}",
            headers={"Accept": "application/json"},
        )
        assert response.status_code == 200
    users = db.execute(select(User).where(User.github_id == 777)).scalars().all()
    assert len(users) == 1


def test_admin_bootstrap_usernames_are_promoted(oauth_app, oauth_client, db, oauth_settings):
    from app.core.config import Settings
    from app.core.dependencies import get_settings_dependency

    promoted_settings = Settings(
        _env_file=None,
        environment="test",
        github_client_id="test-client-id",
        github_client_secret="test-client-secret",
        github_oauth_token_url="https://github.test/login/oauth/access_token",
        github_api_base_url="https://api.github.test",
        github_oauth_authorize_url="https://github.test/login/oauth/authorize",
        admin_github_usernames="buildmaster",
        session_cookie_secure=False,
    )
    oauth_app.dependency_overrides[get_settings_dependency] = lambda: promoted_settings
    _mock_github(oauth_app, _happy_handler(login="buildmaster", user_id=8888))
    oauth_client.cookies.set("ba_oauth_state", "s")
    oauth_client.cookies.set("ba_oauth_verifier", "v")
    response = oauth_client.get(
        "/api/v1/auth/github/callback?code=c&state=s", headers={"Accept": "application/json"}
    )
    assert response.status_code == 200
    assert response.json()["role"] == UserRole.ADMIN.value


# --- session handling -----------------------------------------------------------------


def test_me_requires_authentication(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"


def test_me_returns_current_user(client, make_user, login):
    user = make_user(username="sessioned")
    login(client, user)
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 200
    assert response.json()["github_username"] == "sessioned"


def test_bearer_token_authentication_works(client, make_user, login):
    user = make_user(username="beareruser")
    tokens = login(client, user)
    client.headers.pop("Cookie")
    client.headers.pop("X-CSRF-Token")
    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['session']}"}
    )
    assert response.status_code == 200
    assert response.json()["github_username"] == "beareruser"


def test_logout_revokes_session(client, make_user, login, revoked_session):
    user = make_user(username="loggingout")
    tokens = login(client, user)
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 200
    assert revoked_session(tokens["session"])
    assert client.get("/api/v1/auth/me").status_code == 401


def test_logout_requires_csrf_header(client, make_user, login):
    user = make_user(username="csrfvictim")
    login(client, user)
    client.headers.pop("X-CSRF-Token")
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "csrf_failed"
    assert client.get("/api/v1/auth/me").status_code == 200  # session untouched


def test_expired_or_revoked_sessions_are_rejected(client, db, make_user, login):
    from datetime import timedelta

    from app.core.security import hash_token, now_utc
    from app.repositories.audit import SessionRepository

    user = make_user(username="expired")
    tokens = login(client, user)
    session_row = SessionRepository(db).get_valid_by_token_hash(hash_token(tokens["session"]))
    assert session_row is not None
    session_row.expires_at = now_utc() - timedelta(seconds=1)
    db.flush()
    assert client.get("/api/v1/auth/me").status_code == 401


def test_inactive_users_cannot_authenticate(client, make_user, login):
    user = make_user(username="deactivated")
    login(client, user)
    user.is_active = False
    assert client.get("/api/v1/auth/me").status_code == 401


def test_github_access_tokens_are_never_persisted(oauth_app, oauth_client):
    from app.models import Base

    _mock_github(oauth_app, _happy_handler(login="nopersist", user_id=5150))
    oauth_client.cookies.set("ba_oauth_state", "s")
    oauth_client.cookies.set("ba_oauth_verifier", "v")
    response = oauth_client.get(
        "/api/v1/auth/github/callback?code=c&state=s", headers={"Accept": "application/json"}
    )
    assert response.status_code == 200
    columns = {column.name for table in Base.metadata.tables.values() for column in table.columns}
    assert not any("access_token" in name or name == "github_token" for name in columns)
