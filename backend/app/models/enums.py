"""Domain enumerations shared by models and schemas."""

from __future__ import annotations

from enum import StrEnum


class UserRole(StrEnum):
    STUDENT = "student"
    MODERATOR = "moderator"
    ADMIN = "admin"


class ChallengeStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class Difficulty(StrEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class SubmissionStatus(StrEnum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"


class EvaluationStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"


class CheckStatus(StrEnum):
    PASSED = "passed"
    PARTIAL = "partial"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


class BadgeRuleType(StrEnum):
    SUBMISSIONS_FINALIZED = "submissions_finalized"
    CHALLENGES_PASSED = "challenges_passed"
    PERFECT_SCORES = "perfect_scores"
    TRACK_CHALLENGES_PASSED = "track_challenges_passed"


# Statuses that count as a settled, final result (used by leaderboard/badges).
FINALIZED_SUBMISSION_STATUSES = (SubmissionStatus.PASSED, SubmissionStatus.FAILED)
# Broad "not yet settled" grouping: also used to detect duplicate live submissions.
ACTIVE_SUBMISSION_STATUSES = (
    SubmissionStatus.PENDING,
    SubmissionStatus.QUEUED,
    SubmissionStatus.RUNNING,
)
# Narrow "an evaluation is already executing" grouping (drives idempotent triggers).
IN_FLIGHT_SUBMISSION_STATUSES = (
    SubmissionStatus.QUEUED,
    SubmissionStatus.RUNNING,
)
