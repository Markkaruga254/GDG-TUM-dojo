"""Administrative endpoints (role management, moderation, audit trail).

Authorization is enforced by dependencies: ``RequireStaffDep`` (moderator/admin)
and ``RequireAdminDep`` (admin). Every mutation is written to the audit trail.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query

from app.core.dependencies import (
    DbDep,
    PaginationDep,
    RequireAdminDep,
    RequireStaffDep,
    SettingsDep,
)
from app.core.errors import NotFound
from app.models import UserRole
from app.repositories.submissions import SubmissionRepository
from app.repositories.users import UserRepository
from app.schemas.admin import (
    AdminActionResponse,
    AdminUserSummary,
    DisqualifyRequest,
    RoleUpdate,
    ScoreOverrideRequest,
    UserStatusUpdate,
)
from app.schemas.audit import AuditLogPublic
from app.schemas.badge import BadgeCreate, BadgeGrant, BadgePublic, BadgeUpdate
from app.schemas.common import ErrorResponse, Page
from app.schemas.submission import SubmissionDetail, SubmissionSummary
from app.services.admin import AdminService
from app.services.audit import AuditService
from app.services.badges import BadgeService
from app.services.submissions import SubmissionService

router = APIRouter()


# --- users --------------------------------------------------------------------------
@router.get(
    "/users",
    response_model=Page[AdminUserSummary],
    summary="List users (moderator/admin)",
)
def list_users(
    actor: RequireStaffDep,
    db: DbDep,
    pagination: PaginationDep,
    search: Annotated[str | None, Query(max_length=100)] = None,
    role: Annotated[UserRole | None, Query()] = None,
    is_active: Annotated[bool | None, Query()] = None,
) -> Page[AdminUserSummary]:
    users, total = AdminService(db).list_users(
        search=search,
        role=role.value if role else None,
        is_active=is_active,
        limit=pagination.page_size,
        offset=pagination.offset,
    )
    return Page.build(
        items=[AdminUserSummary.model_validate(user) for user in users],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.patch(
    "/users/{user_id}/role",
    response_model=AdminUserSummary,
    responses={
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
    summary="Change a user's role (admin)",
)
def change_user_role(
    user_id: uuid.UUID, payload: RoleUpdate, actor: RequireAdminDep, db: DbDep
) -> AdminUserSummary:
    user = AdminService(db).change_role(actor, user_id, payload.role, payload.reason)
    db.commit()
    return AdminUserSummary.model_validate(user)


@router.patch(
    "/users/{user_id}/status",
    response_model=AdminUserSummary,
    responses={
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
    summary="Activate or deactivate a user (admin)",
)
def change_user_status(
    user_id: uuid.UUID, payload: UserStatusUpdate, actor: RequireAdminDep, db: DbDep
) -> AdminUserSummary:
    user = AdminService(db).change_status(actor, user_id, payload.is_active, payload.reason)
    db.commit()
    return AdminUserSummary.model_validate(user)


# --- submissions -----------------------------------------------------------------------
@router.get(
    "/submissions",
    response_model=Page[SubmissionSummary],
    summary="List a challenge's submissions (moderator/admin)",
)
def list_challenge_submissions(
    actor: RequireStaffDep,
    db: DbDep,
    settings: SettingsDep,
    pagination: PaginationDep,
    challenge_id: Annotated[uuid.UUID, Query()],
) -> Page[SubmissionSummary]:
    service = SubmissionService(db, settings)
    submissions, total = SubmissionRepository(db).list_for_challenge(
        challenge_id, limit=pagination.page_size, offset=pagination.offset
    )
    return Page.build(
        items=[service.to_summary(submission) for submission in submissions],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post(
    "/submissions/{submission_id}/disqualify",
    response_model=SubmissionDetail,
    responses={
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
    summary="Disqualify a submission (moderator/admin)",
)
def disqualify_submission(
    submission_id: uuid.UUID,
    payload: DisqualifyRequest,
    actor: RequireStaffDep,
    db: DbDep,
    settings: SettingsDep,
) -> SubmissionDetail:
    submission = AdminService(db).disqualify(actor, submission_id, payload.reason)
    db.commit()
    return SubmissionService(db, settings).to_detail(submission)


@router.post(
    "/submissions/{submission_id}/reinstate",
    response_model=SubmissionDetail,
    responses={
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
    summary="Reinstate a disqualified submission (moderator/admin)",
)
def reinstate_submission(
    submission_id: uuid.UUID, actor: RequireStaffDep, db: DbDep, settings: SettingsDep
) -> SubmissionDetail:
    submission = AdminService(db).reinstate(actor, submission_id)
    db.commit()
    return SubmissionService(db, settings).to_detail(submission)


@router.post(
    "/submissions/{submission_id}/score",
    response_model=SubmissionDetail,
    responses={
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
    summary="Override a submission score (admin)",
)
def override_submission_score(
    submission_id: uuid.UUID,
    payload: ScoreOverrideRequest,
    actor: RequireAdminDep,
    db: DbDep,
    settings: SettingsDep,
) -> SubmissionDetail:
    submission = AdminService(db).override_score(
        actor, submission_id, payload.points, payload.reason
    )
    db.commit()
    return SubmissionService(db, settings).to_detail(submission)


@router.delete(
    "/submissions/{submission_id}/score-override",
    response_model=SubmissionDetail,
    responses={
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
    summary="Clear a score override (admin)",
)
def clear_submission_score(
    submission_id: uuid.UUID, actor: RequireAdminDep, db: DbDep, settings: SettingsDep
) -> SubmissionDetail:
    submission = AdminService(db).clear_score_override(actor, submission_id)
    db.commit()
    return SubmissionService(db, settings).to_detail(submission)


# --- audit trail ---------------------------------------------------------------------------
@router.get(
    "/audit-logs",
    response_model=Page[AuditLogPublic],
    responses={403: {"model": ErrorResponse}},
    summary="Read the audit trail (admin)",
)
def list_audit_logs(
    actor: RequireAdminDep,
    db: DbDep,
    pagination: PaginationDep,
    action: Annotated[str | None, Query(max_length=64)] = None,
    actor_id: Annotated[uuid.UUID | None, Query()] = None,
) -> Page[AuditLogPublic]:
    entries, total = AuditService(db).list_entries(
        action=action, actor_id=actor_id, limit=pagination.page_size, offset=pagination.offset
    )
    return Page.build(
        items=[AuditLogPublic.model_validate(entry) for entry in entries],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


# --- badges -----------------------------------------------------------------------------------
@router.post(
    "/badges",
    response_model=BadgePublic,
    status_code=201,
    responses={403: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
    summary="Create a badge (admin)",
)
def create_badge(payload: BadgeCreate, actor: RequireAdminDep, db: DbDep) -> BadgePublic:
    badge = BadgeService(db).create_badge(actor, payload)
    db.commit()
    return BadgePublic.model_validate(badge)


@router.patch(
    "/badges/{badge_id}",
    response_model=BadgePublic,
    responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="Update a badge (admin)",
)
def update_badge(
    badge_id: uuid.UUID, payload: BadgeUpdate, actor: RequireAdminDep, db: DbDep
) -> BadgePublic:
    badge = BadgeService(db).update_badge(actor, badge_id, payload)
    db.commit()
    return BadgePublic.model_validate(badge)


@router.post(
    "/users/{user_id}/badges/{badge_slug}",
    response_model=AdminActionResponse,
    responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="Grant a badge to a user (moderator/admin)",
)
def grant_badge(
    user_id: uuid.UUID,
    badge_slug: str,
    payload: BadgeGrant,
    actor: RequireStaffDep,
    db: DbDep,
) -> AdminActionResponse:
    target = UserRepository(db).get_by_id(user_id)
    if target is None:
        raise NotFound("User not found.")
    created = BadgeService(db).grant_badge(actor, target, badge_slug, payload.reason)
    db.commit()
    message = "Badge granted." if created else "User already has this badge."
    return AdminActionResponse(message=message)
