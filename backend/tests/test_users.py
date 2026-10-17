"""User endpoint tests: self-service profile, public profile, portfolio."""

from __future__ import annotations

from app.models import ChallengeStatus, UserRole
from tests import factories

# --- self service -----------------------------------------------------------------


def test_me_requires_authentication(client):
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"


def test_update_profile_fields(client, make_user, login):
    user = make_user(username="updater")
    login(client, user)

    response = client.patch(
        "/api/v1/users/me",
        json={"display_name": "New Name", "bio": "Builds clouds"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["display_name"] == "New Name"
    assert body["bio"] == "Builds clouds"
    assert body["github_username"] == "updater"


def test_update_profile_rejects_unknown_and_privileged_fields(client, db, make_user, login):
    user = make_user(username="privilege")
    login(client, user)

    response = client.patch("/api/v1/users/me", json={"role": "admin"})

    assert response.status_code == 422
    db.refresh(user)
    assert user.role is UserRole.STUDENT


def test_display_name_can_be_cleared_with_explicit_null(client, make_user, login):
    user = make_user(username="clearname", display_name="Old Name")
    login(client, user)

    response = client.patch("/api/v1/users/me", json={"display_name": None})

    assert response.status_code == 200
    assert response.json()["display_name"] is None


def test_empty_patch_is_a_noop(client, make_user, login):
    user = make_user(username="noop", display_name="Keep Me")
    login(client, user)

    response = client.patch("/api/v1/users/me", json={})

    assert response.status_code == 200
    assert response.json()["display_name"] == "Keep Me"


# --- public profile ---------------------------------------------------------------


def test_public_profile_reports_rank_and_stats(client, db, make_user):
    user = make_user(username="profiled")
    rival = make_user(username="rival")
    challenge = factories.make_challenge(db, max_points=100)
    factories.finalize_submission(db, user=user, challenge=challenge, points=80)
    factories.finalize_submission(db, user=rival, challenge=challenge, points=100)

    response = client.get("/api/v1/users/profiled/profile")

    assert response.status_code == 200
    body = response.json()
    assert body["user"]["github_username"] == "profiled"
    assert "role" not in body["user"]
    assert body["stats"]["total_points"] == 80
    assert body["stats"]["completed_challenges"] == 1
    assert body["stats"]["submissions_passed"] == 1
    assert body["stats"]["global_rank"] == 2


def test_profile_unknown_user_is_404(client):
    response = client.get("/api/v1/users/nobody-here/profile")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_portfolio_keeps_best_attempt_per_challenge(client, db, make_user):
    user = make_user(username="portfolio")
    challenge = factories.make_challenge(db, max_points=100, slug="portfolio-challenge")
    factories.finalize_submission(
        db, user=user, challenge=challenge, points=40, repo_full_name="portfolio/low"
    )
    factories.finalize_submission(
        db, user=user, challenge=challenge, points=90, repo_full_name="portfolio/high"
    )

    response = client.get("/api/v1/users/portfolio/portfolio")

    assert response.status_code == 200
    entries = response.json()["entries"]
    assert len(entries) == 1
    assert entries[0]["points"] == 90
    assert entries[0]["challenge_slug"] == "portfolio-challenge"
    assert entries[0]["max_points"] == 100


def test_portfolio_excludes_disqualified_and_draft_entries(client, db, make_user):
    user = make_user(username="portexcl")
    published = factories.make_challenge(db, max_points=100, slug="pub-ch")
    draft = factories.make_challenge(
        db, status=ChallengeStatus.DRAFT, max_points=100, slug="draft-ch"
    )
    factories.finalize_submission(db, user=user, challenge=published, points=50)
    factories.finalize_submission(db, user=user, challenge=draft, points=70)
    factories.finalize_submission(
        db, user=user, challenge=published, points=30, is_disqualified=True
    )

    response = client.get("/api/v1/users/portexcl/portfolio")

    assert response.status_code == 200
    entries = response.json()["entries"]
    assert len(entries) == 1
    assert entries[0]["points"] == 50
    assert entries[0]["challenge_slug"] == "pub-ch"
