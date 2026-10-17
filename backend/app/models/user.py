"""User and authentication-session models."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Uuid,
    func,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.security import now_utc
from app.db.base import Base, TimestampMixin
from app.models.enums import UserRole
from app.models.types import enum_check, enum_column


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    github_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    github_username: Mapped[str] = mapped_column(String(39), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(512))
    display_name: Mapped[str | None] = mapped_column(String(120))
    bio: Mapped[str | None] = mapped_column(String(500))
    role: Mapped[UserRole] = mapped_column(
        enum_column(UserRole, "user_role"),
        nullable=False,
        default=UserRole.STUDENT,
        server_default=UserRole.STUDENT.value,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )

    __table_args__ = (
        CheckConstraint(enum_check("role", UserRole), name="role_valid"),
        Index("uq_users_github_id", "github_id", unique=True),
        Index("uq_users_github_username", "github_username", unique=True),
        Index("ix_users_role", "role"),
        Index("ix_users_is_active", "is_active"),
    )

    sessions: Mapped[list[AuthSession]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )

    @property
    def is_staff(self) -> bool:
        return self.role in (UserRole.MODERATOR, UserRole.ADMIN)


class AuthSession(Base):
    """Server-side session record. Only the SHA-256 hash of the token is stored."""

    __tablename__ = "auth_sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    user_agent: Mapped[str | None] = mapped_column(String(256))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=now_utc, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="sessions")

    __table_args__ = (
        Index("uq_auth_sessions_token_hash", "token_hash", unique=True),
        Index("ix_auth_sessions_user_id", "user_id"),
        Index("ix_auth_sessions_expires_at", "expires_at"),
    )

    @property
    def is_valid(self) -> bool:
        return self.revoked_at is None and self.expires_at > now_utc()
