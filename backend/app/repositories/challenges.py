"""Challenge data access."""

from __future__ import annotations

import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import Challenge, ChallengeStatus


class ChallengeRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, challenge_id: uuid.UUID) -> Challenge | None:
        return self.session.get(Challenge, challenge_id)

    def get_by_slug(self, slug: str) -> Challenge | None:
        return self.session.execute(
            select(Challenge).where(Challenge.slug == slug.strip().lower())
        ).scalar_one_or_none()

    def slug_exists(self, slug: str) -> bool:
        return (
            self.session.execute(select(Challenge.id).where(Challenge.slug == slug)).first()
            is not None
        )

    def list_challenges(
        self,
        *,
        statuses: list[ChallengeStatus],
        track: str | None = None,
        difficulty: str | None = None,
        search: str | None = None,
        tag: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Challenge], int]:
        query = select(Challenge).where(Challenge.status.in_(statuses))
        if track:
            query = query.where(Challenge.track == track)
        if difficulty:
            query = query.where(Challenge.difficulty == difficulty)
        if tag:
            query = query.where(Challenge.tags.contains([tag.strip().lower()]))
        if search:
            pattern = f"%{search.strip().lower()}%"
            query = query.where(
                or_(
                    func.lower(Challenge.title).like(pattern),
                    func.lower(Challenge.description).like(pattern),
                )
            )

        total = self.session.execute(
            select(func.count()).select_from(query.subquery())
        ).scalar_one()
        rows = (
            self.session.execute(
                query.order_by(Challenge.created_at.desc()).limit(limit).offset(offset)
            )
            .scalars()
            .all()
        )
        return list(rows), int(total)

    def list_tracks(self) -> list[str]:
        rows = self.session.execute(
            select(Challenge.track)
            .where(Challenge.status != ChallengeStatus.DRAFT)
            .distinct()
            .order_by(Challenge.track)
        ).scalars()
        return list(rows)

    def add(self, challenge: Challenge) -> Challenge:
        self.session.add(challenge)
        return challenge
