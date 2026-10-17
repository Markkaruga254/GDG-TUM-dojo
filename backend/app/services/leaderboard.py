"""Leaderboard service: documented aggregation exposed through the API."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import User
from app.repositories.leaderboard import LeaderboardRepository
from app.schemas.common import Page
from app.schemas.leaderboard import (
    LeaderboardChallengeEntry,
    LeaderboardEntry,
    LeaderboardMe,
)


class LeaderboardService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = LeaderboardRepository(db)

    def leaderboard(
        self, *, track: str | None = None, page: int = 1, page_size: int = 20
    ) -> Page[LeaderboardEntry]:
        offset = (page - 1) * page_size
        rows, total = self.repository.leaderboard(track=track, limit=page_size, offset=offset)
        return Page.build(
            items=[self._to_entry(row) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
        )

    def me(self, user: User, *, track: str | None = None) -> LeaderboardMe:
        entry = self.repository.user_entry(user.id, track=track)
        entries = [
            LeaderboardChallengeEntry(
                challenge_id=row["challenge_id"],
                challenge_slug=row["slug"],
                challenge_title=row["title"],
                track=row["track"],
                points=int(row["points"]),
                max_points=int(row["max_points"]),
                achieved_at=row["evaluated_at"],
            )
            for row in self.repository.user_challenge_entries(user.id, track=track)
        ]
        if entry is None:
            return LeaderboardMe(track=track, entries=entries)
        return LeaderboardMe(
            rank=int(entry["rank"]),
            track=track,
            total_points=int(entry["total_points"]),
            completed_challenges=int(entry["completed_challenges"]),
            achieved_at=entry["achieved_at"],
            entries=entries,
        )

    @staticmethod
    def _to_entry(row: dict) -> LeaderboardEntry:
        return LeaderboardEntry(
            rank=int(row["rank"]),
            user_id=row["user_id"],
            github_username=row["github_username"],
            display_name=row["display_name"],
            avatar_url=row["avatar_url"],
            total_points=int(row["total_points"]),
            completed_challenges=int(row["completed_challenges"]),
            achieved_at=row["achieved_at"],
        )
