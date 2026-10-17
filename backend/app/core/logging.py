"""Structured logging with secret redaction."""

from __future__ import annotations

import json
import logging
import re
import sys
from datetime import UTC, datetime
from typing import Any

SENSITIVE_KEY_PATTERN = re.compile(
    r"(authorization|proxy-authorization|cookie|set-cookie|token|secret|password|passwd|"
    r"api[_-]?key|client[_-]?secret|access[_-]?token|refresh[_-]?token|code|state|session)",
    re.IGNORECASE,
)

# Query string parameters that must never reach access logs (OAuth callback).
SENSITIVE_QUERY_PATTERN = re.compile(r"([?&](?:code|state|code_verifier)=)[^&\s]+", re.IGNORECASE)

REDACTED = "[REDACTED]"
_MAX_VALUE_LENGTH = 512


def redact_value(value: Any) -> Any:
    """Recursively redact sensitive keys and truncate long values."""
    if isinstance(value, dict):
        return {
            key: (REDACTED if SENSITIVE_KEY_PATTERN.search(str(key)) else redact_value(item))
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact_value(item) for item in value]
    if isinstance(value, str) and len(value) > _MAX_VALUE_LENGTH:
        return value[:_MAX_VALUE_LENGTH] + "...[truncated]"
    return value


def redact_text(text: str) -> str:
    return SENSITIVE_QUERY_PATTERN.sub(r"\1[REDACTED]", text)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": redact_text(record.getMessage()),
        }
        extra = getattr(record, "context", None)
        if isinstance(extra, dict):
            payload["context"] = redact_value(extra)
        if record.exc_info:
            payload["exception"] = redact_text(self.formatException(record.exc_info))
        return json.dumps(payload, default=str)


class PlainFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        message = redact_text(record.getMessage())
        extra = getattr(record, "context", None)
        suffix = ""
        if isinstance(extra, dict):
            suffix = " " + json.dumps(redact_value(extra), default=str)
        base = f"{self.formatTime(record)} {record.levelname} {record.name}: {message}{suffix}"
        if record.exc_info:
            base += "\n" + redact_text(self.formatException(record.exc_info))
        return base


class RedactingFilter(logging.Filter):
    """Scrub OAuth codes/states that would otherwise land in access logs."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact_text(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = redact_value(record.args)
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    redact_text(a) if isinstance(a, str) else a for a in record.args
                )
        return True


def configure_logging(level: str = "INFO", json_output: bool = True) -> None:
    """Configure root logging once, idempotently."""
    root = logging.getLogger()
    root.setLevel(level.upper())
    for handler in list(root.handlers):
        root.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter() if json_output else PlainFormatter())
    handler.addFilter(RedactingFilter())
    root.addHandler(handler)

    # Uvicorn installs its own handlers; make them inherit redaction.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "sqlalchemy.engine"):
        logger = logging.getLogger(name)
        logger.handlers = []
        logger.propagate = True
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def log_context(**kwargs: Any) -> dict[str, Any]:
    """Build a redacted structured-logging context dict."""
    return {"context": redact_value(kwargs)}
