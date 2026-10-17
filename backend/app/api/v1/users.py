"""User profile endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.dependencies import CurrentUserDep, DbDep
from app.schemas.common import ErrorResponse
from app.schemas.user import UserPortfolio, UserProfile, UserSelf, UserUpdate
from app.services.users import UserService

router = APIRouter()


@router.get("/me", response_model=UserSelf, summary="Get the current user")
def get_me(user: CurrentUserDep) -> UserSelf:
    return UserSelf.model_validate(user)


@router.patch(
    "/me",
    response_model=UserSelf,
    responses={401: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    summary="Update the current user's profile",
)
def update_me(payload: UserUpdate, user: CurrentUserDep, db: DbDep) -> UserSelf:
    service = UserService(db)
    updated = service.update_self(
        user,
        display_name=payload.display_name,
        bio=payload.bio,
        provided=payload.model_fields_set,
    )
    db.commit()
    return UserSelf.model_validate(updated)


@router.get(
    "/{username}/profile",
    response_model=UserProfile,
    responses={404: {"model": ErrorResponse}},
    summary="Public profile with stats",
)
def get_profile(username: str, db: DbDep) -> UserProfile:
    return UserService(db).profile(username)


@router.get(
    "/{username}/portfolio",
    response_model=UserPortfolio,
    responses={404: {"model": ErrorResponse}},
    summary="Public portfolio of scored challenges",
)
def get_portfolio(username: str, db: DbDep) -> UserPortfolio:
    return UserService(db).portfolio(username)
