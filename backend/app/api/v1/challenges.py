"""Challenge endpoints (public reads, staff-only moderation)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import (
    DbDep,
    PaginationDep,
    RequireStaffDep,
    get_auth_context_optional,
)
from app.schemas.challenge import (
    ChallengeCreate,
    ChallengeDetail,
    ChallengeSummary,
    ChallengeUpdate,
)
from app.schemas.common import ErrorResponse, Page
from app.services.challenges import ChallengeService

router = APIRouter()

OptionalUserDep = Annotated[object, Depends(get_auth_context_optional)]


@router.get("", response_model=Page[ChallengeSummary], summary="List challenges")
def list_challenges(
    db: DbDep,
    pagination: PaginationDep,
    context: OptionalUserDep,
    track: Annotated[str | None, Query(max_length=64)] = None,
    difficulty: Annotated[str | None, Query(max_length=20)] = None,
    status: Annotated[str | None, Query(max_length=20)] = None,
    search: Annotated[str | None, Query(max_length=100)] = None,
    tag: Annotated[str | None, Query(max_length=50)] = None,
) -> Page[ChallengeSummary]:
    viewer = context.user if context else None  # type: ignore[attr-defined]
    service = ChallengeService(db)
    challenges, total = service.list_challenges(
        viewer=viewer,
        track=track,
        difficulty=difficulty,
        status=status,
        search=search,
        tag=tag,
        limit=pagination.page_size,
        offset=pagination.offset,
    )
    return Page.build(
        items=[service.to_summary(challenge) for challenge in challenges],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get(
    "/{slug}",
    response_model=ChallengeDetail,
    responses={404: {"model": ErrorResponse}},
    summary="Get a challenge by slug",
)
def get_challenge(slug: str, db: DbDep, context: OptionalUserDep) -> ChallengeDetail:
    viewer = context.user if context else None  # type: ignore[attr-defined]
    service = ChallengeService(db)
    challenge = service.get_by_slug(slug, viewer=viewer)
    return service.to_detail(challenge)


@router.post(
    "",
    response_model=ChallengeDetail,
    status_code=201,
    responses={403: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    summary="Create a challenge (moderator/admin)",
)
def create_challenge(
    payload: ChallengeCreate, actor: RequireStaffDep, db: DbDep
) -> ChallengeDetail:
    service = ChallengeService(db)
    challenge = service.create_challenge(actor, payload)
    db.commit()
    return service.to_detail(challenge, created_by=actor.github_username)


@router.patch(
    "/{challenge_id}",
    response_model=ChallengeDetail,
    responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="Update a challenge (moderator/admin)",
)
def update_challenge(
    challenge_id: uuid.UUID, payload: ChallengeUpdate, actor: RequireStaffDep, db: DbDep
) -> ChallengeDetail:
    service = ChallengeService(db)
    challenge = service.update_challenge(actor, challenge_id, payload)
    db.commit()
    return service.to_detail(challenge)


@router.post(
    "/{challenge_id}/publish",
    response_model=ChallengeDetail,
    responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="Publish a challenge (moderator/admin)",
)
def publish_challenge(
    challenge_id: uuid.UUID, actor: RequireStaffDep, db: DbDep
) -> ChallengeDetail:
    service = ChallengeService(db)
    challenge = service.publish_challenge(actor, challenge_id)
    db.commit()
    return service.to_detail(challenge)


@router.post(
    "/{challenge_id}/archive",
    response_model=ChallengeDetail,
    responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="Archive a challenge (moderator/admin)",
)
def archive_challenge(
    challenge_id: uuid.UUID, actor: RequireStaffDep, db: DbDep
) -> ChallengeDetail:
    service = ChallengeService(db)
    challenge = service.archive_challenge(actor, challenge_id)
    db.commit()
    return service.to_detail(challenge)
