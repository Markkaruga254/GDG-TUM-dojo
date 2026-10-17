"""Challenge endpoint tests: visibility, filters, authoring and moderation."""

from __future__ import annotations

from sqlalchemy import select

from app.models import AuditLog, Challenge, ChallengeStatus, Difficulty, UserRole
from tests import factories

EVAL_CONFIG = {
    "version": 1,
    "checks": [
        {
            "id": "repo_accessible",
            "type": "repo_accessible",
            "description": "Repository is accessible.",
            "points": 40,
        },
        {
            "id": "readme_present",
            "type": "readme_present",
            "description": "README exists.",
            "points": 60,
        },
    ],
}


def _payload(**overrides):
    payload = {
        "title": "Build a Cloud Tracker",
        "description": "Deploy a working cloud cost tracker.",
        "instructions": "Use any cloud provider.",
        "track": "cloud",
        "difficulty": "beginner",
        "tags": ["gcp", "Terraform"],
        "max_points": 100,
        "evaluation_config": EVAL_CONFIG,
    }
    payload.update(overrides)
    return payload


# --- visibility and filters ------------------------------------------------------------


def test_list_shows_only_published_challenges_to_anonymous(client, db):
    factories.make_challenge(db, slug="pub-a")
    factories.make_challenge(db, slug="pub-b")
    factories.make_challenge(db, status=ChallengeStatus.DRAFT, slug="draft-a")

    response = client.get("/api/v1/challenges")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert {item["slug"] for item in body["items"]} == {"pub-a", "pub-b"}


def test_staff_sees_drafts_in_list(client, db, make_user, login):
    factories.make_challenge(db, slug="pub-a")
    factories.make_challenge(db, status=ChallengeStatus.DRAFT, slug="draft-a")

    anonymous = client.get("/api/v1/challenges").json()
    assert anonymous["total"] == 1

    login(client, make_user(username="mod", role=UserRole.MODERATOR))
    response = client.get("/api/v1/challenges")

    assert response.status_code == 200
    assert response.json()["total"] == 2


def test_filters_by_track_difficulty_tag_and_search(client, db):
    factories.make_challenge(
        db, slug="cloud-beginner", track="cloud", difficulty=Difficulty.BEGINNER
    )
    factories.make_challenge(db, slug="web-advanced", track="web", difficulty=Difficulty.ADVANCED)
    special = factories.make_challenge(
        db, slug="cloud-advanced", track="cloud", difficulty=Difficulty.ADVANCED
    )
    special.title = "Quantum Ledger Sprint"
    db.flush()

    cloud = client.get("/api/v1/challenges?track=cloud").json()
    assert {item["slug"] for item in cloud["items"]} == {"cloud-beginner", "cloud-advanced"}

    advanced = client.get("/api/v1/challenges?difficulty=advanced").json()
    assert {item["slug"] for item in advanced["items"]} == {"web-advanced", "cloud-advanced"}

    tagged = client.get("/api/v1/challenges?tag=test").json()
    assert tagged["total"] == 3

    searched = client.get("/api/v1/challenges?search=quantum").json()
    assert searched["total"] == 1
    assert searched["items"][0]["slug"] == "cloud-advanced"


def test_pagination_envelope_counts_pages(client, db):
    for index in range(3):
        factories.make_challenge(db, slug=f"paged-{index}")

    first = client.get("/api/v1/challenges?page=1&page_size=2").json()
    assert first["total"] == 3
    assert first["pages"] == 2
    assert first["page_size"] == 2
    assert len(first["items"]) == 2

    second = client.get("/api/v1/challenges?page=2&page_size=2").json()
    assert len(second["items"]) == 1


def test_draft_detail_is_hidden_from_public_but_visible_to_staff(client, db, make_user, login):
    factories.make_challenge(db, status=ChallengeStatus.DRAFT, slug="secret-draft")

    assert client.get("/api/v1/challenges/secret-draft").status_code == 404

    login(client, make_user(username="mod", role=UserRole.MODERATOR))
    response = client.get("/api/v1/challenges/secret-draft")

    assert response.status_code == 200
    assert response.json()["status"] == "draft"


def test_challenge_detail_exposes_check_summary_without_params(client, db):
    factories.make_challenge(db, slug="detailed")

    response = client.get("/api/v1/challenges/detailed")

    assert response.status_code == 200
    body = response.json()
    checks = body["evaluation"]
    assert len(checks) == 2
    assert {check["id"] for check in checks} == {"repo_accessible", "readme_present"}
    assert all("params" not in check for check in checks)


# --- authoring --------------------------------------------------------------------------


def test_create_challenge_requires_staff(client, make_user, login):
    login(client, make_user(username="student"))
    response = client.post("/api/v1/challenges", json=_payload())

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


def test_create_challenge_creates_draft_and_audit_entry(client, db, make_user, login):
    admin = make_user(username="admin", role=UserRole.ADMIN)
    login(client, admin)

    response = client.post("/api/v1/challenges", json=_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "draft"
    assert body["slug"] == "build-a-cloud-tracker"
    assert body["tags"] == ["gcp", "terraform"], "tags are normalized and sorted"
    assert body["created_by"] == "admin"

    entry = db.execute(select(AuditLog).where(AuditLog.action == "challenge.create")).scalar_one()
    assert entry.actor_id == admin.id
    assert entry.log_metadata["slug"] == "build-a-cloud-tracker"


def test_create_challenge_rejects_over_allocated_points(client, make_user, login):
    login(client, make_user(username="admin", role=UserRole.ADMIN))
    response = client.post("/api/v1/challenges", json=_payload(max_points=50))

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_create_challenge_rejects_duplicate_check_ids(client, make_user, login):
    login(client, make_user(username="admin", role=UserRole.ADMIN))
    duplicated = {
        "version": 1,
        "checks": [
            {"id": "same", "type": "repo_accessible", "points": 50},
            {"id": "same", "type": "readme_present", "points": 50},
        ],
    }
    response = client.post("/api/v1/challenges", json=_payload(evaluation_config=duplicated))

    assert response.status_code == 422


def test_slug_is_generated_and_uniquified(client, db, make_user, login):
    login(client, make_user(username="admin", role=UserRole.ADMIN))
    first = client.post("/api/v1/challenges", json=_payload()).json()
    second = client.post("/api/v1/challenges", json=_payload()).json()

    assert first["slug"] == "build-a-cloud-tracker"
    assert second["slug"] == "build-a-cloud-tracker-2"


# --- moderation ---------------------------------------------------------------------------


def test_publish_draft_challenge_and_audit(client, db, make_user, login):
    admin = make_user(username="admin", role=UserRole.ADMIN)
    challenge = factories.make_challenge(db, status=ChallengeStatus.DRAFT)
    login(client, admin)

    response = client.post(f"/api/v1/challenges/{challenge.id}/publish")

    assert response.status_code == 200
    assert response.json()["status"] == "published"
    entry = db.execute(select(AuditLog).where(AuditLog.action == "challenge.publish")).scalar_one()
    assert entry.actor_id == admin.id
    assert entry.log_metadata["slug"] == challenge.slug


def test_archive_blocks_updates_and_republish(client, db, make_user, login):
    admin = make_user(username="admin", role=UserRole.ADMIN)
    challenge = factories.make_challenge(db, status=ChallengeStatus.PUBLISHED, slug="to-archive")
    login(client, admin)

    archived = client.post(f"/api/v1/challenges/{challenge.id}/archive")
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"

    update = client.patch(f"/api/v1/challenges/{challenge.id}", json={"title": "Renamed Challenge"})
    assert update.status_code == 409

    publish = client.post(f"/api/v1/challenges/{challenge.id}/publish")
    assert publish.status_code == 409


def test_update_validates_combined_configuration(client, db, make_user, login):
    login(client, make_user(username="admin", role=UserRole.ADMIN))
    challenge = factories.make_challenge(db, max_points=100, status=ChallengeStatus.PUBLISHED)

    # Lowering the maximum below the allocated check points must be rejected…
    response = client.patch(f"/api/v1/challenges/{challenge.id}", json={"max_points": 50})
    assert response.status_code == 422

    # …while a value that fits the configuration is accepted.
    ok = client.patch(f"/api/v1/challenges/{challenge.id}", json={"max_points": 120})
    assert ok.status_code == 200
    assert ok.json()["max_points"] == 120


def test_update_requires_staff_and_existing_challenge(client, db, make_user, login):
    student = make_user(username="student")
    challenge = factories.make_challenge(db)
    login(client, student)

    assert (
        client.patch(f"/api/v1/challenges/{challenge.id}", json={"max_points": 90}).status_code
        == 403
    )

    login(client, make_user(username="admin", role=UserRole.ADMIN))
    missing = client.patch(
        "/api/v1/challenges/00000000-0000-0000-0000-000000000000",
        json={"max_points": 90},
    )
    assert missing.status_code == 404


def test_created_challenge_state_is_flushed_to_database(client, db, make_user, login):
    login(client, make_user(username="admin", role=UserRole.ADMIN))
    slug = client.post("/api/v1/challenges", json=_payload()).json()["slug"]

    stored = db.execute(select(Challenge).where(Challenge.slug == slug)).scalar_one()
    assert stored.description == "Deploy a working cloud cost tracker."
    assert stored.max_points == 100
