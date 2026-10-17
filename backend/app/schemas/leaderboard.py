"""Leaderboard schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class LeaderboardEntry(BaseModel):
    rank: int
    user_id: uuid.UUID
    github_username: str
    display_name: str | None = None
    avatar_url: str | None = None
    total_points: int
    completed_challenges: int
    achieved_at: datetime | None = None


class LeaderboardChallengeEntry(BaseModel):
    challenge_id: uuid.UUID
    challenge_slug: str
    challenge_title: str
    track: str
    points: int
    max_points: int
    achieved_at: datetime | None = None


class LeaderboardMe(BaseModel):
    rank: int | None = None
    track: str | None = None
    total_points: int = 0
    completed_challenges: int = 0
    achieved_at: datetime | None = None
    entries: list[LeaderboardChallengeEntry] = []
