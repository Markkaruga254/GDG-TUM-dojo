"""SQLAlchemy models."""

from app.db.base import Base
from app.models.audit import AuditLog, sanitize_audit_metadata
from app.models.badge import Badge, UserBadge
from app.models.challenge import MAX_CHALLENGE_POINTS, Challenge
from app.models.enums import (
    ACTIVE_SUBMISSION_STATUSES,
    FINALIZED_SUBMISSION_STATUSES,
    IN_FLIGHT_SUBMISSION_STATUSES,
    BadgeRuleType,
    ChallengeStatus,
    CheckStatus,
    Difficulty,
    EvaluationStatus,
    SubmissionStatus,
    UserRole,
)
from app.models.submission import Evaluation, Submission
from app.models.user import AuthSession, User

__all__ = [
    "ACTIVE_SUBMISSION_STATUSES",
    "FINALIZED_SUBMISSION_STATUSES",
    "IN_FLIGHT_SUBMISSION_STATUSES",
    "MAX_CHALLENGE_POINTS",
    "AuditLog",
    "AuthSession",
    "Badge",
    "BadgeRuleType",
    "Base",
    "Challenge",
    "ChallengeStatus",
    "CheckStatus",
    "Difficulty",
    "Evaluation",
    "EvaluationStatus",
    "Submission",
    "SubmissionStatus",
    "User",
    "UserBadge",
    "UserRole",
    "sanitize_audit_metadata",
]
