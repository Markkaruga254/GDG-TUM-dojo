"""Challenge service: authoring, moderation and publication rules."""

from __future__ import annotations

import uuid

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.errors import Conflict, NotFound, ValidationFailed
from app.core.security import now_utc, unique_slug
from app.evaluation.rules import EvaluationConfig, validate_config_points
from app.models import Challenge, ChallengeStatus, User
from app.repositories.challenges import ChallengeRepository
from app.schemas.challenge import (
    ChallengeCreate,
    ChallengeDetail,
    ChallengeSummary,
    ChallengeUpdate,
    CheckSummary,
)
from app.services.audit import AuditAction, AuditService


class ChallengeService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = ChallengeRepository(db)
        self.audit = AuditService(db)

    # --- reads -----------------------------------------------------------------
    def list_challenges(
        self,
        *,
        viewer: User | None,
        track: str | None = None,
        difficulty: str | None = None,
        status: str | None = None,
        search: str | None = None,
        tag: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Challenge], int]:
        is_staff = viewer is not None and viewer.is_staff
        if is_staff and status:
            statuses = [ChallengeStatus(status)]
        elif is_staff and not status:
            statuses = list(ChallengeStatus)
        else:
            statuses = [ChallengeStatus.PUBLISHED]
        return self.repository.list_challenges(
            statuses=statuses,
            track=track,
            difficulty=difficulty,
            search=search,
            tag=tag,
            limit=limit,
            offset=offset,
        )

    def get_by_slug(self, slug: str, *, viewer: User | None) -> Challenge:
        challenge = self.repository.get_by_slug(slug)
        if challenge is None:
            raise NotFound("Challenge not found.")
        if challenge.status is ChallengeStatus.DRAFT and not (viewer and viewer.is_staff):
            raise NotFound("Challenge not found.")
        return challenge

    def get_by_id(self, challenge_id: uuid.UUID) -> Challenge:
        challenge = self.repository.get_by_id(challenge_id)
        if challenge is None:
            raise NotFound("Challenge not found.")
        return challenge

    def evaluation_config(self, challenge: Challenge) -> EvaluationConfig:
        try:
            return EvaluationConfig.model_validate(challenge.evaluation_config or {})
        except ValidationError as exc:
            raise ValidationFailed(
                "The stored evaluation configuration is invalid.",
                details=[
                    {"reason": error["msg"], "loc": list(error["loc"])} for error in exc.errors()
                ],
            ) from exc

    def is_open(self, challenge: Challenge) -> tuple[bool, str | None]:
        now = now_utc()
        if challenge.status is not ChallengeStatus.PUBLISHED:
            return False, "challenge_not_published"
        if challenge.starts_at and now < challenge.starts_at:
            return False, "challenge_not_started"
        if challenge.ends_at and now > challenge.ends_at:
            return False, "challenge_closed"
        return True, None

    # --- writes -------------------------------------------------------------------
    def create_challenge(self, actor: User, payload: ChallengeCreate) -> Challenge:
        self._validate_config(payload.evaluation_config, payload.max_points)
        slug = unique_slug(payload.slug or payload.title, self.repository.slug_exists)
        challenge = Challenge(
            title=payload.title.strip(),
            slug=slug,
            description=payload.description,
            instructions=payload.instructions or "",
            track=payload.track.strip().lower(),
            difficulty=payload.difficulty,
            tags=payload.tags,
            max_points=payload.max_points,
            status=ChallengeStatus.DRAFT,
            starts_at=payload.starts_at,
            ends_at=payload.ends_at,
            evaluation_config=payload.evaluation_config.model_dump(mode="json"),
            created_by=actor.id,
        )
        self.repository.add(challenge)
        self.db.flush()
        self.audit.record(
            actor,
            AuditAction.CHALLENGE_CREATE,
            target_type="challenge",
            target_id=str(challenge.id),
            metadata={"slug": challenge.slug, "max_points": challenge.max_points},
        )
        return challenge

    def update_challenge(
        self, actor: User, challenge_id: uuid.UUID, payload: ChallengeUpdate
    ) -> Challenge:
        challenge = self.get_by_id(challenge_id)
        if challenge.status is ChallengeStatus.ARCHIVED:
            raise Conflict("Archived challenges cannot be edited.")

        changes: dict = {}
        for field in (
            "title",
            "description",
            "instructions",
            "difficulty",
            "tags",
            "starts_at",
            "ends_at",
        ):
            value = getattr(payload, field)
            if value is not None:
                setattr(challenge, field, value)
                changes[field] = True
        if payload.track is not None:
            challenge.track = payload.track.strip().lower()
            changes["track"] = True
        if payload.max_points is not None:
            challenge.max_points = payload.max_points
            changes["max_points"] = payload.max_points
        if payload.evaluation_config is not None:
            challenge.evaluation_config = payload.evaluation_config.model_dump(mode="json")
            changes["evaluation_config"] = True

        # Validate the resulting state as a whole.
        config = self.evaluation_config(challenge)
        self._validate_config(config, challenge.max_points)
        if challenge.ends_at and challenge.starts_at and challenge.ends_at <= challenge.starts_at:
            raise ValidationFailed("ends_at must be after starts_at.")

        self.db.flush()
        self.audit.record(
            actor,
            AuditAction.CHALLENGE_UPDATE,
            target_type="challenge",
            target_id=str(challenge.id),
            metadata=changes,
        )
        return challenge

    def publish_challenge(self, actor: User, challenge_id: uuid.UUID) -> Challenge:
        challenge = self.get_by_id(challenge_id)
        if challenge.status is ChallengeStatus.ARCHIVED:
            raise Conflict("Archived challenges cannot be published.")
        config = self.evaluation_config(challenge)
        self._validate_config(config, challenge.max_points)
        challenge.status = ChallengeStatus.PUBLISHED
        self.db.flush()
        self.audit.record(
            actor,
            AuditAction.CHALLENGE_PUBLISH,
            target_type="challenge",
            target_id=str(challenge.id),
            metadata={"slug": challenge.slug},
        )
        return challenge

    def archive_challenge(self, actor: User, challenge_id: uuid.UUID) -> Challenge:
        challenge = self.get_by_id(challenge_id)
        if challenge.status is ChallengeStatus.ARCHIVED:
            return challenge
        challenge.status = ChallengeStatus.ARCHIVED
        self.db.flush()
        self.audit.record(
            actor,
            AuditAction.CHALLENGE_ARCHIVE,
            target_type="challenge",
            target_id=str(challenge.id),
            metadata={"slug": challenge.slug},
        )
        return challenge

    # --- helpers ---------------------------------------------------------------------
    def _validate_config(self, config: EvaluationConfig, max_points: int) -> None:
        problems = validate_config_points(config, max_points)
        if problems:
            raise ValidationFailed(
                "Invalid evaluation configuration.",
                details=[{"reason": problem} for problem in problems],
            )

    def to_summary(self, challenge: Challenge) -> ChallengeSummary:
        return ChallengeSummary.model_validate(challenge)

    def to_detail(
        self, challenge: Challenge, *, created_by: str | None = None, include_params: bool = False
    ) -> ChallengeDetail:
        config = EvaluationConfig.model_validate(challenge.evaluation_config or {})
        checks = config.public_summary()
        if include_params:
            checks = [
                {**check, "params": item.params}
                for check, item in zip(checks, config.checks, strict=True)
            ]
        return ChallengeDetail(
            id=challenge.id,
            slug=challenge.slug,
            title=challenge.title,
            track=challenge.track,
            difficulty=challenge.difficulty,
            tags=list(challenge.tags or []),
            max_points=challenge.max_points,
            status=challenge.status,
            starts_at=challenge.starts_at,
            ends_at=challenge.ends_at,
            created_at=challenge.created_at,
            description=challenge.description,
            instructions=challenge.instructions,
            created_by=created_by,
            evaluation=[CheckSummary(**check) for check in checks],
        )
