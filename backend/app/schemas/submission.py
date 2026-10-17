"""Submission and evaluation-result schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.integrations.github import InvalidRepoUrlError, parse_repo_url
from app.models.enums import EvaluationStatus, SubmissionStatus

MAX_EVIDENCE_URL_LENGTH = 500


def _validate_evidence_url(url: str) -> str:
    candidate = url.strip()
    if not candidate or len(candidate) > MAX_EVIDENCE_URL_LENGTH:
        raise ValueError("evidence URLs must be non-empty and at most 500 characters")
    parts = urlsplit(candidate)
    if parts.scheme.lower() not in {"http", "https"}:
        raise ValueError("evidence URLs must use http:// or https://")
    if parts.username or parts.password:
        raise ValueError("evidence URLs must not contain embedded credentials")
    if not parts.hostname:
        raise ValueError("evidence URL must include a host")
    return candidate


class SubmissionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    repo_url: str = Field(min_length=10, max_length=300)
    notes: str | None = Field(default=None, max_length=4000)
    evidence_urls: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("repo_url")
    @classmethod
    def _validate_repo_url(cls, value: str) -> str:
        try:
            ref = parse_repo_url(value)
        except InvalidRepoUrlError as exc:
            raise ValueError(str(exc)) from exc
        return ref.canonical_url

    @field_validator("evidence_urls")
    @classmethod
    def _validate_evidence_urls(cls, urls: list[str]) -> list[str]:
        cleaned = [_validate_evidence_url(url) for url in urls]
        if len(set(cleaned)) != len(cleaned):
            raise ValueError("duplicate evidence URLs are not allowed")
        return cleaned

    @field_validator("notes")
    @classmethod
    def _clean_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class SubmissionSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    challenge_id: uuid.UUID
    user_id: uuid.UUID
    status: SubmissionStatus
    repo_url: str
    repo_full_name: str
    points_awarded: int | None = None
    effective_points: int = 0
    evaluation_summary: str | None = None
    submitted_at: datetime
    evaluated_at: datetime | None = None
    evaluation_attempts: int = 0
    is_disqualified: bool = False
    disqualification_reason: str | None = None
    score_override_points: int | None = None
    score_override_reason: str | None = None


class SubmissionDetail(SubmissionSummary):
    notes: str | None = None
    evidence_urls: list[str] = Field(default_factory=list)


class CheckResultOut(BaseModel):
    id: str
    type: str
    description: str
    status: str
    max_points: int
    awarded_points: int
    message: str
    required: bool | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)


class EvaluationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: EvaluationStatus
    max_score: int
    awarded_score: int
    feedback: str | None = None
    evaluator_version: str
    started_at: datetime
    completed_at: datetime | None = None
    checks: list[CheckResultOut] = Field(default_factory=list)


class SubmissionResults(BaseModel):
    """Aggregated, owner-visible evaluation results for a submission."""

    submission: SubmissionDetail
    evaluation: EvaluationOut | None = None
    challenge_slug: str
    challenge_title: str
    max_points: int
    effective_points: int
    counts_for_leaderboard: bool
