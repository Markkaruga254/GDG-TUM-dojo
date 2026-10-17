"""Leaderboard endpoint tests: ranking policy, filters and personal standing."""

from __future__ import annotations

from datetime import timedelta

from app.models import ChallengeStatus
from tests import factories


def test_leaderboard_ranks_by_total_points(client, db, make_user):
    leader = make_user(username="leader")
    runner_up = make_user(username="runner")
    make_user(username="nosubs")
    challenge = factories.make_challenge(db, max_points=100)
    factories.finalize_submission(db, user=leader, challenge=challenge, points=90)
    factories.finalize_submission(db, user=runner_up, challenge=challenge, points=40)

    body = client.get("/api/v1/leaderboard").json()

    usernames = [entry["github_username"] for entry in body["items"]]
    assert usernames[0] == "leader"
    assert usernames[1] == "runner"
    assert "nosubs" not in usernames
    assert body["items"][0]["rank"] == 1
    assert body["items"][0]["total_points"] == 90
    assert body["items"][1]["rank"] == 2


def test_best_attempt_per_challenge_is_counted_once(client, db, make_user):
    user = make_user(username="retrier")
    challenge = factories.make_challenge(db, max_points=100)
    factories.finalize_submission(
        db, user=user, challenge=challenge, points=40, repo_full_name="arena/first"
    )
    factories.finalize_submission(
        db, user=user, challenge=challenge, points=90, repo_full_name="arena/best"
    )

    entry = client.get("/api/v1/leaderboard").json()["items"][0]

    assert entry["total_points"] == 90, "only the best attempt counts"
    assert entry["completed_challenges"] == 1


def test_disqualified_and_draft_results_are_excluded(client, db, make_user):
    clean = make_user(username="clean")
    cheater = make_user(username="cheater")
    drafts = make_user(username="drafter")
    published = factories.make_challenge(db, max_points=100, slug="published-ch")
    draft = factories.make_challenge(db, status=ChallengeStatus.DRAFT, slug="hidden-ch")
    factories.finalize_submission(db, user=clean, challenge=published, points=30)
    factories.finalize_submission(
        db, user=cheater, challenge=published, points=95, is_disqualified=True
    )
    factories.finalize_submission(db, user=drafts, challenge=draft, points=99)

    usernames = [
        entry["github_username"] for entry in client.get("/api/v1/leaderboard").json()["items"]
    ]

    assert usernames == ["clean"]


def test_archived_challenge_points_still_count(client, db, make_user):
    user = make_user(username="archivist")
    archived = factories.make_challenge(db, status=ChallengeStatus.ARCHIVED, max_points=100)
    factories.finalize_submission(db, user=user, challenge=archived, points=70)

    body = client.get("/api/v1/leaderboard").json()

    assert body["total"] == 1
    assert body["items"][0]["total_points"] == 70


def test_inactive_users_are_excluded(client, db, make_user):
    active = make_user(username="active")
    banned = make_user(username="banned", is_active=False)
    challenge = factories.make_challenge(db, max_points=100)
    factories.finalize_submission(db, user=active, challenge=challenge, points=10)
    factories.finalize_submission(db, user=banned, challenge=challenge, points=95)

    usernames = [
        entry["github_username"] for entry in client.get("/api/v1/leaderboard").json()["items"]
    ]

    assert usernames == ["active"]


def test_failed_but_scored_submission_counts(client, db, make_user):
    user = make_user(username="partially")
    challenge = factories.make_challenge(db, max_points=100)
    factories.finalize_submission(db, user=user, challenge=challenge, points=40, passed=False)

    entry = client.get("/api/v1/leaderboard").json()["items"][0]

    assert entry["total_points"] == 40
    assert entry["completed_challenges"] == 1


def test_admin_override_changes_leaderboard_total(client, db, make_user):
    user = make_user(username="corrected")
    challenge = factories.make_challenge(db, max_points=100)
    submission = factories.finalize_submission(db, user=user, challenge=challenge, points=40)
    submission.score_override_points = 85
    db.flush()

    entry = client.get("/api/v1/leaderboard").json()["items"][0]

    assert entry["total_points"] == 85


def test_tie_break_prefers_more_completed_challenges(client, db, make_user):
    broad = make_user(username="broad")
    deep = make_user(username="deep")
    first = factories.make_challenge(db, max_points=100, slug="first-ch")
    second = factories.make_challenge(db, max_points=100, slug="second-ch")
    factories.finalize_submission(
        db,
        user=broad,
        challenge=first,
        points=50,
        evaluated_at=factories.now() - timedelta(hours=3),
    )
    factories.finalize_submission(
        db,
        user=broad,
        challenge=second,
        points=50,
        evaluated_at=factories.now() - timedelta(hours=1),
    )
    factories.finalize_submission(
        db,
        user=deep,
        challenge=first,
        points=100,
        evaluated_at=factories.now() - timedelta(hours=5),
    )

    usernames = [
        entry["github_username"] for entry in client.get("/api/v1/leaderboard").json()["items"]
    ]

    assert usernames == ["broad", "deep"], "same total → more completed challenges wins"


def test_tie_break_prefers_earlier_achievement(client, db, make_user):
    earlier = make_user(username="earlier")
    later = make_user(username="later")
    challenge = factories.make_challenge(db, max_points=100)
    factories.finalize_submission(
        db,
        user=earlier,
        challenge=challenge,
        points=100,
        evaluated_at=factories.now() - timedelta(hours=2),
    )
    factories.finalize_submission(
        db,
        user=later,
        challenge=challenge,
        points=100,
        evaluated_at=factories.now() - timedelta(hours=1),
    )

    usernames = [
        entry["github_username"] for entry in client.get("/api/v1/leaderboard").json()["items"]
    ]

    assert usernames == ["earlier", "later"]


def test_track_filter_scopes_the_ranking(client, db, make_user):
    cloud_user = make_user(username="cloudy")
    web_user = make_user(username="webby")
    cloud = factories.make_challenge(db, track="cloud", max_points=100, slug="cloud-task")
    web = factories.make_challenge(db, track="web", max_points=100, slug="web-task")
    factories.finalize_submission(db, user=cloud_user, challenge=cloud, points=60)
    factories.finalize_submission(db, user=web_user, challenge=web, points=90)
    factories.finalize_submission(db, user=web_user, challenge=cloud, points=10)

    filtered = client.get("/api/v1/leaderboard?track=cloud").json()
    assert filtered["total"] == 2
    cloud_entry = next(item for item in filtered["items"] if item["github_username"] == "cloudy")
    assert cloud_entry["total_points"] == 60

    all_tracks = client.get("/api/v1/leaderboard").json()
    webby = next(item for item in all_tracks["items"] if item["github_username"] == "webby")
    assert webby["total_points"] == 100


def test_leaderboard_pagination(client, db, make_user):
    for index in range(3):
        user = make_user(username=f"paged{index}")
        challenge = factories.make_challenge(db, max_points=100)
        factories.finalize_submission(db, user=user, challenge=challenge, points=10 * (index + 1))

    first = client.get("/api/v1/leaderboard?page=1&page_size=2").json()

    assert first["total"] == 3
    assert first["pages"] == 2
    assert [entry["rank"] for entry in first["items"]] == [1, 2]

    second = client.get("/api/v1/leaderboard?page=2&page_size=2").json()
    assert [entry["rank"] for entry in second["items"]] == [3]


# --- personal standing ----------------------------------------------------------------


def test_my_leaderboard_requires_authentication(client):
    assert client.get("/api/v1/leaderboard/me").status_code == 401


def test_my_leaderboard_reports_rank_and_entries(client, db, make_user, login):
    user = make_user(username="myself")
    rival = make_user(username="rival")
    challenge = factories.make_challenge(db, max_points=100, slug="my-challenge")
    factories.finalize_submission(db, user=user, challenge=challenge, points=70)
    factories.finalize_submission(db, user=rival, challenge=challenge, points=80)
    login(client, user)

    body = client.get("/api/v1/leaderboard/me").json()

    assert body["rank"] == 2
    assert body["total_points"] == 70
    assert body["completed_challenges"] == 1
    assert len(body["entries"]) == 1
    assert body["entries"][0]["challenge_slug"] == "my-challenge"
    assert body["entries"][0]["points"] == 70
    assert body["entries"][0]["max_points"] == 100


def test_my_leaderboard_without_results_is_empty(client, make_user, login):
    login(client, make_user(username="fresh"))

    body = client.get("/api/v1/leaderboard/me").json()

    assert body["rank"] is None
    assert body["total_points"] == 0
    assert body["entries"] == []
