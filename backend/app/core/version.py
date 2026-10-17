"""Version constants shared across the application."""

from __future__ import annotations

APP_VERSION = "0.1.0"

# Bump this whenever evaluation semantics, check types or scoring rules change.
# Persisted on every Evaluation row so historical scores stay interpretable.
EVALUATOR_VERSION = "1.0.0"
