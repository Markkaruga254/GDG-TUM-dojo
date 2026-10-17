"""Administrative service: role/status changes, moderation, score corrections.

Authorization is enforced by route dependencies; every mutation here is audited.
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.errors import Conflict, NotFound, ValidationFailed
from app.core.security import now_utc
from app.models import Submission, User, UserRole
from app.repositories.audit import SessionRepository
from app.repositories.challenges import ChallengeRepository
from app.repositories.submissions import SubmissionRepository
from app.repositories.users import UserRepository
from app.services.audit import AuditAction, AuditService


class AdminService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.submissions = SubmissionRepository(db)
        self.challenges = ChallengeRepository(db)
        self.sessions = SessionRepository(db)
        self.audit = AuditService(db)

    # --- users ----------------------------------------------------------------------
    def list_users(
        self,
        *,
        search: str | None = None,
        role: str | None = None,
        is_active: bool | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[User], int]:
        return self.users.list_users(
            search=search, role=role, is_active=is_active, limit=limit, offset=offset
        )

    def change_role(
        self, actor: User, user_id: uuid.UUID, role: UserRole, reason: str | None
    ) -> User:
        user = self.users.get_by_id(user_id)
        if user is None:
            raise NotFound("User not found.")
        if user.id == actor.id:
            raise Conflict("Administrators cannot change their own role.")
        previous = user.role
        user.role = role
        self.db.flush()
        self.audit.record(
            actor,
            AuditAction.USER_ROLE_CHANGE,
            target_type="user",
            target_id=str(user.id),
            metadata={
                "previous_role": previous.value,
                "new_role": role.value,
                "reason": reason,
                "username": user.github_username,
            },
        )
        return user

    def change_status(
        self, actor: User, user_id: uuid.UUID, is_active: bool, reason: str | None
    ) -> User:
        user = self.users.get_by_id(user_id)
        if user is None:
            raise NotFound("User not found.")
        if user.id == actor.id and not is_active:
            raise Conflict("Administrators cannot deactivate themselves.")
        user.is_active = is_active
        revoked = self.sessions.revoke_all_for_user(user.id) if not is_active else 0
        self.db.flush()
        self.audit.record(
            actor,
            AuditAction.USER_STATUS_CHANGE,
            target_type="user",
            target_id=str(user.id),
            metadata={
                "is_active": is_active,
                "sessions_revoked": revoked,
                "reason": reason,
                "username": user.github_username,
            },
        )
        return user

    # --- submissions ---------------------------------------------------------------------
    def get_submission(self, submission_id: uuid.UUID) -> Submission:
        submission = self.submissions.get_by_id(submission_id)
        if submission is None:
            raise NotFound("Submission not found.")
        return submission

    def disqualify(self, actor: User, submission_id: uuid.UUID, reason: str) -> Submission:
        submission = self.get_submission(submission_id)
        if submission.is_disqualified:
            raise Conflict("Submission is already disqualified.")
        submission.is_disqualified = True
        submission.disqualification_reason = reason
        submission.disqualified_at = now_utc()
        submission.disqualified_by = actor.id
        self.db.flush()
        self.audit.record(
            actor,
            AuditAction.SUBMISSION_DISQUALIFY,
            target_type="submission",
            target_id=str(submission.id),
            metadata={
                "reason": reason,
                "previous_points": submission.effective_points,
                "user_id": str(submission.user_id),
                "challenge_id": str(submission.challenge_id),
            },
        )
        return submission

    def reinstate(self, actor: User, submission_id: uuid.UUID) -> Submission:
        submission = self.get_submission(submission_id)
        if not submission.is_disqualified:
            raise Conflict("Submission is not disqualified.")
        previous_reason = submission.disqualification_reason
        submission.is_disqualified = False
        submission.disqualification_reason = None
        submission.disqualified_at = None
        submission.disqualified_by = None
        self.db.flush()
        self.audit.record(
            actor,
            AuditAction.SUBMISSION_REINSTATE,
            target_type="submission",
            target_id=str(submission.id),
            metadata={"previous_reason": previous_reason, "user_id": str(submission.user_id)},
        )
        return submission

    def override_score(
        self, actor: User, submission_id: uuid.UUID, points: int, reason: str
    ) -> Submission:
        submission = self.get_submission(submission_id)
        challenge = self.challenges.get_by_id(submission.challenge_id)
        if challenge is None:  # pragma: no cover - FK guarantees existence
            raise NotFound("Challenge not found.")
        if points > challenge.max_points:
            raise ValidationFailed(
                f"Score correction cannot exceed the challenge maximum of {challenge.max_points}."
            )
        previous = submission.effective_points
        submission.score_override_points = points
        submission.score_override_reason = reason
        submission.score_overridden_at = now_utc()
        submission.score_overridden_by = actor.id
        self.db.flush()
        self.audit.record(
            actor,
            AuditAction.SUBMISSION_SCORE_OVERRIDE,
            target_type="submission",
            target_id=str(submission.id),
            metadata={
                "previous_points": previous,
                "override_points": points,
                "reason": reason,
                "user_id": str(submission.user_id),
                "challenge_id": str(submission.challenge_id),
            },
        )
        return submission

    def clear_score_override(self, actor: User, submission_id: uuid.UUID) -> Submission:
        submission = self.get_submission(submission_id)
        if submission.score_override_points is None:
            raise Conflict("No score override is set for this submission.")
        previous = submission.score_override_points
        submission.score_override_points = None
        submission.score_override_reason = None
        submission.score_overridden_at = None
        submission.score_overridden_by = None
        self.db.flush()
        self.audit.record(
            actor,
            AuditAction.SUBMISSION_SCORE_OVERRIDE_CLEAR,
            target_type="submission",
            target_id=str(submission.id),
            metadata={"cleared_override": previous, "user_id": str(submission.user_id)},
        )
        return submission
