"""Badge service: listing, server-side rule evaluation and awarding.

Badge rules are data, validated by :class:`app.schemas.badge.BadgeCriteria`, and
are only ever evaluated in backend code — never from client input.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.errors import Conflict, NotFound, ValidationFailed
from app.models import Badge, BadgeRuleType, User
from app.repositories.badges import BadgeRepository
from app.repositories.leaderboard import LeaderboardRepository
from app.schemas.badge import BadgeCriteria
from app.services.audit import AuditAction, AuditService

DEFAULT_BADGES: list[dict] = [
    {
        "slug": "first-submission",
        "name": "First Submission",
        "description": "Submitted your first project for automated evaluation.",
        "icon": "rocket",
        "criteria": {
            "description": "Finalize at least one submission.",
            "rule": {"type": "submissions_finalized", "count": 1},
        },
    },
    {
        "slug": "first-challenge",
        "name": "First Challenge Complete",
        "description": "Earned points on your first challenge.",
        "icon": "medal",
        "criteria": {
            "description": "Earn a positive score on at least one challenge.",
            "rule": {"type": "challenges_passed", "count": 1},
        },
    },
    {
        "slug": "five-challenges",
        "name": "Five Challenges Complete",
        "description": "Earned points on five different challenges.",
        "icon": "flame",
        "criteria": {
            "description": "Earn a positive score on five challenges.",
            "rule": {"type": "challenges_passed", "count": 5},
        },
    },
    {
        "slug": "ten-challenges",
        "name": "Ten Challenges Complete",
        "description": "Earned points on ten different challenges.",
        "icon": "trophy",
        "criteria": {
            "description": "Earn a positive score on ten challenges.",
            "rule": {"type": "challenges_passed", "count": 10},
        },
    },
    {
        "slug": "perfect-build",
        "name": "Perfect Build",
        "description": "Scored full marks on a challenge.",
        "icon": "star",
        "criteria": {
            "description": "Score the challenge maximum on at least one challenge.",
            "rule": {"type": "perfect_scores", "count": 1},
        },
    },
]


class BadgeService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = BadgeRepository(db)
        self.leaderboard = LeaderboardRepository(db)
        self.audit = AuditService(db)

    def list_badges(self) -> list[Badge]:
        return self.repository.list_badges()

    def list_for_user(self, user: User) -> list[tuple[Badge, datetime]]:
        return self.repository.list_for_user(user.id)

    def seed_defaults(self) -> int:
        """Create missing default badges (idempotent). Returns number created."""
        created = 0
        for definition in DEFAULT_BADGES:
            if self.repository.get_by_slug(definition["slug"]) is not None:
                continue
            criteria = BadgeCriteria.model_validate(definition["criteria"])
            self.repository.add(
                Badge(
                    slug=definition["slug"],
                    name=definition["name"],
                    description=definition["description"],
                    icon=definition["icon"],
                    criteria=criteria.model_dump(mode="json"),
                )
            )
            # Flush so repeated calls in the same (non-autoflush) session stay idempotent.
            self.db.flush()
            created += 1
        return created

    def create_badge(self, actor: User, payload) -> Badge:  # type: ignore[no-untyped-def]
        if self.repository.get_by_slug(payload.slug) is not None:
            raise Conflict("A badge with this slug already exists.")
        badge = Badge(
            slug=payload.slug,
            name=payload.name,
            description=payload.description,
            icon=payload.icon,
            criteria=payload.criteria.model_dump(mode="json"),
            is_active=payload.is_active,
        )
        self.repository.add(badge)
        self.audit.record(
            actor,
            AuditAction.BADGE_CREATE,
            target_type="badge",
            target_id=payload.slug,
            metadata={"name": payload.name},
        )
        return badge

    def update_badge(self, actor: User, badge_id: uuid.UUID, payload) -> Badge:  # type: ignore[no-untyped-def]
        badge = self.repository.get_by_id(badge_id)
        if badge is None:
            raise NotFound("Badge not found.")
        changes: dict = {}
        for field in ("name", "description", "icon", "is_active"):
            value = getattr(payload, field, None)
            if value is not None:
                changes[field] = value
                setattr(badge, field, value)
        if payload.criteria is not None:
            badge.criteria = payload.criteria.model_dump(mode="json")
            changes["criteria_updated"] = True
        self.audit.record(
            actor,
            AuditAction.BADGE_UPDATE,
            target_type="badge",
            target_id=str(badge.id),
            metadata=changes,
        )
        return badge

    def grant_badge(self, actor: User, user: User, badge_slug: str, reason: str | None) -> bool:
        badge = self.repository.get_by_slug(badge_slug)
        if badge is None:
            raise NotFound("Badge not found.")
        created = self.repository.award(user.id, badge.id, awarded_by=actor.id)
        self.audit.record(
            actor,
            AuditAction.BADGE_GRANT,
            target_type="user",
            target_id=str(user.id),
            metadata={"badge": badge.slug, "duplicate": not created, "reason": reason},
        )
        return created

    def evaluate_awards(self, user: User) -> list[Badge]:
        """Award every badge whose rule the user now satisfies. Idempotent."""
        metrics = self.leaderboard.metrics(user.id)
        track_cache: dict[str, dict[str, int]] = {}
        awarded: list[Badge] = []
        for badge in self.repository.list_badges(active_only=True):
            try:
                criteria = BadgeCriteria.model_validate(badge.criteria)
            except ValidationError:
                # Skip malformed legacy criteria rather than breaking evaluation.
                continue
            rule = criteria.rule
            satisfied = False
            if rule.type is BadgeRuleType.SUBMISSIONS_FINALIZED:
                satisfied = metrics.get("submissions_finalized", 0) >= rule.count
            elif rule.type is BadgeRuleType.CHALLENGES_PASSED:
                satisfied = metrics.get("challenges_passed", 0) >= rule.count
            elif rule.type is BadgeRuleType.PERFECT_SCORES:
                satisfied = metrics.get("perfect_scores", 0) >= rule.count
            elif rule.type is BadgeRuleType.TRACK_CHALLENGES_PASSED and rule.track:
                track = rule.track.lower()
                if track not in track_cache:
                    track_cache[track] = self.leaderboard.track_metrics(user.id, track)
                satisfied = track_cache[track].get("track_challenges_passed", 0) >= rule.count

            if not satisfied:
                continue
            if self.repository.award(user.id, badge.id):
                awarded.append(badge)
        return awarded


def validate_badge_criteria(payload: dict) -> BadgeCriteria:
    try:
        return BadgeCriteria.model_validate(payload)
    except ValidationError as exc:
        raise ValidationFailed(
            "Invalid badge criteria.",
            details=[{"field": "criteria", "reason": error["msg"]} for error in exc.errors()],
        ) from exc
