"""Submission service: creation rules, ownership and results assembly."""

from __future__ import annotations

import uuid
from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import Conflict, NotFound, RateLimited, ValidationFailed
from app.core.security import now_utc
from app.integrations.github import parse_repo_url
from app.models import Evaluation, Submission, SubmissionStatus, User
from app.repositories.challenges import ChallengeRepository
from app.repositories.submissions import EvaluationRepository, SubmissionRepository
from app.schemas.submission import (
    CheckResultOut,
    EvaluationOut,
    SubmissionCreate,
    SubmissionDetail,
    SubmissionResults,
    SubmissionSummary,
)
from app.services.challenges import ChallengeService


class SubmissionService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.submissions = SubmissionRepository(db)
        self.evaluations = EvaluationRepository(db)
        self.challenges = ChallengeRepository(db)
        self.challenge_service = ChallengeService(db)

    # --- creation -----------------------------------------------------------------
    def create_submission(
        self, actor: User, challenge_id: uuid.UUID, payload: SubmissionCreate
    ) -> Submission:
        challenge = self.challenges.get_by_id(challenge_id)
        if challenge is None:
            raise NotFound("Challenge not found.")

        is_open, reason = self.challenge_service.is_open(challenge)
        if not is_open:
            messages = {
                "challenge_not_published": "This challenge is not open for submissions.",
                "challenge_not_started": "This challenge has not started yet.",
                "challenge_closed": "This challenge is closed for submissions.",
            }
            raise ValidationFailed(
                messages.get(reason or "", "Challenge is not open."), code=reason
            )

        ref = parse_repo_url(payload.repo_url)

        if len(payload.evidence_urls) > self.settings.max_evidence_urls:
            raise ValidationFailed(
                f"At most {self.settings.max_evidence_urls} evidence URLs are allowed.",
                details=[{"field": "evidence_urls"}],
            )
        notes = payload.notes
        if notes and len(notes) > self.settings.max_notes_length:
            raise ValidationFailed(
                f"Notes must be at most {self.settings.max_notes_length} characters.",
                details=[{"field": "notes"}],
            )

        active_duplicate = self.submissions.find_active_duplicate(
            actor.id, challenge.id, ref.full_name
        )
        if active_duplicate is not None:
            raise Conflict(
                "You already have a pending submission for this repository on this challenge.",
                details=[{"submission_id": str(active_duplicate.id)}],
            )

        now = now_utc()
        last_submitted = self.submissions.latest_submission_at(actor.id, challenge.id)
        if last_submitted is not None and self.settings.submission_cooldown_seconds > 0:
            elapsed = (now - last_submitted).total_seconds()
            if elapsed < self.settings.submission_cooldown_seconds:
                retry_after = int(self.settings.submission_cooldown_seconds - elapsed) + 1
                raise RateLimited(
                    "Please wait before submitting again for this challenge.",
                    details=[{"retry_after_seconds": retry_after}],
                )

        recent = self.submissions.count_since(actor.id, challenge.id, now - timedelta(days=1))
        if recent >= self.settings.max_submissions_per_challenge_per_day:
            raise RateLimited(
                "Daily submission limit reached for this challenge. Try again tomorrow.",
                details=[{"limit": self.settings.max_submissions_per_challenge_per_day}],
            )

        submission = Submission(
            user_id=actor.id,
            challenge_id=challenge.id,
            repo_url=ref.canonical_url,
            repo_full_name=ref.full_name,
            notes=notes,
            evidence_urls=payload.evidence_urls,
            status=SubmissionStatus.PENDING,
            submitted_at=now,
        )
        self.submissions.add(submission)
        self.db.flush()
        return submission

    # --- reads -------------------------------------------------------------------------
    def get_for_actor(self, actor: User, submission_id: uuid.UUID) -> Submission:
        submission = self.submissions.get_by_id(submission_id)
        if submission is None:
            raise NotFound("Submission not found.")
        if submission.user_id != actor.id and not actor.is_staff:
            # Do not reveal the existence of other users' submissions.
            raise NotFound("Submission not found.")
        return submission

    def list_mine(
        self,
        actor: User,
        *,
        challenge_id: uuid.UUID | None = None,
        statuses: list[SubmissionStatus] | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Submission], int]:
        return self.submissions.list_for_user(
            actor.id,
            challenge_id=challenge_id,
            statuses=statuses,
            limit=limit,
            offset=offset,
        )

    def results_for_actor(self, actor: User, submission_id: uuid.UUID) -> SubmissionResults:
        submission = self.get_for_actor(actor, submission_id)
        challenge = self.challenges.get_by_id(submission.challenge_id)
        if challenge is None:  # pragma: no cover - FK guarantees existence
            raise NotFound("Challenge not found.")
        evaluation = self.evaluations.latest_for_submission(submission.id)
        return SubmissionResults(
            submission=self.to_detail(submission),
            evaluation=self.to_evaluation_out(evaluation),
            challenge_slug=challenge.slug,
            challenge_title=challenge.title,
            max_points=challenge.max_points,
            effective_points=submission.effective_points,
            counts_for_leaderboard=submission.counts_for_leaderboard
            and challenge.status.value != "draft",
        )

    # --- helpers -------------------------------------------------------------------------
    def to_summary(self, submission: Submission) -> SubmissionSummary:
        summary = SubmissionSummary.model_validate(submission)
        return summary.model_copy(update={"effective_points": submission.effective_points})

    def to_detail(self, submission: Submission) -> SubmissionDetail:
        detail = SubmissionDetail.model_validate(submission)
        return detail.model_copy(update={"effective_points": submission.effective_points})

    def to_evaluation_out(self, evaluation: Evaluation | None) -> EvaluationOut | None:
        if evaluation is None:
            return None
        checks = [
            CheckResultOut.model_validate(check)
            if isinstance(check, dict)
            else CheckResultOut(**check)
            for check in (evaluation.checks or [])
        ]
        return EvaluationOut(
            id=evaluation.id,
            status=evaluation.status,
            max_score=evaluation.max_score,
            awarded_score=evaluation.awarded_score,
            feedback=evaluation.feedback,
            evaluator_version=evaluation.evaluator_version,
            started_at=evaluation.started_at,
            completed_at=evaluation.completed_at,
            checks=checks,
        )
