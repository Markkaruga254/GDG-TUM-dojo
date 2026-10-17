"""Submission and evaluation data access."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models import (
    ACTIVE_SUBMISSION_STATUSES,
    Evaluation,
    Submission,
    SubmissionStatus,
)


class SubmissionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, submission_id: uuid.UUID) -> Submission | None:
        return self.session.get(Submission, submission_id)

    def list_for_user(
        self,
        user_id: uuid.UUID,
        *,
        challenge_id: uuid.UUID | None = None,
        statuses: list[SubmissionStatus] | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Submission], int]:
        query = select(Submission).where(Submission.user_id == user_id)
        if challenge_id is not None:
            query = query.where(Submission.challenge_id == challenge_id)
        if statuses:
            query = query.where(Submission.status.in_(statuses))
        total = self.session.execute(
            select(func.count()).select_from(query.subquery())
        ).scalar_one()
        rows = (
            self.session.execute(
                query.order_by(Submission.submitted_at.desc(), Submission.id.desc())
                .limit(limit)
                .offset(offset)
            )
            .scalars()
            .all()
        )
        return list(rows), int(total)

    def list_for_challenge(
        self,
        challenge_id: uuid.UUID,
        *,
        statuses: list[SubmissionStatus] | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Submission], int]:
        query = select(Submission).where(Submission.challenge_id == challenge_id)
        if statuses:
            query = query.where(Submission.status.in_(statuses))
        total = self.session.execute(
            select(func.count()).select_from(query.subquery())
        ).scalar_one()
        rows = (
            self.session.execute(
                query.order_by(Submission.submitted_at.desc(), Submission.id.desc())
                .limit(limit)
                .offset(offset)
            )
            .scalars()
            .all()
        )
        return list(rows), int(total)

    def find_active_duplicate(
        self, user_id: uuid.UUID, challenge_id: uuid.UUID, repo_full_name: str
    ) -> Submission | None:
        """Detect an in-flight submission for the same repository."""
        return (
            self.session.execute(
                select(Submission).where(
                    Submission.user_id == user_id,
                    Submission.challenge_id == challenge_id,
                    Submission.repo_full_name == repo_full_name,
                    Submission.status.in_(ACTIVE_SUBMISSION_STATUSES),
                )
            )
            .scalars()
            .first()
        )

    def count_since(
        self,
        user_id: uuid.UUID,
        challenge_id: uuid.UUID,
        since: datetime,
    ) -> int:
        return int(
            self.session.execute(
                select(func.count())
                .select_from(Submission)
                .where(
                    Submission.user_id == user_id,
                    Submission.challenge_id == challenge_id,
                    Submission.submitted_at >= since,
                )
            ).scalar_one()
        )

    def latest_submission_at(self, user_id: uuid.UUID, challenge_id: uuid.UUID) -> datetime | None:
        return self.session.execute(
            select(func.max(Submission.submitted_at)).where(
                Submission.user_id == user_id, Submission.challenge_id == challenge_id
            )
        ).scalar_one_or_none()

    def claim_for_evaluation(
        self, submission_id: uuid.UUID, *, include_final: bool = False
    ) -> bool:
        """Atomically move a submission into ``running``.

        Returns True only for the caller that won the transition, which makes the
        evaluation trigger idempotent even under concurrent requests. ``include_final``
        additionally lets staff force a re-run of an already-passed submission.
        """
        claimable = [
            SubmissionStatus.PENDING,
            SubmissionStatus.FAILED,
            SubmissionStatus.ERROR,
        ]
        if include_final:
            claimable.append(SubmissionStatus.PASSED)
        result = self.session.execute(
            update(Submission)
            .where(
                Submission.id == submission_id,
                Submission.status.in_(claimable),
            )
            .values(
                status=SubmissionStatus.RUNNING,
                evaluation_attempts=Submission.evaluation_attempts + 1,
            )
            .returning(Submission.id)
        )
        return result.scalar_one_or_none() is not None

    def add(self, submission: Submission) -> Submission:
        self.session.add(submission)
        return submission


class EvaluationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, evaluation_id: uuid.UUID) -> Evaluation | None:
        return self.session.get(Evaluation, evaluation_id)

    def latest_for_submission(self, submission_id: uuid.UUID) -> Evaluation | None:
        return (
            self.session.execute(
                select(Evaluation)
                .where(Evaluation.submission_id == submission_id)
                .order_by(Evaluation.created_at.desc(), Evaluation.id.desc())
                .limit(1)
            )
            .scalars()
            .first()
        )

    def count_for_submission(self, submission_id: uuid.UUID) -> int:
        return int(
            self.session.execute(
                select(func.count())
                .select_from(Evaluation)
                .where(Evaluation.submission_id == submission_id)
            ).scalar_one()
        )

    def add(self, evaluation: Evaluation) -> Evaluation:
        self.session.add(evaluation)
        return evaluation
