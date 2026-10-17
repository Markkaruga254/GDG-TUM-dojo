"""Submission endpoint tests: creation rules, ownership, listing and results."""

from __future__ import annotations

from datetime import timedelta

from app.models import ChallengeStatus, SubmissionStatus, UserRole
from tests import factories

REPO_URL = "https://github.com/arena/demo"


# --- creation ----------------------------------------------------------------------


def test_create_submission_requires_authentication(client, db):
    challenge = factories.make_challenge(db)
    response = client.post(
        f"/api/v1/challenges/{challenge.id}/submissions", json={"repo_url": REPO_URL}
    )

    assert response.status_code == 401


def test_create_submission_stores_canonical_state(client, db, make_user, login):
    user = make_user(username="submitter")
    challenge = factories.make_challenge(db, max_points=100)
    login(client, user)

    response = client.post(
        f"/api/v1/challenges/{challenge.id}/submissions",
        json={
            "repo_url": REPO_URL + ".git",
            "notes": "  Built with Terraform  ",
            "evidence_urls": ["https://example.com/screenshot.png"],
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pending"
    assert body["repo_url"] == REPO_URL
    assert body["repo_full_name"] == "arena/demo"
    assert body["notes"] == "Built with Terraform"
    assert body["evidence_urls"] == ["https://example.com/screenshot.png"]
    assert body["user_id"] == str(user.id)
    assert body["effective_points"] == 0


def test_create_submission_rejects_unknown_challenge(client, make_user, login):
    login(client, make_user())
    response = client.post(
        "/api/v1/challenges/00000000-0000-0000-0000-000000000000/submissions",
        json={"repo_url": REPO_URL},
    )

    assert response.status_code == 404


def test_create_submission_respects_challenge_window(client, db, make_user, login):
    login(client, make_user())
    now = factories.now()
    not_started = factories.make_challenge(
        db, slug="future-challenge", starts_at=now + timedelta(days=1)
    )
    closed = factories.make_challenge(db, slug="closed-challenge", ends_at=now - timedelta(days=1))
    draft = factories.make_challenge(db, slug="draft-challenge", status=ChallengeStatus.DRAFT)

    for challenge, expected_code in (
        (not_started, "challenge_not_started"),
        (closed, "challenge_closed"),
        (draft, "challenge_not_published"),
    ):
        response = client.post(
            f"/api/v1/challenges/{challenge.id}/submissions", json={"repo_url": REPO_URL}
        )
        assert response.status_code == 422, challenge.slug
        assert response.json()["error"]["code"] == expected_code


def test_create_submission_validates_repo_and_evidence_urls(client, db, make_user, login):
    challenge = factories.make_challenge(db)
    login(client, make_user())

    bad_repo = client.post(
        f"/api/v1/challenges/{challenge.id}/submissions",
        json={"repo_url": "https://gitlab.com/arena/demo"},
    )
    assert bad_repo.status_code == 422

    bad_evidence = client.post(
        f"/api/v1/challenges/{challenge.id}/submissions",
        json={"repo_url": REPO_URL, "evidence_urls": ["ftp://example.com/file"]},
    )
    assert bad_evidence.status_code == 422

    too_many = client.post(
        f"/api/v1/challenges/{challenge.id}/submissions",
        json={
            "repo_url": REPO_URL,
            "evidence_urls": [f"https://example.com/{index}.png" for index in range(6)],
        },
    )
    assert too_many.status_code == 422

    duplicate = client.post(
        f"/api/v1/challenges/{challenge.id}/submissions",
        json={"repo_url": REPO_URL, "evidence_urls": ["https://a.test/x", "https://a.test/x"]},
    )
    assert duplicate.status_code == 422


def test_duplicate_pending_submission_is_conflict(client, db, make_user, login):
    user = make_user()
    challenge = factories.make_challenge(db)
    login(client, user)

    first = client.post(
        f"/api/v1/challenges/{challenge.id}/submissions", json={"repo_url": REPO_URL}
    )
    assert first.status_code == 201

    second = client.post(
        f"/api/v1/challenges/{challenge.id}/submissions", json={"repo_url": REPO_URL}
    )
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "conflict"


def test_submission_cooldown_blocks_rapid_resubmission(client, db, make_user, login):
    user = make_user()
    challenge = factories.make_challenge(db)
    factories.finalize_submission(
        db,
        user=user,
        challenge=challenge,
        points=10,
        repo_full_name="arena/first-attempt",
        submitted_at=factories.now(),
    )
    login(client, user)

    response = client.post(
        f"/api/v1/challenges/{challenge.id}/submissions", json={"repo_url": REPO_URL}
    )

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "rate_limited"
    assert response.json()["error"]["details"][0]["retry_after_seconds"] > 0


def test_resubmission_allowed_after_cooldown(client, db, make_user, login):
    user = make_user()
    challenge = factories.make_challenge(db)
    factories.finalize_submission(
        db,
        user=user,
        challenge=challenge,
        points=10,
        repo_full_name="arena/old-attempt",
        submitted_at=factories.now() - timedelta(hours=2),
    )
    login(client, user)

    response = client.post(
        f"/api/v1/challenges/{challenge.id}/submissions", json={"repo_url": REPO_URL}
    )

    assert response.status_code == 201


def test_daily_submission_limit_is_enforced(client, db, make_user, login):
    user = make_user()
    challenge = factories.make_challenge(db)
    for index in range(10):
        factories.make_submission(
            db,
            user=user,
            challenge=challenge,
            repo_full_name=f"arena/attempt-{index}",
            submitted_at=factories.now() - timedelta(hours=3),
        )
    login(client, user)

    response = client.post(
        f"/api/v1/challenges/{challenge.id}/submissions", json={"repo_url": REPO_URL}
    )

    assert response.status_code == 429
    assert response.json()["error"]["details"][0]["limit"] == 10


# --- listing --------------------------------------------------------------------------


def test_list_my_submissions_filters_by_owner_and_status(client, db, make_user, login):
    user = make_user(username="lister")
    other = make_user(username="otheruser")
    challenge = factories.make_challenge(db)
    other_challenge = factories.make_challenge(db)
    factories.finalize_submission(db, user=user, challenge=challenge, points=50)
    factories.make_submission(db, user=user, challenge=other_challenge)
    factories.finalize_submission(db, user=other, challenge=challenge, points=99)
    login(client, user)

    everything = client.get("/api/v1/users/me/submissions").json()
    assert everything["total"] == 2
    assert {item["user_id"] for item in everything["items"]} == {str(user.id)}

    passed = client.get("/api/v1/users/me/submissions?status=passed").json()
    assert passed["total"] == 1
    assert passed["items"][0]["status"] == "passed"

    scoped = client.get(f"/api/v1/users/me/submissions?challenge_id={other_challenge.id}").json()
    assert scoped["total"] == 1
    assert scoped["items"][0]["challenge_id"] == str(other_challenge.id)


# --- detail access -------------------------------------------------------------------------


def test_submission_detail_is_owner_or_staff_only(client, db, make_user, login):
    owner = make_user(username="owner")
    challenge = factories.make_challenge(db)
    submission = factories.make_submission(db, user=owner, challenge=challenge)

    login(client, make_user(username="stranger"))
    assert client.get(f"/api/v1/submissions/{submission.id}").status_code == 404, (
        "existence must not leak to other students"
    )

    login(client, make_user(username="mod", role=UserRole.MODERATOR))
    staff_view = client.get(f"/api/v1/submissions/{submission.id}")
    assert staff_view.status_code == 200

    login(client, owner)
    owner_view = client.get(f"/api/v1/submissions/{submission.id}")
    assert owner_view.status_code == 200
    assert owner_view.json()["id"] == str(submission.id)


def test_results_before_evaluation_are_empty(client, db, make_user, login):
    user = make_user()
    challenge = factories.make_challenge(db, max_points=100)
    submission = factories.make_submission(db, user=user, challenge=challenge)
    login(client, user)

    response = client.get(f"/api/v1/submissions/{submission.id}/results")

    assert response.status_code == 200
    body = response.json()
    assert body["evaluation"] is None
    assert body["effective_points"] == 0
    assert body["counts_for_leaderboard"] is False
    assert body["max_points"] == 100
    assert body["challenge_slug"] == challenge.slug


def test_results_reflect_override_and_disqualification(client, db, make_user, login):
    user = make_user()
    challenge = factories.make_challenge(db, max_points=100)
    overridden = factories.finalize_submission(
        db, user=user, challenge=challenge, points=40, repo_full_name="arena/override"
    )
    overridden.score_override_points = 75
    disqualified = factories.finalize_submission(
        db,
        user=user,
        challenge=challenge,
        points=90,
        repo_full_name="arena/disqualified",
        is_disqualified=True,
    )
    db.flush()
    login(client, user)

    override_body = client.get(f"/api/v1/submissions/{overridden.id}/results").json()
    assert override_body["effective_points"] == 75
    assert override_body["evaluation"]["awarded_score"] == 40
    assert override_body["counts_for_leaderboard"] is True

    disqualified_body = client.get(f"/api/v1/submissions/{disqualified.id}/results").json()
    assert disqualified_body["counts_for_leaderboard"] is False
    assert disqualified_body["submission"]["is_disqualified"] is True


def test_results_exclude_draft_challenges_from_leaderboard(client, db, make_user, login):
    user = make_user()
    challenge = factories.make_challenge(db, status=ChallengeStatus.DRAFT)
    submission = factories.finalize_submission(db, user=user, challenge=challenge, points=50)
    login(client, user)

    body = client.get(f"/api/v1/submissions/{submission.id}/results").json()

    assert body["submission"]["status"] == "passed"
    assert body["counts_for_leaderboard"] is False


def test_submission_summary_lists_effective_points(client, db, make_user, login):
    user = make_user()
    challenge = factories.make_challenge(db)
    submission = factories.make_submission(
        db,
        user=user,
        challenge=challenge,
        status=SubmissionStatus.RUNNING,
    )
    login(client, user)

    body = client.get("/api/v1/users/me/submissions").json()

    assert body["total"] == 1
    assert body["items"][0]["id"] == str(submission.id)
    assert body["items"][0]["status"] == "running"
    assert body["items"][0]["effective_points"] == 0
