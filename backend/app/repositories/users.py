"""User data access."""

from __future__ import annotations

import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import User


class UserRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return self.session.get(User, user_id)

    def get_by_github_id(self, github_id: int) -> User | None:
        return self.session.execute(
            select(User).where(User.github_id == github_id)
        ).scalar_one_or_none()

    def get_by_username(self, username: str) -> User | None:
        return self.session.execute(
            select(User).where(func.lower(User.github_username) == username.strip().lower())
        ).scalar_one_or_none()

    def list_users(
        self,
        *,
        search: str | None = None,
        role: str | None = None,
        is_active: bool | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[User], int]:
        query = select(User)
        if search:
            pattern = f"%{search.strip().lower()}%"
            query = query.where(
                or_(
                    func.lower(User.github_username).like(pattern),
                    func.lower(func.coalesce(User.display_name, "")).like(pattern),
                )
            )
        if role:
            query = query.where(User.role == role)
        if is_active is not None:
            query = query.where(User.is_active.is_(is_active))

        total = self.session.execute(
            select(func.count()).select_from(query.subquery())
        ).scalar_one()
        rows = (
            self.session.execute(query.order_by(User.created_at.desc()).limit(limit).offset(offset))
            .scalars()
            .all()
        )
        return list(rows), int(total)

    def add(self, user: User) -> User:
        self.session.add(user)
        return user
