"""Evaluation API tests: synchronous triggering, idempotency, scoring and badges."""

from __future__ import annotations

import base64

import httpx
from sqlalchemy import func, select

from app.core.dependencies import get_github_client
from app.integrations.github import GitHubClient
from app.models import AuditLog, Evaluation, SubmissionStatus, UserRole
from app.services.badges import BadgeService
from tests import factories

REPO_FULL_NAME = "arena/demo"


def _repo_payload(*, private: bool = False) -> dict:
    return {
        "full_name": REPO_FULL_NAME,
        "private": private,
        "default_branch": "main",
        "html_url": f"https://github.com/{REPO_FULL_NAME}",
        "archived": False,
        "fork": False,
        "size": 128,
        "stargazers_count": 3,
    }


def _readme_payload(text: str = "# Demo\nA cloud cost tracker.") -> dict:
    return {"content": base64.b64encode(text.encode()).decode(), "encoding": "base64"}


def _transport(*, repo_status: int = 200, readme_status: int = 200, private: bool = False):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == f"/repos/{REPO_FULL_NAME}":
            if repo_status != 200:
                return httpx.Response(repo_status, json={"message": "server error"})
            return httpx.Response(200, json=_repo_payload(private=private))
        if request.url.path == f"/repos/{REPO_FULL_NAME}/readme":
            if readme_status != 200:
                return httpx.Response(readme_status, json={"message": "Not Found"})
            return httpx.Response(200, json=_readme_payload())
        return httpx.Response(404, json={"message": "Not Found"})

    return httpx.MockTransport(handler)


def _mock_github(app, transport: httpx.MockTransport) -> None:  # type: ignore[no-untyped-def]
    client = GitHubClient(
        base_url="https://api.github.test", timeout_seconds=2.0, transport=transport
    )
    app.dependency_overrides[get_github_client] = lambda: client


def _make_submission(db, user, challenge=None):  # type: ignore[no-untyped-def]
    challenge = challenge or factories.make_challenge(db, max_points=100)
    return factories.make_submission(
        db, user=user, challenge=challenge, repo_full_name=REPO_FULL_NAME
    )


def _evaluation_count(db) -> int:  # type: ignore[no-untyped-def]
    return db.execute(select(func.count()).select_from(Evaluation)).scalar_one()


# --- happy path -------------------------------------------------------------------


def test_trigger_runs_evaluation_and_scores_submission(client, app, db, make_user, login):
    _mock_github(app, _transport())
    user = make_user(username="evaluated")
    submission = _make_submission(db, user)
    login(client, user)

    response = client.post(f"/api/v1/submissions/{submission.id}/evaluate")

    assert response.status_code == 200
    body = response.json()
    assert body["submission"]["status"] == "passed"
    assert body["submission"]["evaluation_attempts"] == 1
    assert body["submission"]["evaluated_at"] is not None
    assert body["evaluation"]["status"] == "completed"
    assert body["evaluation"]["awarded_score"] == 100
    assert body["evaluation"]["max_score"] == 100
    statuses = {check["id"]: check["status"] for check in body["evaluation"]["checks"]}
    assert statuses == {"repo_accessible": "passed", "readme_present": "passed"}
    assert body["effective_points"] == 100
    assert body["counts_for_leaderboard"] is True
    assert _evaluation_count(db) == 1


def test_partial_credit_fails_required_gate_and_scores_partially(client, app, db, make_user, login):
    _mock_github(app, _transport(readme_status=404))
    user = make_user()
    submission = _make_submission(db, user)
    login(client, user)

    body = client.post(f"/api/v1/submissions/{submission.id}/evaluate").json()

    assert body["evaluation"]["status"] == "completed"
    assert body["evaluation"]["awarded_score"] == 40  # repo_accessible passed, readme failed
    statuses = {check["id"]: check["status"] for check in body["evaluation"]["checks"]}
    assert statuses == {"repo_accessible": "passed", "readme_present": "failed"}
    assert body["submission"]["status"] == "failed", "a failed required check fails the submission"
    assert body["effective_points"] == 40, "partial points are kept"
    assert body["counts_for_leaderboard"] is True


def test_private_repository_is_rejected_when_config_requires_public(
    client, app, db, make_user, login
):
    _mock_github(app, _transport(private=True))
    user = make_user()
    submission = _make_submission(db, user)
    login(client, user)

    body = client.post(f"/api/v1/submissions/{submission.id}/evaluate").json()

    assert body["submission"]["status"] == "failed"
    checks = body["evaluation"]["checks"]
    assert any(check["type"] == "repo_public" and check["status"] == "failed" for check in checks)


# --- idempotency and state machine ---------------------------------------------------------


def test_trigger_is_idempotent_once_final(client, app, db, make_user, login):
    _mock_github(app, _transport())
    user = make_user()
    submission = _make_submission(db, user)
    login(client, user)

    first = client.post(f"/api/v1/submissions/{submission.id}/evaluate")
    assert first.status_code == 200

    second = client.post(f"/api/v1/submissions/{submission.id}/evaluate")

    assert second.status_code == 202, "already-final evaluations are a no-op"
    assert second.json()["evaluation"]["awarded_score"] == 100
    assert _evaluation_count(db) == 1
    assert second.json()["submission"]["evaluation_attempts"] == 1


def test_running_submission_returns_202_without_reexecuting(client, db, make_user, login):
    user = make_user()
    submission = _make_submission(db, user)
    submission.status = SubmissionStatus.RUNNING
    db.flush()
    login(client, user)

    response = client.post(f"/api/v1/submissions/{submission.id}/evaluate")

    assert response.status_code == 202
    assert response.json()["evaluation"] is None
    assert _evaluation_count(db) == 0


def test_students_cannot_force_rerun(client, app, db, make_user, login):
    _mock_github(app, _transport())
    user = make_user()
    submission = _make_submission(db, user)
    login(client, user)

    assert client.post(f"/api/v1/submissions/{submission.id}/evaluate").status_code == 200
    forced = client.post(f"/api/v1/submissions/{submission.id}/evaluate?force=true")

    assert forced.status_code == 404
    assert _evaluation_count(db) == 1


def test_staff_force_rerun_creates_new_evaluation_and_audit_entry(
    client, app, db, make_user, login
):
    _mock_github(app, _transport())
    user = make_user(username="builder")
    submission = _make_submission(db, user)

    login(client, user)
    assert client.post(f"/api/v1/submissions/{submission.id}/evaluate").status_code == 200

    moderator = make_user(username="mod", role=UserRole.MODERATOR)
    login(client, moderator)
    response = client.post(f"/api/v1/submissions/{submission.id}/evaluate?force=true")

    assert response.status_code == 200
    assert response.json()["submission"]["evaluation_attempts"] == 2
    assert _evaluation_count(db) == 2
    entry = db.execute(
        select(AuditLog).where(AuditLog.action == "submission.force_evaluate")
    ).scalar_one()
    assert entry.actor_id == moderator.id
    assert entry.target_id == str(submission.id)


def test_other_users_cannot_trigger_or_read_results(client, db, make_user, login):
    owner = make_user(username="owner")
    submission = _make_submission(db, owner)

    login(client, make_user(username="stranger"))
    assert client.post(f"/api/v1/submissions/{submission.id}/evaluate").status_code == 404
    assert client.get(f"/api/v1/submissions/{submission.id}/results").status_code == 404
    assert _evaluation_count(db) == 0


def test_probe_failure_marks_evaluation_and_submission_errored(client, app, db, make_user, login):
    _mock_github(app, _transport(repo_status=500))
    user = make_user()
    submission = _make_submission(db, user)
    login(client, user)

    response = client.post(f"/api/v1/submissions/{submission.id}/evaluate")

    assert response.status_code == 200
    body = response.json()
    assert body["evaluation"]["status"] == "error"
    assert body["submission"]["status"] == "error"
    assert body["evaluation"]["awarded_score"] == 0
    assert body["counts_for_leaderboard"] is False
    assert all(check["status"] == "error" for check in body["evaluation"]["checks"])

    # Errored evaluations may be retried (staff force); the submission is not final.
    moderator = make_user(username="mod", role=UserRole.MODERATOR)
    login(client, moderator)
    retry = client.post(f"/api/v1/submissions/{submission.id}/evaluate?force=true")
    assert retry.status_code == 200


# --- badge awarding -------------------------------------------------------------------------


def test_successful_evaluation_awards_badges_idempotently(client, app, db, make_user, login):
    BadgeService(db).seed_defaults()
    _mock_github(app, _transport())
    user = make_user(username="badged")
    submission = _make_submission(db, user)
    login(client, user)

    assert client.post(f"/api/v1/submissions/{submission.id}/evaluate").status_code == 200

    badges = client.get("/api/v1/users/badged/badges").json()
    slugs = {entry["badge"]["slug"] for entry in badges}
    assert {"first-submission", "first-challenge", "perfect-build"} <= slugs

    moderator = make_user(username="mod", role=UserRole.MODERATOR)
    login(client, moderator)
    assert (
        client.post(f"/api/v1/submissions/{submission.id}/evaluate?force=true").status_code == 200
    )

    after = client.get("/api/v1/users/badged/badges").json()
    assert len(after) == len(badges), "re-evaluation must not duplicate awards"
