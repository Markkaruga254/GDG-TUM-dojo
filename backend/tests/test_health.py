"""Health and readiness endpoint tests."""

from __future__ import annotations

from sqlalchemy.exc import OperationalError


def test_health_is_ok(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "database" not in response.text.lower()


def test_ready_reports_database(client):
    response = client.get("/api/v1/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "checks": {"database": "ok"}}


def test_root_level_probes_for_deploy_platforms(client):
    assert client.get("/health").status_code == 200
    assert client.get("/ready").status_code == 200


def test_ready_returns_503_without_leaking_details(client, app):
    from app.db.session import get_db

    class BrokenSession:
        def execute(self, *args, **kwargs):
            raise OperationalError("SELECT 1", {}, Exception("connection refused to db:5432"))

    app.dependency_overrides[get_db] = lambda: BrokenSession()
    response = client.get("/api/v1/ready")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "not_ready"
    assert body["checks"]["database"] == "error"
    assert "5432" not in response.text
    assert "refused" not in response.text
