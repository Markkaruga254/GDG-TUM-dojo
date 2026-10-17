"""Badge and user-badge data access."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models import Badge, UserBadge


class BadgeRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, badge_id: uuid.UUID) -> Badge | None:
        return self.session.get(Badge, badge_id)

    def get_by_slug(self, slug: str) -> Badge | None:
        return self.session.execute(
            select(Badge).where(Badge.slug == slug.strip().lower())
        ).scalar_one_or_none()

    def list_badges(self, *, active_only: bool = False) -> list[Badge]:
        query = select(Badge).order_by(Badge.name.asc())
        if active_only:
            query = query.where(Badge.is_active.is_(True))
        return list(self.session.execute(query).scalars().all())

    def list_for_user(self, user_id: uuid.UUID) -> list[tuple[Badge, object]]:
        rows = self.session.execute(
            select(Badge, UserBadge.awarded_at)
            .join(UserBadge, UserBadge.badge_id == Badge.id)
            .where(UserBadge.user_id == user_id)
            .order_by(UserBadge.awarded_at.desc())
        ).all()
        return [(row[0], row[1]) for row in rows]

    def has_badge(self, user_id: uuid.UUID, badge_id: uuid.UUID) -> bool:
        return (
            self.session.execute(
                select(UserBadge.id).where(
                    UserBadge.user_id == user_id, UserBadge.badge_id == badge_id
                )
            ).first()
            is not None
        )

    def award(
        self, user_id: uuid.UUID, badge_id: uuid.UUID, *, awarded_by: uuid.UUID | None = None
    ) -> bool:
        """Idempotently grant a badge. Returns True when a new award was created."""
        statement = (
            pg_insert(UserBadge)
            .values(user_id=user_id, badge_id=badge_id, awarded_by=awarded_by)
            .on_conflict_do_nothing(constraint="uq_user_badges_user_id_badge_id")
            .returning(UserBadge.id)
        )
        return self.session.execute(statement).scalar_one_or_none() is not None

    def count_for_badge(self, badge_id: uuid.UUID) -> int:
        return int(
            self.session.execute(
                select(func.count()).select_from(UserBadge).where(UserBadge.badge_id == badge_id)
            ).scalar_one()
        )

    def add(self, badge: Badge) -> Badge:
        self.session.add(badge)
        return badge
