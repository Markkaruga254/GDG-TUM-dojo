"""Admin endpoint tests: RBAC, user management, moderation, audit trail, badges."""

from __future__ import annotations

from sqlalchemy import select

from app.core.security import generate_token, hash_token
from app.models import AuditLog, UserRole
from app.repositories.audit import SessionRepository
from tests import factories


def _login_admin(db, make_user, client, login):  # type: ignore[no-untyped-def]
    admin = make_user(username="rootadmin", role=UserRole.ADMIN)
    login(client, admin)
    return admin


# --- RBAC --------------------------------------------------------------------------------


def test_admin_rbac_matrix(client, db, make_user, login):
    student = make_user(username="plainstudent")
    login(client, student)
    assert client.get("/api/v1/admin/users").status_code == 403

    moderator = make_user(username="moderator", role=UserRole.MODERATOR)
    login(client, moderator)
    assert client.get("/api/v1/admin/users").status_code == 200
    assert client.get("/api/v1/admin/audit-logs").status_code == 403, "audit is admin-only"
    assert (
        client.patch(
            f"/api/v1/admin/users/{student.id}/role", json={"role": "moderator"}
        ).status_code
        == 403
    ), "role changes are admin-only"

    admin = make_user(username="adminuser", role=UserRole.ADMIN)
    login(client, admin)
    changed = client.patch(
        f"/api/v1/admin/users/{student.id}/role",
        json={"role": "moderator", "reason": "Promoted for event duty"},
    )
    assert changed.status_code == 200
    assert changed.json()["role"] == "moderator"


# --- user management ---------------------------------------------------------------------


def test_list_users_filters(client, db, make_user, login):
    make_user(username="alice")
    make_user(username="bob", role=UserRole.MODERATOR)
    make_user(username="carol", is_active=False)
    _login_admin(db, make_user, client, login)

    by_search = client.get("/api/v1/admin/users?search=ali").json()
    assert [user["github_username"] for user in by_search["items"]] == ["alice"]

    by_role = client.get("/api/v1/admin/users?role=moderator").json()
    assert by_role["total"] == 1
    assert by_role["items"][0]["github_username"] == "bob"

    inactive = client.get("/api/v1/admin/users?is_active=false").json()
    assert {user["github_username"] for user in inactive["items"]} == {"carol"}


def test_role_change_is_audited_and_self_change_rejected(client, db, make_user, login):
    admin = _login_admin(db, make_user, client, login)
    target = make_user(username="target")

    response = client.patch(
        f"/api/v1/admin/users/{target.id}/role",
        json={"role": "moderator", "reason": "Event moderation"},
    )

    assert response.status_code == 200
    entry = db.execute(select(AuditLog).where(AuditLog.action == "user.role_change")).scalar_one()
    assert entry.actor_id == admin.id
    assert entry.log_metadata["previous_role"] == "student"
    assert entry.log_metadata["new_role"] == "moderator"

    self_change = client.patch(f"/api/v1/admin/users/{admin.id}/role", json={"role": "student"})
    assert self_change.status_code == 409


def test_status_change_revokes_sessions_and_blocks_login(
    client, db, make_user, login, revoked_session
):
    _login_admin(db, make_user, client, login)
    target = make_user(username="tofreeze")
    raw_token = generate_token(16)
    SessionRepository(db).create(
        user_id=target.id, token_hash=hash_token(raw_token), expires_at=factories.future_expiry()
    )
    db.flush()

    response = client.patch(
        f"/api/v1/admin/users/{target.id}/status",
        json={"is_active": False, "reason": "Code of conduct"},
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is False
    assert revoked_session(raw_token)

    login(client, target)
    assert client.get("/api/v1/auth/me").status_code == 401


def test_admin_cannot_deactivate_self(client, db, make_user, login):
    admin = _login_admin(db, make_user, client, login)

    response = client.patch(f"/api/v1/admin/users/{admin.id}/status", json={"is_active": False})

    assert response.status_code == 409


def test_user_management_unknown_user_is_404(client, db, make_user, login):
    _login_admin(db, make_user, client, login)

    response = client.patch(
        "/api/v1/admin/users/00000000-0000-0000-0000-000000000000/role",
        json={"role": "moderator"},
    )

    assert response.status_code == 404


# --- submission moderation ------------------------------------------------------------------


def test_disqualify_and_reinstate_flow(client, db, make_user, login):
    moderator = make_user(username="mod", role=UserRole.MODERATOR)
    owner = make_user(username="offender")
    challenge = factories.make_challenge(db, max_points=100)
    submission = factories.finalize_submission(db, user=owner, challenge=challenge, points=90)
    login(client, moderator)

    disqualified = client.post(
        f"/api/v1/admin/submissions/{submission.id}/disqualify",
        json={"reason": "Plagiarized repository"},
    )
    assert disqualified.status_code == 200
    assert disqualified.json()["is_disqualified"] is True
    assert disqualified.json()["disqualification_reason"] == "Plagiarized repository"

    again = client.post(
        f"/api/v1/admin/submissions/{submission.id}/disqualify",
        json={"reason": "Second attempt"},
    )
    assert again.status_code == 409

    assert client.get("/api/v1/leaderboard").json()["total"] == 0

    reinstated = client.post(f"/api/v1/admin/submissions/{submission.id}/reinstate")
    assert reinstated.status_code == 200
    assert reinstated.json()["is_disqualified"] is False
    assert client.get("/api/v1/leaderboard").json()["total"] == 1

    assert client.post(f"/api/v1/admin/submissions/{submission.id}/reinstate").status_code == 409


def test_disqualification_requires_a_meaningful_reason(client, db, make_user, login):
    moderator = make_user(username="mod", role=UserRole.MODERATOR)
    owner = make_user()
    submission = factories.finalize_submission(
        db, user=owner, challenge=factories.make_challenge(db), points=10
    )
    login(client, moderator)

    response = client.post(
        f"/api/v1/admin/submissions/{submission.id}/disqualify", json={"reason": "no"}
    )

    assert response.status_code == 422


def test_score_override_flow(client, db, make_user, login):
    admin = _login_admin(db, make_user, client, login)
    owner = make_user()
    challenge = factories.make_challenge(db, max_points=100)
    submission = factories.finalize_submission(db, user=owner, challenge=challenge, points=40)

    overridden = client.post(
        f"/api/v1/admin/submissions/{submission.id}/score",
        json={"points": 75, "reason": "Manual verification of extra work"},
    )
    assert overridden.status_code == 200
    body = overridden.json()
    assert body["score_override_points"] == 75
    assert body["effective_points"] == 75
    entry = db.execute(
        select(AuditLog).where(AuditLog.action == "submission.score_override")
    ).scalar_one()
    assert entry.actor_id == admin.id

    too_high = client.post(
        f"/api/v1/admin/submissions/{submission.id}/score",
        json={"points": 101, "reason": "Beyond maximum"},
    )
    assert too_high.status_code == 422

    cleared = client.delete(f"/api/v1/admin/submissions/{submission.id}/score-override")
    assert cleared.status_code == 200
    assert cleared.json()["score_override_points"] is None
    assert cleared.json()["effective_points"] == 40

    assert (
        client.delete(f"/api/v1/admin/submissions/{submission.id}/score-override").status_code
        == 409
    )


def test_moderator_cannot_override_scores(client, db, make_user, login):
    moderator = make_user(username="mod", role=UserRole.MODERATOR)
    owner = make_user()
    submission = factories.finalize_submission(
        db, user=owner, challenge=factories.make_challenge(db), points=10
    )
    login(client, moderator)

    response = client.post(
        f"/api/v1/admin/submissions/{submission.id}/score",
        json={"points": 50, "reason": "Moderator attempt"},
    )

    assert response.status_code == 403, "score overrides are admin-only"


def test_list_challenge_submissions_requires_id_and_returns_page(client, db, make_user, login):
    moderator = make_user(username="mod", role=UserRole.MODERATOR)
    owner = make_user()
    challenge = factories.make_challenge(db)
    factories.finalize_submission(db, user=owner, challenge=challenge, points=10)
    login(client, moderator)

    missing = client.get("/api/v1/admin/submissions")
    assert missing.status_code == 422

    page = client.get(f"/api/v1/admin/submissions?challenge_id={challenge.id}")
    assert page.status_code == 200
    assert page.json()["total"] == 1


# --- audit trail --------------------------------------------------------------------------------


def test_audit_trail_records_and_filters(client, db, make_user, login):
    admin = _login_admin(db, make_user, client, login)
    target = make_user(username="audited")
    client.patch(
        f"/api/v1/admin/users/{target.id}/role",
        json={"role": "moderator", "reason": "Promotion"},
    )

    all_entries = client.get("/api/v1/admin/audit-logs").json()
    assert all_entries["total"] >= 1
    entry = all_entries["items"][0]
    assert entry["action"] == "user.role_change"
    assert entry["actor_username"] == admin.github_username

    filtered = client.get("/api/v1/admin/audit-logs?action=user.role_change").json()
    assert filtered["total"] == 1

    unrelated = client.get("/api/v1/admin/audit-logs?action=badge.create").json()
    assert unrelated["total"] == 0


# --- badges ----------------------------------------------------------------------------


def test_admin_badge_lifecycle(client, db, make_user, login):
    _login_admin(db, make_user, client, login)
    target = make_user(username="receiver")

    created = client.post(
        "/api/v1/admin/badges",
        json={
            "slug": "community-hero",
            "name": "Community Hero",
            "description": "Helped other teams ship.",
            "icon": "heart",
            "criteria": {
                "description": "Awarded manually.",
                "rule": {"type": "challenges_passed", "count": 1},
            },
        },
    )
    assert created.status_code == 201

    duplicate = client.post(
        "/api/v1/admin/badges",
        json={
            "slug": "community-hero",
            "name": "Community Hero Duplicate",
            "description": "Should conflict.",
            "icon": "heart",
            "criteria": {
                "description": "Awarded manually.",
                "rule": {"type": "challenges_passed", "count": 1},
            },
        },
    )
    assert duplicate.status_code == 409

    updated = client.patch(
        f"/api/v1/admin/badges/{created.json()['id']}", json={"name": "Community Hero Plus"}
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Community Hero Plus"

    granted = client.post(
        f"/api/v1/admin/users/{target.id}/badges/community-hero",
        json={"reason": "Stellar community support"},
    )
    assert granted.status_code == 200
    assert granted.json()["message"] == "Badge granted."

    again = client.post(f"/api/v1/admin/users/{target.id}/badges/community-hero", json={})
    assert again.status_code == 200
    assert again.json()["message"] == "User already has this badge."

    unknown = client.post(f"/api/v1/admin/users/{target.id}/badges/nope", json={})
    assert unknown.status_code == 404

    listed = client.get("/api/v1/users/receiver/badges").json()
    assert [entry["badge"]["slug"] for entry in listed] == ["community-hero"]


def test_badge_creation_rejects_invalid_criteria(client, db, make_user, login):
    _login_admin(db, make_user, client, login)

    response = client.post(
        "/api/v1/admin/badges",
        json={
            "slug": "broken-badge",
            "name": "Broken Badge",
            "description": "Invalid rule type.",
            "icon": "bug",
            "criteria": {"description": "Nope.", "rule": {"type": "not_a_rule", "count": 1}},
        },
    )

    assert response.status_code == 422
