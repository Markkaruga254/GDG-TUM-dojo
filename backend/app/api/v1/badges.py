"""Badge endpoints (public listings)."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.dependencies import DbDep
from app.schemas.badge import BadgePublic, UserBadgeEntry
from app.schemas.common import ErrorResponse
from app.services.badges import BadgeService
from app.services.users import UserService

router = APIRouter()


@router.get("/badges", response_model=list[BadgePublic], summary="List all badges")
def list_badges(db: DbDep) -> list[BadgePublic]:
    badges = BadgeService(db).list_badges()
    return [BadgePublic.model_validate(badge) for badge in badges]


@router.get(
    "/users/{username}/badges",
    response_model=list[UserBadgeEntry],
    responses={404: {"model": ErrorResponse}},
    summary="List badges earned by a user",
)
def list_user_badges(username: str, db: DbDep) -> list[UserBadgeEntry]:
    user = UserService(db).get_by_username(username)
    awards = BadgeService(db).list_for_user(user)
    return [
        UserBadgeEntry(badge=BadgePublic.model_validate(badge), awarded_at=awarded_at)
        for badge, awarded_at in awards
    ]
