"""Audit trail service. Every privileged action goes through here."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models import User
from app.repositories.audit import AuditRepository


class AuditAction:
    CHALLENGE_CREATE = "challenge.create"
    CHALLENGE_UPDATE = "challenge.update"
    CHALLENGE_PUBLISH = "challenge.publish"
    CHALLENGE_ARCHIVE = "challenge.archive"
    USER_ROLE_CHANGE = "user.role_change"
    USER_STATUS_CHANGE = "user.status_change"
    SUBMISSION_DISQUALIFY = "submission.disqualify"
    SUBMISSION_REINSTATE = "submission.reinstate"
    SUBMISSION_SCORE_OVERRIDE = "submission.score_override"
    SUBMISSION_SCORE_OVERRIDE_CLEAR = "submission.score_override_clear"
    SUBMISSION_FORCE_EVALUATE = "submission.force_evaluate"
    BADGE_CREATE = "badge.create"
    BADGE_UPDATE = "badge.update"
    BADGE_GRANT = "badge.grant"


class AuditService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = AuditRepository(db)

    def record(
        self,
        actor: User | None,
        action: str,
        *,
        target_type: str | None = None,
        target_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Persist a sanitized audit entry (secrets are stripped by the model layer)."""
        self.repository.record(
            action=action,
            actor_id=actor.id if actor else None,
            actor_username=actor.github_username if actor else None,
            target_type=target_type,
            target_id=target_id,
            metadata=metadata,
        )

    def list_entries(
        self,
        *,
        action: str | None = None,
        actor_id=None,  # type: ignore[no-untyped-def]
        limit: int = 20,
        offset: int = 0,
    ):  # type: ignore[no-untyped-def]
        return self.repository.list_logs(
            action=action, actor_id=actor_id, limit=limit, offset=offset
        )
