"""Submission and evaluation models."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.security import now_utc
from app.db.base import Base, TimestampMixin
from app.models.enums import EvaluationStatus, SubmissionStatus
from app.models.types import enum_check, enum_column


class Submission(TimestampMixin, Base):
    __tablename__ = "submissions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    challenge_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("challenges.id", ondelete="CASCADE"), nullable=False
    )

    repo_url: Mapped[str] = mapped_column(String(300), nullable=False)
    repo_full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    evidence_urls: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb")
    )

    status: Mapped[SubmissionStatus] = mapped_column(
        enum_column(SubmissionStatus, "submission_status"),
        nullable=False,
        default=SubmissionStatus.PENDING,
        server_default=SubmissionStatus.PENDING.value,
    )
    points_awarded: Mapped[int | None] = mapped_column(Integer)
    evaluation_summary: Mapped[str | None] = mapped_column(Text)
    results: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    evaluation_attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )

    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=now_utc, server_default=func.now()
    )
    evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Moderation: disqualification removes a submission from scoring entirely.
    is_disqualified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    disqualification_reason: Mapped[str | None] = mapped_column(String(500))
    disqualified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    disqualified_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )

    # Authorized score correction (takes precedence over computed points).
    score_override_points: Mapped[int | None] = mapped_column(Integer)
    score_override_reason: Mapped[str | None] = mapped_column(String(500))
    score_overridden_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    score_overridden_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )

    evaluations: Mapped[list[Evaluation]] = relationship(
        back_populates="submission", cascade="all, delete-orphan", passive_deletes=True
    )

    __table_args__ = (
        CheckConstraint(
            "points_awarded IS NULL OR points_awarded >= 0", name="points_non_negative"
        ),
        CheckConstraint(
            "score_override_points IS NULL OR score_override_points >= 0",
            name="override_points_non_negative",
        ),
        Index("ix_submissions_user_id", "user_id"),
        Index("ix_submissions_challenge_id", "challenge_id"),
        Index("ix_submissions_user_challenge", "user_id", "challenge_id"),
        Index("ix_submissions_challenge_status", "challenge_id", "status"),
        Index("ix_submissions_user_submitted_at", "user_id", "submitted_at"),
        Index("ix_submissions_status", "status"),
    )

    @property
    def effective_points(self) -> int:
        """Points used for scoring: authorized override wins over computed score."""
        if self.score_override_points is not None:
            return self.score_override_points
        return self.points_awarded or 0

    @property
    def counts_for_leaderboard(self) -> bool:
        return (
            not self.is_disqualified
            and self.evaluated_at is not None
            and self.status in (SubmissionStatus.PASSED, SubmissionStatus.FAILED)
        )


class Evaluation(Base):
    __tablename__ = "evaluations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    submission_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[EvaluationStatus] = mapped_column(
        enum_column(EvaluationStatus, "evaluation_status"), nullable=False
    )
    checks: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb")
    )
    max_score: Mapped[int] = mapped_column(Integer, nullable=False)
    awarded_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    feedback: Mapped[str | None] = mapped_column(Text)
    evaluator_version: Mapped[str] = mapped_column(String(32), nullable=False)

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=now_utc, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=now_utc, server_default=func.now()
    )

    submission: Mapped[Submission] = relationship(back_populates="evaluations")

    __table_args__ = (
        CheckConstraint(enum_check("status", EvaluationStatus), name="status_valid"),
        CheckConstraint("max_score >= 0", name="max_score_non_negative"),
        CheckConstraint(
            "awarded_score >= 0 AND awarded_score <= max_score", name="awarded_within_bounds"
        ),
        Index("ix_evaluations_submission_id", "submission_id"),
        Index("ix_evaluations_created_at", "created_at"),
    )
