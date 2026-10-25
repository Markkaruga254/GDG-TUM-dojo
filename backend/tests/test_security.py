"""Security middleware tests: CSRF, CORS, headers, rate limits, config guardrails."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.dependencies import get_settings_dependency
from app.core.ratelimit import SlidingWindowRateLimiter, rate_limiter
from app.main import create_app

# --- CSRF -----------------------------------------------------------------------------


def test_csrf_double_submit_is_enforced_for_cookie_clients(client, make_user, login):
    login(client, make_user(username="csrfuser"))

    ok = client.patch("/api/v1/users/me", json={"display_name": "Fine"})
    assert ok.status_code == 200

    client.headers.pop("X-CSRF-Token")
    missing = client.patch("/api/v1/users/me", json={"display_name": "No token"})
    assert missing.status_code == 403
    assert missing.json()["error"]["code"] == "csrf_failed"

    client.headers["X-CSRF-Token"] = "wrong-token"
    mismatched = client.patch("/api/v1/users/me", json={"display_name": "Wrong token"})
    assert mismatched.status_code == 403

    # Safe methods are never CSRF-checked.
    assert client.get("/api/v1/users/me").status_code == 200


def test_csrf_rejects_disallowed_origin(client, make_user, login):
    login(client, make_user(username="originuser"))

    forbidden = client.patch(
        "/api/v1/users/me",
        json={"display_name": "Evil"},
        headers={"Origin": "http://evil.example"},
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "origin_not_allowed"

    allowed = client.patch(
        "/api/v1/users/me",
        json={"display_name": "Legit"},
        headers={"Origin": "http://localhost:5173"},
    )
    assert allowed.status_code == 200


def test_bearer_clients_are_not_csrf_checked(client, make_user, login):
    user = make_user(username="apiuser")
    tokens = login(client, user)
    client.headers.pop("X-CSRF-Token")
    client.headers["Authorization"] = f"Bearer {tokens['session']}"

    response = client.patch("/api/v1/users/me", json={"display_name": "Bearer Update"})

    assert response.status_code == 200
    assert response.json()["display_name"] == "Bearer Update"


# --- response headers --------------------------------------------------------------------


def test_security_headers_and_request_id_are_applied(client):
    response = client.get("/health", headers={"X-Request-ID": "trace-me-123"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "trace-me-123"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert "geolocation=()" in response.headers["Permissions-Policy"]
    assert response.headers["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"


def test_auth_responses_are_marked_no_store(client):
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.headers.get("Cache-Control") == "no-store"


# --- CORS ---------------------------------------------------------------------------------


def test_cors_preflight_allows_configured_origin(client):
    response = client.options(
        "/api/v1/challenges",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:5173"
    assert response.headers["Access-Control-Allow-Credentials"] == "true"


def test_cors_preflight_rejects_unknown_origin(client):
    response = client.options(
        "/api/v1/challenges",
        headers={
            "Origin": "http://evil.example",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert "access-control-allow-origin" not in response.headers


def test_cors_simple_request_does_not_echo_unknown_origin(client):
    response = client.get("/api/v1/challenges", headers={"Origin": "http://evil.example"})

    assert "access-control-allow-origin" not in response.headers


# --- error envelope --------------------------------------------------------------------------


def test_unknown_path_returns_machine_readable_envelope(client):
    response = client.get("/api/v1/definitely-not-a-route")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_validation_errors_report_fields_without_echoing_values(client, make_user, login):
    login(client, make_user(username="validator"))
    secret_marker = "super-secret-marker"

    response = client.patch("/api/v1/users/me", json={"display_name": secret_marker * 20})

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    assert body["error"]["details"][0]["field"] == "body.display_name"
    assert secret_marker not in response.text


# --- rate limiting ---------------------------------------------------------------------------


def test_sliding_window_limiter_prunes_expired_hits(monkeypatch):
    clock = {"now": 1000.0}
    monkeypatch.setattr("app.core.ratelimit.time.monotonic", lambda: clock["now"])
    limiter = SlidingWindowRateLimiter()

    allowed, _ = limiter.check("key", limit=2, window_seconds=60)
    assert allowed
    assert limiter.check("key", limit=2, window_seconds=60)[0] is True

    blocked, retry_after = limiter.check("key", limit=2, window_seconds=60)
    assert blocked is False
    assert retry_after >= 1

    clock["now"] += 61
    assert limiter.check("key", limit=2, window_seconds=60)[0] is True

    # Keys are isolated from each other.
    assert limiter.check("other", limit=2, window_seconds=60)[0] is True


def test_auth_endpoints_return_429_when_rate_limited(app, client):
    limited = Settings(
        _env_file=None,
        environment="test",
        rate_limit_enabled=True,
        auth_rate_limit_per_minute=2,
        session_cookie_secure=False,
    )
    app.dependency_overrides[get_settings_dependency] = lambda: limited
    rate_limiter.reset()
    try:
        first = client.get("/api/v1/auth/github/login")
        second = client.get("/api/v1/auth/github/login")
        third = client.get("/api/v1/auth/github/login")
    finally:
        rate_limiter.reset()

    assert first.status_code == 503, "oauth is unconfigured, not rate limited"
    assert second.status_code == 503
    assert third.status_code == 429
    assert third.json()["error"]["code"] == "rate_limited"
    assert third.json()["error"]["details"][0]["retry_after_seconds"] >= 1


# --- host allowlist and production guardrails ----------------------------------------------------


def test_trusted_host_middleware_rejects_unknown_hosts():
    settings = Settings(
        _env_file=None,
        environment="test",
        allowed_hosts=["api.example.test"],
        session_cookie_secure=False,
    )
    app = create_app(settings)

    with TestClient(app, base_url="http://evil.example") as bad_client:
        assert bad_client.get("/health").status_code == 400

    with TestClient(app, base_url="http://api.example.test") as good_client:
        assert good_client.get("/health").status_code == 200


def test_production_configuration_rejects_insecure_settings():
    with pytest.raises(ValueError, match="invalid production configuration"):
        Settings(
            _env_file=None,
            environment="production",
            github_client_id="client",
            github_client_secret="secret",
            frontend_origins=["*"],
            session_cookie_secure=True,
        )

    with pytest.raises(ValueError):
        Settings(
            _env_file=None,
            environment="production",
            github_client_id="",
            github_client_secret="",
            frontend_origins=["https://arena.example"],
            session_cookie_secure=True,
        )
