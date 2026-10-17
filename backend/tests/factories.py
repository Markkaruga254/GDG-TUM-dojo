"""Model factories shared by tests."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.models import (
    Badge,
    Challenge,
    ChallengeStatus,
    Difficulty,
    Evaluation,
    EvaluationStatus,
    Submission,
    SubmissionStatus,
    User,
    UserBadge,
    UserRole,
)

DEFAULT_EVALUATION_CONFIG = {
    "version": 1,
    "require_public_repo": True,
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

_counter = {"n": 0}


def _next() -> int:
    _counter["n"] += 1
    return _counter["n"]


def now() -> datetime:
    return datetime.now(UTC)


def future_expiry(hours: int = 24) -> datetime:
    return now() + timedelta(hours=hours)


def make_user(
    db: Session,
    *,
    username: str | None = None,
    github_id: int | None = None,
    role: UserRole = UserRole.STUDENT,
    is_active: bool = True,
    display_name: str | None = None,
) -> User:
    index = _next()
    user = User(
        github_id=github_id if github_id is not None else 100_000 + index,
        github_username=username or f"student{index}",
        display_name=display_name,
        role=role,
        is_active=is_active,
    )
    db.add(user)
    db.flush()
    return user


def make_challenge(
    db: Session,
    *,
    status: ChallengeStatus = ChallengeStatus.PUBLISHED,
    track: str = "cloud",
    difficulty: Difficulty = Difficulty.BEGINNER,
    max_points: int = 100,
    slug: str | None = None,
    created_by: User | None = None,
    evaluation_config: dict | None = None,
    starts_at: datetime | None = None,
    ends_at: datetime | None = None,
) -> Challenge:
    index = _next()
    challenge = Challenge(
        title=f"Challenge {index}",
        slug=slug or f"challenge-{index}",
        description="A test challenge description.",
        instructions="Do the thing.",
        track=track,
        difficulty=difficulty,
        tags=["test"],
        max_points=max_points,
        status=status,
        starts_at=starts_at,
        ends_at=ends_at,
        evaluation_config=evaluation_config or DEFAULT_EVALUATION_CONFIG,
        created_by=created_by.id if created_by else None,
    )
    db.add(challenge)
    db.flush()
    return challenge


def make_submission(
    db: Session,
    *,
    user: User,
    challenge: Challenge,
    status: SubmissionStatus = SubmissionStatus.PENDING,
    points: int | None = None,
    repo_full_name: str | None = None,
    evaluated_at: datetime | None = None,
    is_disqualified: bool = False,
    score_override_points: int | None = None,
    submitted_at: datetime | None = None,
) -> Submission:
    index = _next()
    full_name = repo_full_name or f"{user.github_username}/project{index}"
    submission = Submission(
        user_id=user.id,
        challenge_id=challenge.id,
        repo_url=f"https://github.com/{full_name}",
        repo_full_name=full_name,
        status=status,
        points_awarded=points,
        evaluated_at=evaluated_at,
        submitted_at=submitted_at or now(),
        is_disqualified=is_disqualified,
        score_override_points=score_override_points,
        evidence_urls=[],
    )
    db.add(submission)
    db.flush()
    return submission


def finalize_submission(
    db: Session,
    *,
    user: User,
    challenge: Challenge,
    points: int,
    evaluated_at: datetime | None = None,
    passed: bool = True,
    repo_full_name: str | None = None,
    **kwargs,
) -> Submission:
    """Create a submission together with a completed evaluation row."""
    submission = make_submission(
        db,
        user=user,
        challenge=challenge,
        status=SubmissionStatus.PASSED if passed else SubmissionStatus.FAILED,
        points=points,
        evaluated_at=evaluated_at or now(),
        repo_full_name=repo_full_name,
        **kwargs,
    )
    db.add(
        Evaluation(
            submission_id=submission.id,
            status=EvaluationStatus.COMPLETED,
            checks=[],
            max_score=challenge.max_points,
            awarded_score=points,
            feedback="ok",
            evaluator_version="1.0.0",
            started_at=submission.evaluated_at,
            completed_at=submission.evaluated_at,
        )
    )
    db.flush()
    return submission


def make_badge(
    db: Session,
    *,
    slug: str | None = None,
    rule: dict | None = None,
    is_active: bool = True,
) -> Badge:
    index = _next()
    badge = Badge(
        slug=slug or f"badge-{index}",
        name=f"Badge {index}",
        description="A test badge.",
        icon="star",
        criteria={
            "description": "Test rule",
            "rule": rule or {"type": "challenges_passed", "count": 1},
        },
        is_active=is_active,
    )
    db.add(badge)
    db.flush()
    return badge


def make_user_badge(db: Session, *, user: User, badge: Badge) -> UserBadge:
    award = UserBadge(user_id=user.id, badge_id=badge.id)
    db.add(award)
    db.flush()
    return award


def uuid_str() -> str:
    return str(uuid.uuid4())
