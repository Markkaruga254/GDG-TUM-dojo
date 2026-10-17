"""Leaderboard aggregation and badge metrics.

Documented scoring policy (see README "Scoring and leaderboard policy"):

1. Only finalized, non-disqualified submissions count (status passed/failed with
   an ``evaluated_at`` timestamp and a persisted score).
2. Challenges in ``draft`` do not count; archived challenges keep their points.
3. Deactivated users are excluded.
4. A user's per-challenge score is their **best** effective score for that
   challenge (score override wins over the computed score).
5. ``total_points`` = sum of per-challenge best scores.
6. ``completed_challenges`` = number of challenges with a positive best score.
7. Tie-breaking order: total points desc, completed challenges desc, achievement
   time asc (the latest per-challenge timestamp at which the score was reached),
   then user id asc for full determinism.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import CTE, case, func, select
from sqlalchemy.orm import Session

from app.models import (
    Challenge,
    ChallengeStatus,
    Submission,
    SubmissionStatus,
    User,
)

_ROW_NUMBER_ORDER = None  # documented above; order is applied inline


def best_scores_cte(track: str | None = None) -> CTE:
    """Per (user, challenge) best effective score, excluding invalid results."""
    points = func.coalesce(Submission.score_override_points, Submission.points_awarded).label(
        "points"
    )
    ranked = (
        select(
            Submission.user_id.label("user_id"),
            Submission.challenge_id.label("challenge_id"),
            Submission.id.label("submission_id"),
            points,
            Submission.evaluated_at.label("evaluated_at"),
            func.row_number()
            .over(
                partition_by=(Submission.user_id, Submission.challenge_id),
                order_by=(
                    points.desc(),
                    Submission.evaluated_at.asc(),
                    Submission.id.asc(),
                ),
            )
            .label("rn"),
        )
        .join(Challenge, Challenge.id == Submission.challenge_id)
        .join(User, User.id == Submission.user_id)
        .where(
            Submission.is_disqualified.is_(False),
            Submission.status.in_((SubmissionStatus.PASSED, SubmissionStatus.FAILED)),
            Submission.evaluated_at.is_not(None),
            Submission.points_awarded.is_not(None),
            Challenge.status != ChallengeStatus.DRAFT,
            User.is_active.is_(True),
        )
    )
    if track:
        ranked = ranked.where(Challenge.track == track)
    ranked_cte = ranked.cte("ranked_submissions")
    return select(ranked_cte).where(ranked_cte.c.rn == 1).cte("best_scores")


def _aggregated(track: str | None = None) -> Any:
    best = best_scores_cte(track)
    return (
        select(
            best.c.user_id.label("user_id"),
            func.coalesce(func.sum(best.c.points), 0).label("total_points"),
            func.count(case((best.c.points > 0, 1))).label("completed_challenges"),
            func.max(best.c.evaluated_at).label("achieved_at"),
        )
        .group_by(best.c.user_id)
        .subquery("aggregated_scores")
    )


def _ranked(track: str | None = None) -> Any:
    aggregated = _aggregated(track)
    return (
        select(
            aggregated.c.user_id,
            aggregated.c.total_points,
            aggregated.c.completed_challenges,
            aggregated.c.achieved_at,
            User.github_username,
            User.display_name,
            User.avatar_url,
            func.row_number()
            .over(
                order_by=(
                    aggregated.c.total_points.desc(),
                    aggregated.c.completed_challenges.desc(),
                    aggregated.c.achieved_at.asc(),
                    aggregated.c.user_id.asc(),
                )
            )
            .label("rank"),
        )
        .join(User, User.id == aggregated.c.user_id)
        .subquery("ranked_users")
    )


class LeaderboardRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def leaderboard(
        self, *, track: str | None = None, limit: int = 20, offset: int = 0
    ) -> tuple[list[dict[str, Any]], int]:
        ranked = _ranked(track)
        total = int(self.session.execute(select(func.count()).select_from(ranked)).scalar_one())
        rows = self.session.execute(
            select(ranked).order_by(ranked.c.rank).limit(limit).offset(offset)
        ).mappings()
        return [dict(row) for row in rows], total

    def user_entry(self, user_id: uuid.UUID, *, track: str | None = None) -> dict[str, Any] | None:
        ranked = _ranked(track)
        row = (
            self.session.execute(select(ranked).where(ranked.c.user_id == user_id))
            .mappings()
            .one_or_none()
        )
        return dict(row) if row else None

    def user_challenge_entries(
        self, user_id: uuid.UUID, *, track: str | None = None
    ) -> list[dict[str, Any]]:
        best = best_scores_cte(track)
        rows = self.session.execute(
            select(
                best.c.challenge_id,
                best.c.points,
                best.c.evaluated_at,
                Challenge.slug,
                Challenge.title,
                Challenge.track,
                Challenge.max_points,
            )
            .join(Challenge, Challenge.id == best.c.challenge_id)
            .where(best.c.user_id == user_id)
            .order_by(best.c.points.desc(), best.c.evaluated_at.asc())
        ).mappings()
        return [dict(row) for row in rows]

    def portfolio_entries(self, user_id: uuid.UUID) -> list[dict[str, Any]]:
        """Best-scoring submission per challenge, including repository details."""
        best = best_scores_cte()
        rows = self.session.execute(
            select(
                best.c.challenge_id,
                best.c.submission_id,
                best.c.points,
                best.c.evaluated_at,
                Challenge.slug,
                Challenge.title,
                Challenge.track,
                Challenge.difficulty,
                Challenge.max_points,
                Submission.repo_full_name,
                Submission.repo_url,
            )
            .join(Challenge, Challenge.id == best.c.challenge_id)
            .join(Submission, Submission.id == best.c.submission_id)
            .where(best.c.user_id == user_id, best.c.points > 0)
            .order_by(best.c.evaluated_at.desc().nullslast(), Challenge.title.asc())
        ).mappings()
        return [dict(row) for row in rows]

    def metrics(self, user_id: uuid.UUID) -> dict[str, int]:
        """Badge metrics derived from the same aggregation as the leaderboard."""
        best = best_scores_cte()
        row = (
            self.session.execute(
                select(
                    func.count().label("challenges_with_results"),
                    func.count(case((best.c.points > 0, 1))).label("challenges_passed"),
                    func.count(
                        case(
                            (
                                best.c.points == Challenge.max_points,
                                1,
                            )
                        )
                    ).label("perfect_scores"),
                )
                .join(Challenge, Challenge.id == best.c.challenge_id)
                .where(best.c.user_id == user_id)
            )
            .mappings()
            .one()
        )
        metrics = {
            "challenges_passed": int(row["challenges_passed"] or 0),
            "perfect_scores": int(row["perfect_scores"] or 0),
        }
        finalized = self.session.execute(
            select(func.count())
            .select_from(Submission)
            .join(Challenge, Challenge.id == Submission.challenge_id)
            .where(
                Submission.user_id == user_id,
                Submission.is_disqualified.is_(False),
                Submission.status.in_((SubmissionStatus.PASSED, SubmissionStatus.FAILED)),
                Challenge.status != ChallengeStatus.DRAFT,
            )
        ).scalar_one()
        metrics["submissions_finalized"] = int(finalized)
        return metrics

    def track_metrics(self, user_id: uuid.UUID, track: str) -> dict[str, int]:
        best = best_scores_cte(track)
        row = (
            self.session.execute(
                select(func.count(case((best.c.points > 0, 1))).label("challenges_passed")).where(
                    best.c.user_id == user_id
                )
            )
            .mappings()
            .one()
        )
        return {"track_challenges_passed": int(row["challenges_passed"] or 0)}

    def user_stats(self, user_id: uuid.UUID, *, track: str | None = None) -> dict[str, Any]:
        aggregated = _aggregated(track)
        row = (
            self.session.execute(select(aggregated).where(aggregated.c.user_id == user_id))
            .mappings()
            .one_or_none()
        )
        if not row:
            return {"total_points": 0, "completed_challenges": 0, "achieved_at": None}
        return dict(row)

    def count_badges(self, user_id: uuid.UUID) -> int:
        from app.models import UserBadge

        return int(
            self.session.execute(
                select(func.count()).select_from(UserBadge).where(UserBadge.user_id == user_id)
            ).scalar_one()
        )

    def count_passed_submissions(self, user_id: uuid.UUID) -> int:
        return int(
            self.session.execute(
                select(func.count())
                .select_from(Submission)
                .where(
                    Submission.user_id == user_id,
                    Submission.status == SubmissionStatus.PASSED,
                    Submission.is_disqualified.is_(False),
                )
            ).scalar_one()
        )


__all__ = ["LeaderboardRepository", "best_scores_cte"]
