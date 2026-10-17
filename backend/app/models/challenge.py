"""Challenge model."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.enums import ChallengeStatus, Difficulty
from app.models.types import enum_check, enum_column

MAX_CHALLENGE_POINTS = 10_000


class Challenge(TimestampMixin, Base):
    __tablename__ = "challenges"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    instructions: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    track: Mapped[str] = mapped_column(String(64), nullable=False)
    difficulty: Mapped[Difficulty] = mapped_column(
        enum_column(Difficulty, "challenge_difficulty"),
        nullable=False,
        default=Difficulty.BEGINNER,
        server_default=Difficulty.BEGINNER.value,
    )
    tags: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb")
    )
    max_points: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[ChallengeStatus] = mapped_column(
        enum_column(ChallengeStatus, "challenge_status"),
        nullable=False,
        default=ChallengeStatus.DRAFT,
        server_default=ChallengeStatus.DRAFT.value,
    )
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    evaluation_config: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    __table_args__ = (
        CheckConstraint(enum_check("status", ChallengeStatus), name="status_valid"),
        CheckConstraint(enum_check("difficulty", Difficulty), name="difficulty_valid"),
        CheckConstraint("max_points > 0", name="max_points_positive"),
        CheckConstraint(f"max_points <= {MAX_CHALLENGE_POINTS}", name="max_points_upper_bound"),
        CheckConstraint(
            "ends_at IS NULL OR starts_at IS NULL OR ends_at > starts_at", name="date_window"
        ),
        Index("uq_challenges_slug", "slug", unique=True),
        Index("ix_challenges_status", "status"),
        Index("ix_challenges_track", "track"),
        Index("ix_challenges_difficulty", "difficulty"),
        Index("ix_challenges_status_track", "status", "track"),
        Index("ix_challenges_created_at", "created_at"),
    )
