"""Submission endpoints (create, inspect, evaluate, results)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response

from app.core.dependencies import (
    CurrentUserDep,
    DbDep,
    GitHubClientDep,
    PaginationDep,
    SettingsDep,
    rate_limit_dependency,
)
from app.evaluation.executor import SynchronousExecutor
from app.models import SubmissionStatus
from app.schemas.common import ErrorResponse, Page
from app.schemas.submission import (
    SubmissionCreate,
    SubmissionDetail,
    SubmissionResults,
    SubmissionSummary,
)
from app.services.evaluation import EvaluationService
from app.services.submissions import SubmissionService

router = APIRouter()

submission_rate_limit = rate_limit_dependency(
    "submission.create",
    lambda settings: (settings.submission_rate_limit_per_hour, 3600),
)
evaluation_rate_limit = rate_limit_dependency(
    "submission.evaluate",
    lambda settings: (settings.evaluation_rate_limit_per_hour, 3600),
)


@router.post(
    "/challenges/{challenge_id}/submissions",
    response_model=SubmissionDetail,
    status_code=201,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
    },
    dependencies=[Depends(submission_rate_limit)],
    summary="Submit a repository for a challenge",
)
def create_submission(
    challenge_id: uuid.UUID,
    payload: SubmissionCreate,
    actor: CurrentUserDep,
    db: DbDep,
    settings: SettingsDep,
) -> SubmissionDetail:
    service = SubmissionService(db, settings)
    submission = service.create_submission(actor, challenge_id, payload)
    db.commit()
    return service.to_detail(submission)


@router.get(
    "/users/me/submissions",
    response_model=Page[SubmissionSummary],
    summary="List the current user's submissions",
)
def list_my_submissions(
    actor: CurrentUserDep,
    db: DbDep,
    settings: SettingsDep,
    pagination: PaginationDep,
    challenge_id: Annotated[uuid.UUID | None, Query()] = None,
    status: Annotated[SubmissionStatus | None, Query()] = None,
) -> Page[SubmissionSummary]:
    service = SubmissionService(db, settings)
    statuses = [status] if status else None
    submissions, total = service.list_mine(
        actor,
        challenge_id=challenge_id,
        statuses=statuses,
        limit=pagination.page_size,
        offset=pagination.offset,
    )
    return Page.build(
        items=[service.to_summary(submission) for submission in submissions],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get(
    "/submissions/{submission_id}",
    response_model=SubmissionDetail,
    responses={404: {"model": ErrorResponse}},
    summary="Get a submission (owner or staff)",
)
def get_submission(
    submission_id: uuid.UUID, actor: CurrentUserDep, db: DbDep, settings: SettingsDep
) -> SubmissionDetail:
    service = SubmissionService(db, settings)
    submission = service.get_for_actor(actor, submission_id)
    return service.to_detail(submission)


@router.get(
    "/submissions/{submission_id}/results",
    response_model=SubmissionResults,
    responses={404: {"model": ErrorResponse}},
    summary="Get evaluation results for a submission (owner or staff)",
)
def get_submission_results(
    submission_id: uuid.UUID, actor: CurrentUserDep, db: DbDep, settings: SettingsDep
) -> SubmissionResults:
    return SubmissionService(db, settings).results_for_actor(actor, submission_id)


@router.post(
    "/submissions/{submission_id}/evaluate",
    response_model=SubmissionResults,
    responses={
        202: {"model": SubmissionResults, "description": "Evaluation already in progress"},
        404: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
    },
    dependencies=[Depends(evaluation_rate_limit)],
    summary="Trigger evaluation (idempotent)",
)
def evaluate_submission(
    submission_id: uuid.UUID,
    response: Response,
    actor: CurrentUserDep,
    db: DbDep,
    settings: SettingsDep,
    client: GitHubClientDep,
    force: Annotated[bool, Query(description="Staff-only: re-run evaluation")] = False,
) -> SubmissionResults:
    service = EvaluationService(db, settings, SynchronousExecutor(client))
    result = service.trigger(actor, submission_id, force=force)
    if not result.triggered:
        # Idempotent no-op: evaluation is already in progress or already final.
        response.status_code = 202
    return SubmissionService(db, settings).results_for_actor(actor, submission_id)
