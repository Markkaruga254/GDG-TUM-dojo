"""Leaderboard endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from app.core.dependencies import CurrentUserDep, DbDep, PaginationDep
from app.schemas.common import Page
from app.schemas.leaderboard import LeaderboardEntry, LeaderboardMe
from app.services.leaderboard import LeaderboardService

router = APIRouter()


@router.get("", response_model=Page[LeaderboardEntry], summary="Global leaderboard")
def get_leaderboard(
    db: DbDep,
    pagination: PaginationDep,
    track: Annotated[str | None, Query(max_length=64)] = None,
) -> Page[LeaderboardEntry]:
    return LeaderboardService(db).leaderboard(
        track=track, page=pagination.page, page_size=pagination.page_size
    )


@router.get("/me", response_model=LeaderboardMe, summary="Current user's leaderboard standing")
def get_my_leaderboard(
    user: CurrentUserDep,
    db: DbDep,
    track: Annotated[str | None, Query(max_length=64)] = None,
) -> LeaderboardMe:
    return LeaderboardService(db).me(user, track=track)
