"""Model-level tests: identifiers, constraints, cascades and scoring properties."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from app.models import (
    AuditLog,
    AuthSession,
    Evaluation,
    EvaluationStatus,
    Submission,
    SubmissionStatus,
    UserBadge,
)
from app.models.audit import sanitize_audit_metadata
from tests import factories

# --- identifiers and timestamps -------------------------------------------------


def test_uuid_primary_keys_are_generated(db, make_user):
    user = make_user()
    challenge = factories.make_challenge(db, created_by=user)
    submission = factories.make_submission(db, user=user, challenge=challenge)

    ids = [user.id, challenge.id, submission.id]
    assert all(isinstance(value, uuid.UUID) for value in ids)
    assert len(set(ids)) == 3


def test_timestamps_are_timezone_aware_utc(db, make_user):
    user = make_user()
    db.refresh(user)

    assert user.created_at.tzinfo is not None
    assert user.created_at.utcoffset().total_seconds() == 0
    assert user.updated_at.utcoffset().total_seconds() == 0


# --- uniqueness ------------------------------------------------------------------


def test_duplicate_github_id_is_rejected(db, make_user):
    make_user(github_id=424242)
    with pytest.raises(IntegrityError):
        factories.make_user(db, github_id=424242)
    db.rollback()


def test_duplicate_challenge_slug_is_rejected(db):
    factories.make_challenge(db, slug="unique-slug")
    with pytest.raises(IntegrityError):
        factories.make_challenge(db, slug="unique-slug")
    db.rollback()


def test_duplicate_badge_slug_is_rejected(db):
    factories.make_badge(db, slug="duplicate-badge")
    with pytest.raises(IntegrityError):
        factories.make_badge(db, slug="duplicate-badge")
    db.rollback()


def test_user_badge_is_unique_per_user_and_badge(db, make_user):
    user = make_user()
    badge = factories.make_badge(db)
    factories.make_user_badge(db, user=user, badge=badge)

    with pytest.raises(IntegrityError):
        factories.make_user_badge(db, user=user, badge=badge)
    db.rollback()


# --- check constraints ------------------------------------------------------------------


def test_check_constraint_rejects_unknown_enum_values(db):
    # Raw SQL bypasses Python-side enum validation to exercise the DB CHECK.
    with pytest.raises(IntegrityError):
        db.execute(
            text(
                "INSERT INTO users (id, github_id, github_username, role, is_active) "
                "VALUES ('00000000-0000-0000-0000-00000000dead', 9999, 'badrole', 'wizard', true)"
            )
        )
    db.rollback()


def test_challenge_max_points_must_be_positive(db):
    with pytest.raises(IntegrityError):
        factories.make_challenge(db, max_points=0)
    db.rollback()


def test_evaluation_awarded_score_must_fit_max_score(db, make_user):
    user = make_user()
    challenge = factories.make_challenge(db, max_points=50)
    submission = factories.make_submission(db, user=user, challenge=challenge)

    db.add(
        Evaluation(
            submission_id=submission.id,
            status=EvaluationStatus.COMPLETED,
            max_score=10,
            awarded_score=11,
            evaluator_version="test",
            started_at=factories.now(),
        )
    )
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


# --- scoring properties ------------------------------------------------------------------


def test_effective_points_prefers_authorized_override(db, make_user):
    user = make_user()
    challenge = factories.make_challenge(db)
    submission = factories.make_submission(
        db, user=user, challenge=challenge, status=SubmissionStatus.PASSED, points=40
    )
    assert submission.effective_points == 40

    submission.score_override_points = 70
    assert submission.effective_points == 70

    submission.score_override_points = 0
    assert submission.effective_points == 0


def test_pending_submission_has_zero_effective_points(db, make_user):
    user = make_user()
    challenge = factories.make_challenge(db)
    submission = factories.make_submission(db, user=user, challenge=challenge)

    assert submission.points_awarded is None
    assert submission.effective_points == 0
    assert submission.counts_for_leaderboard is False


def test_counts_for_leaderboard_requires_final_scored_status(db, make_user):
    user = make_user()
    challenge = factories.make_challenge(db)

    passed = factories.finalize_submission(db, user=user, challenge=challenge, points=10)
    assert passed.counts_for_leaderboard is True

    failed = factories.finalize_submission(
        db, user=user, challenge=challenge, points=0, passed=False
    )
    assert failed.counts_for_leaderboard is True

    disqualified = factories.finalize_submission(
        db, user=user, challenge=challenge, points=10, is_disqualified=True
    )
    assert disqualified.counts_for_leaderboard is False

    errored = factories.make_submission(
        db,
        user=user,
        challenge=challenge,
        status=SubmissionStatus.ERROR,
        evaluated_at=factories.now(),
    )
    assert errored.counts_for_leaderboard is False


# --- deletion policies -----------------------------------------------------------------


def test_deleting_user_cascades_sessions_and_submissions(db, make_user):
    user = make_user()
    challenge = factories.make_challenge(db, created_by=user)
    factories.make_submission(db, user=user, challenge=challenge)
    db.add(AuthSession(user_id=user.id, token_hash="a" * 64, expires_at=factories.future_expiry()))
    db.flush()

    db.delete(user)
    db.flush()

    assert db.execute(select(func.count()).select_from(Submission)).scalar_one() == 0
    assert db.execute(select(func.count()).select_from(AuthSession)).scalar_one() == 0
    # The challenge survives; its creator reference is nulled.
    db.refresh(challenge)
    assert challenge.created_by is None


def test_deleting_challenge_cascades_submissions(db, make_user):
    user = make_user()
    challenge = factories.make_challenge(db)
    submission = factories.finalize_submission(db, user=user, challenge=challenge, points=10)

    db.delete(challenge)
    db.flush()

    assert db.execute(select(func.count()).select_from(Submission)).scalar_one() == 0
    assert db.execute(select(func.count()).select_from(Evaluation)).scalar_one() == 0, (
        "evaluations follow their submission"
    )
    assert submission.id is not None  # object identity survives, row does not


def test_awarded_badge_cannot_be_deleted(db, make_user):
    user = make_user()
    badge = factories.make_badge(db)
    factories.make_user_badge(db, user=user, badge=badge)

    db.delete(badge)
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_audit_log_survives_user_deletion(db, make_user):
    user = make_user()
    entry = AuditLog(
        actor_id=user.id,
        actor_username=user.github_username,
        action="user.role_change",
        target_type="user",
        target_id=str(user.id),
    )
    db.add(entry)
    db.flush()

    db.delete(user)
    db.flush()
    db.refresh(entry)

    assert entry.actor_id is None
    assert entry.actor_username == user.github_username


# --- audit metadata sanitization ---------------------------------------------------------


def test_audit_metadata_redacts_sensitive_keys():
    cleaned = sanitize_audit_metadata(
        {
            "authorization": "Bearer secret",
            "nested": {"client_secret": "shh", "safe": "value"},
            "list": [{"token_hash": "x"}, "plain"],
        }
    )
    assert cleaned["authorization"] == "[redacted]"
    assert cleaned["nested"]["client_secret"] == "[redacted]"
    assert cleaned["nested"]["safe"] == "value"
    assert cleaned["list"][0]["token_hash"] == "[redacted]"
    assert cleaned["list"][1] == "plain"


def test_audit_metadata_truncates_and_caps_payloads():
    long_value = sanitize_audit_metadata({"blob": "x" * 1000})
    assert long_value["blob"].endswith("...[truncated]")
    assert len(long_value["blob"]) < 300

    oversized = sanitize_audit_metadata({f"k{index}": "v" * 200 for index in range(50)})
    assert oversized.get("truncated") is True
    assert oversized["original_size_bytes"] > 4096

    assert sanitize_audit_metadata(None) == {}


# --- user badge query --------------------------------------------------------------------


def test_user_badge_award_is_queryable_after_insert(db, make_user):
    user = make_user()
    badge = factories.make_badge(db)
    award = factories.make_user_badge(db, user=user, badge=badge)

    count = db.execute(
        select(func.count()).select_from(UserBadge).where(UserBadge.user_id == user.id)
    ).scalar_one()
    assert count == 1
    assert award.user_id == user.id
