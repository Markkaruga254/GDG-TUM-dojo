"""Extensible, deterministic evaluation engine (metadata checks only)."""

from app.evaluation.executor import EvaluationExecutor, SynchronousExecutor
from app.evaluation.rules import (
    CHECK_TYPE_DESCRIPTIONS,
    EvaluationConfig,
    check_result,
    validate_config_points,
)
from app.evaluation.runner import EvaluationOutcome, evaluate_repository

__all__ = [
    "CHECK_TYPE_DESCRIPTIONS",
    "EvaluationConfig",
    "EvaluationExecutor",
    "EvaluationOutcome",
    "SynchronousExecutor",
    "check_result",
    "evaluate_repository",
    "validate_config_points",
]
