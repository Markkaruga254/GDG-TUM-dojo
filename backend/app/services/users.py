"""User service: self-service profile updates, public profiles and portfolios."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.errors import NotFound
from app.models import User
from app.repositories.leaderboard import LeaderboardRepository
from app.repositories.users import UserRepository
from app.schemas.user import (
    PortfolioEntry,
    UserPortfolio,
    UserProfile,
    UserPublic,
    UserStats,
)


class UserService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.leaderboard = LeaderboardRepository(db)

    def get_by_username(self, username: str) -> User:
        user = self.users.get_by_username(username)
        if user is None:
            raise NotFound("User not found.")
        return user

    def update_self(
        self, user: User, *, display_name: str | None, bio: str | None, provided: set[str]
    ) -> User:
        """Apply only whitelisted profile fields (role and scores are never editable)."""
        if "display_name" in provided:
            user.display_name = display_name
        if "bio" in provided:
            user.bio = bio
        self.db.flush()
        return user

    def stats_for(self, user: User) -> UserStats:
        entry = self.leaderboard.user_entry(user.id)
        return UserStats(
            total_points=int(entry["total_points"]) if entry else 0,
            completed_challenges=int(entry["completed_challenges"]) if entry else 0,
            global_rank=int(entry["rank"]) if entry else None,
            badges_count=self.leaderboard.count_badges(user.id),
            submissions_passed=self.leaderboard.count_passed_submissions(user.id),
        )

    def profile(self, username: str) -> UserProfile:
        user = self.get_by_username(username)
        return UserProfile(user=UserPublic.model_validate(user), stats=self.stats_for(user))

    def portfolio(self, username: str) -> UserPortfolio:
        user = self.get_by_username(username)
        entries = [
            PortfolioEntry(
                challenge_id=row["challenge_id"],
                challenge_slug=row["slug"],
                challenge_title=row["title"],
                track=row["track"],
                difficulty=str(row["difficulty"]),
                submission_id=row["submission_id"],
                repo_full_name=row["repo_full_name"],
                repo_url=row["repo_url"],
                points=int(row["points"]),
                max_points=int(row["max_points"]),
                achieved_at=row["evaluated_at"],
            )
            for row in self.leaderboard.portfolio_entries(user.id)
        ]
        return UserPortfolio(
            user=UserPublic.model_validate(user),
            stats=self.stats_for(user),
            entries=entries,
        )
