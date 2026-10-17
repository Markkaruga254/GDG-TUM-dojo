"""Evaluation service: idempotent triggering, persistence and badge awarding.

The heavy lifting lives in :mod:`app.evaluation`. This service owns the state
machine (pending → running → passed/failed/error), persistence and auditing.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import Conflict, NotFound
from app.core.logging import get_logger
from app.core.security import now_utc
from app.evaluation.executor import EvaluationExecutor
from app.evaluation.runner import EvaluationOutcome
from app.integrations.github import RepoRef
from app.models import (
    IN_FLIGHT_SUBMISSION_STATUSES,
    Evaluation,
    EvaluationStatus,
    Submission,
    SubmissionStatus,
    User,
)
from app.repositories.submissions import EvaluationRepository, SubmissionRepository
from app.services.audit import AuditAction, AuditService
from app.services.badges import BadgeService

logger = get_logger(__name__)


@dataclass(frozen=True)
class EvaluationTriggerResult:
    submission: Submission
    evaluation: Evaluation | None
    triggered: bool
    in_progress: bool


class EvaluationService:
    def __init__(
        self,
        db: Session,
        settings: Settings,
        executor: EvaluationExecutor,
    ) -> None:
        self.db = db
        self.settings = settings
        self.executor = executor
        self.submissions = SubmissionRepository(db)
        self.evaluations = EvaluationRepository(db)
        self.audit = AuditService(db)
        self.badges = BadgeService(db)

    def trigger(
        self, actor: User, submission_id: uuid.UUID, *, force: bool = False
    ) -> EvaluationTriggerResult:
        """Run or return the current evaluation for a submission (idempotent)."""
        submission = self.submissions.get_by_id(submission_id)
        if submission is None or (submission.user_id != actor.id and not actor.is_staff):
            raise NotFound("Submission not found.")

        if submission.status in IN_FLIGHT_SUBMISSION_STATUSES:
            return EvaluationTriggerResult(
                submission=submission,
                evaluation=self.evaluations.latest_for_submission(submission.id),
                triggered=False,
                in_progress=True,
            )

        already_final = submission.status in (SubmissionStatus.PASSED, SubmissionStatus.FAILED)
        if already_final and not force:
            return EvaluationTriggerResult(
                submission=submission,
                evaluation=self.evaluations.latest_for_submission(submission.id),
                triggered=False,
                in_progress=False,
            )
        if force and not actor.is_staff:
            raise NotFound("Submission not found.")

        # Validate configuration *before* claiming, so a misconfigured challenge
        # cannot leave a submission stuck in ``running``.
        from app.repositories.challenges import ChallengeRepository
        from app.services.challenges import ChallengeService

        challenge = ChallengeRepository(self.db).get_by_id(submission.challenge_id)
        if challenge is None:
            raise NotFound("Challenge not found.")
        config = ChallengeService(self.db).evaluation_config(challenge)
        repo_ref = RepoRef(*_split_full_name(submission.repo_full_name))

        if not self.submissions.claim_for_evaluation(submission.id, include_final=force):
            self.db.refresh(submission)
            return EvaluationTriggerResult(
                submission=submission,
                evaluation=self.evaluations.latest_for_submission(submission.id),
                triggered=False,
                in_progress=submission.status in IN_FLIGHT_SUBMISSION_STATUSES,
            )
        self.db.refresh(submission)

        started_at = now_utc()
        outcome = self._execute(config, repo_ref, list(submission.evidence_urls or []))
        evaluation = self._persist(submission, outcome, started_at=started_at)
        self.db.flush()

        if outcome.status is EvaluationStatus.COMPLETED:
            self.badges.evaluate_awards(
                self.db.get(User, submission.user_id)  # type: ignore[arg-type]
            )

        if force:
            self.audit.record(
                actor,
                AuditAction.SUBMISSION_FORCE_EVALUATE,
                target_type="submission",
                target_id=str(submission.id),
                metadata={
                    "submission_status": submission.status.value,
                    "awarded_score": evaluation.awarded_score,
                },
            )
        self.db.commit()
        return EvaluationTriggerResult(
            submission=submission,
            evaluation=evaluation,
            triggered=True,
            in_progress=False,
        )

    # --- internals -----------------------------------------------------------------
    def _execute(self, config, repo_ref: RepoRef, evidence: list[str]) -> EvaluationOutcome:  # type: ignore[no-untyped-def]
        try:
            return self.executor.execute(config, repo_ref, evidence)
        except Exception:
            logger.exception(
                "evaluation executor failed",
                extra={"context": {"repo": repo_ref.full_name}},
            )
            from app.evaluation.runner import EvaluationOutcome as Outcome

            return Outcome(
                status=EvaluationStatus.ERROR,
                submission_status=SubmissionStatus.ERROR,
                checks=[],
                awarded_score=0,
                max_score=config.total_points(),
                feedback="The evaluation could not be completed. It can be retried.",
                summary="Evaluation could not be completed.",
            )

    def _persist(
        self, submission: Submission, outcome: EvaluationOutcome, *, started_at: datetime
    ) -> Evaluation:
        completed_at = now_utc()
        evaluation = Evaluation(
            submission_id=submission.id,
            status=outcome.status,
            checks=outcome.checks,
            max_score=outcome.max_score,
            awarded_score=outcome.awarded_score,
            feedback=outcome.feedback,
            evaluator_version=self.settings.evaluator_version,
            started_at=started_at,
            completed_at=completed_at,
        )
        self.evaluations.add(evaluation)
        self.db.flush()

        submission.status = outcome.submission_status
        submission.points_awarded = outcome.awarded_score
        submission.evaluation_summary = outcome.summary
        submission.evaluated_at = completed_at
        submission.results = {
            "evaluation_id": str(evaluation.id),
            "evaluator_version": self.settings.evaluator_version,
            "max_score": outcome.max_score,
            "awarded_score": outcome.awarded_score,
            "summary": outcome.summary,
            "checks": outcome.checks,
        }
        return evaluation


def _split_full_name(full_name: str) -> tuple[str, str]:
    owner, _, name = full_name.partition("/")
    if not owner or not name:
        raise Conflict("Stored repository identifier is malformed.")
    return owner, name
