"""Badge tests: defaults, rule evaluation, listing and manual grants."""

from __future__ import annotations

import pytest

from app.core.errors import NotFound
from app.services.badges import BadgeService
from tests import factories

# --- defaults and listing ---------------------------------------------------------------


def test_seed_defaults_is_idempotent(client, db):
    service = BadgeService(db)

    created_first = service.seed_defaults()
    created_second = service.seed_defaults()

    assert created_first == 5
    assert created_second == 0

    body = client.get("/api/v1/badges").json()
    slugs = {badge["slug"] for badge in body}
    assert {
        "first-submission",
        "first-challenge",
        "five-challenges",
        "ten-challenges",
        "perfect-build",
    } == slugs
    assert all(badge["criteria"]["rule"]["type"] for badge in body)


def test_new_user_has_no_badges(client, db, make_user):
    make_user(username="freshbadge")

    body = client.get("/api/v1/users/freshbadge/badges").json()

    assert body == []


def test_user_badges_unknown_user_is_404(client):
    response = client.get("/api/v1/users/ghost/badges")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


# --- rule evaluation ----------------------------------------------------------------------


def test_rule_requires_finalized_submission(db, make_user):
    user = make_user()
    challenge = factories.make_challenge(db)
    badge = factories.make_badge(db, rule={"type": "submissions_finalized", "count": 1})

    factories.make_submission(db, user=user, challenge=challenge)  # pending: not final
    assert BadgeService(db).evaluate_awards(user) == []

    factories.finalize_submission(db, user=user, challenge=challenge, points=0, passed=False)
    awarded = BadgeService(db).evaluate_awards(user)

    assert [item.slug for item in awarded] == [badge.slug]


def test_rule_challenges_passed_counts_distinct_scored_challenges(db, make_user):
    user = make_user()
    first = factories.make_challenge(db)
    second = factories.make_challenge(db)
    badge = factories.make_badge(db, rule={"type": "challenges_passed", "count": 2})
    factories.finalize_submission(db, user=user, challenge=first, points=40)

    assert BadgeService(db).evaluate_awards(user) == [], "one challenge is not enough"

    factories.finalize_submission(db, user=user, challenge=second, points=60)
    awarded = BadgeService(db).evaluate_awards(user)

    assert [item.slug for item in awarded] == [badge.slug]


def test_rule_perfect_score_requires_full_marks(db, make_user):
    user = make_user()
    challenge = factories.make_challenge(db, max_points=100)
    badge = factories.make_badge(db, rule={"type": "perfect_scores", "count": 1})
    factories.finalize_submission(db, user=user, challenge=challenge, points=99)

    assert BadgeService(db).evaluate_awards(user) == []

    challenge.max_points = 99
    db.flush()
    awarded = BadgeService(db).evaluate_awards(user)

    assert [item.slug for item in awarded] == [badge.slug]


def test_rule_track_challenges_passed_scopes_to_track(db, make_user):
    user = make_user()
    cloud = factories.make_challenge(db, track="cloud")
    web = factories.make_challenge(db, track="web")
    badge = factories.make_badge(
        db, rule={"type": "track_challenges_passed", "count": 1, "track": "cloud"}
    )
    factories.finalize_submission(db, user=user, challenge=web, points=50)

    assert BadgeService(db).evaluate_awards(user) == [], "web points do not satisfy a cloud rule"

    factories.finalize_submission(db, user=user, challenge=cloud, points=10)
    awarded = BadgeService(db).evaluate_awards(user)

    assert [item.slug for item in awarded] == [badge.slug]


def test_disqualified_submissions_do_not_award_badges(db, make_user):
    user = make_user()
    challenge = factories.make_challenge(db)
    factories.make_badge(db, rule={"type": "challenges_passed", "count": 1})
    factories.finalize_submission(
        db, user=user, challenge=challenge, points=90, is_disqualified=True
    )

    assert BadgeService(db).evaluate_awards(user) == []


def test_inactive_badges_are_not_awarded(db, make_user):
    user = make_user()
    challenge = factories.make_challenge(db)
    factories.make_badge(db, rule={"type": "challenges_passed", "count": 1}, is_active=False)
    factories.finalize_submission(db, user=user, challenge=challenge, points=90)

    assert BadgeService(db).evaluate_awards(user) == []


def test_evaluation_is_idempotent(db, make_user):
    user = make_user()
    challenge = factories.make_challenge(db)
    factories.make_badge(db, rule={"type": "challenges_passed", "count": 1})
    factories.finalize_submission(db, user=user, challenge=challenge, points=90)

    first = BadgeService(db).evaluate_awards(user)
    second = BadgeService(db).evaluate_awards(user)

    assert len(first) == 1
    assert second == []

    awards = BadgeService(db).list_for_user(user)
    assert len(awards) == 1
    assert awards[0][0].slug == first[0].slug


# --- manual grants ----------------------------------------------------------------------------


def test_manual_grant_is_idempotent_and_audited(db, make_user):
    actor = make_user(username="moderator")
    target = make_user(username="granted")
    badge = factories.make_badge(db)
    service = BadgeService(db)

    assert service.grant_badge(actor, target, badge.slug, "Helped another team") is True
    assert service.grant_badge(actor, target, badge.slug, None) is False

    awards = service.list_for_user(target)
    assert len(awards) == 1
    assert awards[0][0].slug == badge.slug


def test_grant_unknown_badge_is_404_level_error(db, make_user):
    actor = make_user()
    target = make_user()

    with pytest.raises(NotFound) as excinfo:
        BadgeService(db).grant_badge(actor, target, "does-not-exist", None)

    assert excinfo.value.code == "not_found"
