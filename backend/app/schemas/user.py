"""User-facing schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import UserRole


class UserPublic(BaseModel):
    """Public projection of a user (safe to expose to any visitor)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    github_username: str
    display_name: str | None = None
    avatar_url: str | None = None
    bio: str | None = None
    created_at: datetime


class UserSelf(UserPublic):
    """Owner projection including role and account status."""

    role: UserRole
    is_active: bool
    updated_at: datetime


class UserUpdate(BaseModel):
    """Only these fields may be self-edited. Role and scores are never accepted."""

    model_config = ConfigDict(extra="forbid")

    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    bio: str | None = Field(default=None, max_length=500)


class UserStats(BaseModel):
    total_points: int = 0
    completed_challenges: int = 0
    global_rank: int | None = None
    badges_count: int = 0
    submissions_passed: int = 0


class UserProfile(BaseModel):
    user: UserPublic
    stats: UserStats


class PortfolioEntry(BaseModel):
    challenge_id: uuid.UUID
    challenge_slug: str
    challenge_title: str
    track: str
    difficulty: str
    submission_id: uuid.UUID
    repo_full_name: str
    repo_url: str
    points: int
    max_points: int
    achieved_at: datetime | None = None


class UserPortfolio(BaseModel):
    user: UserPublic
    stats: UserStats
    entries: list[PortfolioEntry]
