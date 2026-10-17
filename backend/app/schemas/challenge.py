"""Challenge schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.evaluation.rules import EvaluationConfig
from app.models.enums import ChallengeStatus, Difficulty

SLUG_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
TRACK_PATTERN = r"^[a-z0-9][a-z0-9 _+-]{1,63}$"


class CheckSummary(BaseModel):
    """Student-facing evaluation check summary (internal params withheld)."""

    id: str
    type: str
    description: str
    points: int
    required: bool
    enabled: bool


class ChallengeSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    title: str
    track: str
    difficulty: Difficulty
    tags: list[str]
    max_points: int
    status: ChallengeStatus
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    created_at: datetime


class ChallengeDetail(ChallengeSummary):
    description: str
    instructions: str
    created_by: str | None = None
    evaluation: list[CheckSummary] = Field(default_factory=list)


class ChallengeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=3, max_length=200)
    slug: str | None = Field(default=None, min_length=3, max_length=120, pattern=SLUG_PATTERN)
    description: str = Field(min_length=10, max_length=20_000)
    instructions: str = Field(default="", max_length=50_000)
    track: str = Field(min_length=2, max_length=64, pattern=TRACK_PATTERN)
    difficulty: Difficulty = Difficulty.BEGINNER
    tags: list[str] = Field(default_factory=list, max_length=10)
    max_points: int = Field(ge=1, le=10_000)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    evaluation_config: EvaluationConfig

    @field_validator("tags")
    @classmethod
    def _validate_tags(cls, tags: list[str]) -> list[str]:
        cleaned = [tag.strip().lower() for tag in tags if tag.strip()]
        if any(len(tag) > 50 for tag in cleaned):
            raise ValueError("tags must be at most 50 characters")
        return sorted(set(cleaned))

    @model_validator(mode="after")
    def _validate_window(self) -> ChallengeCreate:
        if self.ends_at and self.starts_at and self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        return self


class ChallengeUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = Field(default=None, min_length=10, max_length=20_000)
    instructions: str | None = Field(default=None, max_length=50_000)
    track: str | None = Field(default=None, min_length=2, max_length=64, pattern=TRACK_PATTERN)
    difficulty: Difficulty | None = None
    tags: list[str] | None = Field(default=None, max_length=10)
    max_points: int | None = Field(default=None, ge=1, le=10_000)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    evaluation_config: EvaluationConfig | None = None

    @field_validator("tags")
    @classmethod
    def _validate_tags(cls, tags: list[str] | None) -> list[str] | None:
        if tags is None:
            return None
        cleaned = [tag.strip().lower() for tag in tags if tag.strip()]
        if any(len(tag) > 50 for tag in cleaned):
            raise ValueError("tags must be at most 50 characters")
        return sorted(set(cleaned))


class ChallengeModerationResponse(BaseModel):
    challenge: ChallengeDetail
    evaluation_total_points: int
    evaluation_problems: list[str] = Field(default_factory=list)


class EvaluationConfigSummary(BaseModel):
    """Read-only view of a challenge's evaluation configuration (staff only)."""

    config: dict[str, Any]
    total_points: int
    problems: list[str] = Field(default_factory=list)
