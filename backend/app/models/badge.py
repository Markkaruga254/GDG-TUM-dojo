"""Badge and user-badge models."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
    true,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.security import now_utc
from app.db.base import Base, TimestampMixin


class Badge(TimestampMixin, Base):
    __tablename__ = "badges"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    icon: Mapped[str] = mapped_column(String(64), nullable=False)
    # Structured, server-validated award rule:
    # {"description": str, "rule": {"type": ..., "count": int, "track": str | null}}
    criteria: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )

    __table_args__ = (
        Index("uq_badges_slug", "slug", unique=True),
        Index("uq_badges_name", "name", unique=True),
    )


class UserBadge(Base):
    __tablename__ = "user_badges"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    badge_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("badges.id", ondelete="RESTRICT"), nullable=False
    )
    awarded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=now_utc, server_default=func.now()
    )
    awarded_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )

    __table_args__ = (
        UniqueConstraint("user_id", "badge_id", name="uq_user_badges_user_id_badge_id"),
        Index("ix_user_badges_user_id", "user_id"),
    )
