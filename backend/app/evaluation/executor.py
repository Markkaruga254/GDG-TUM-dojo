"""Evaluation execution boundary.

The MVP runs metadata-only checks synchronously inside the request. The
:class:`EvaluationExecutor` protocol is the seam for a future Redis/worker-based
implementation: nothing else in the API layer knows *where* evaluation runs.
"""

from __future__ import annotations

from typing import Protocol

from app.evaluation.probe import GitHubRepoProbe
from app.evaluation.rules import EvaluationConfig
from app.evaluation.runner import EvaluationOutcome, evaluate_repository
from app.integrations.github import GitHubClient, RepoRef


class EvaluationExecutor(Protocol):
    def execute(
        self, config: EvaluationConfig, ref: RepoRef, evidence_urls: list[str]
    ) -> EvaluationOutcome: ...


class SynchronousExecutor:
    """Runs the deterministic runner inline, after a single repository lookup."""

    def __init__(self, client: GitHubClient) -> None:
        self._client = client

    def execute(
        self, config: EvaluationConfig, ref: RepoRef, evidence_urls: list[str]
    ) -> EvaluationOutcome:
        probe = GitHubRepoProbe(self._client, ref)
        return evaluate_repository(config, probe, evidence_urls=evidence_urls)
