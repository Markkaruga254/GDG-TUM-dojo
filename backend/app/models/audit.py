"""Audit log model for privileged and score-affecting actions."""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, String, Uuid, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.security import now_utc
from app.db.base import Base

_SENSITIVE_KEYS = re.compile(
    r"(authorization|cookie|token|secret|password|api[_-]?key|client[_-]?secret)",
    re.IGNORECASE,
)
_MAX_STRING_LENGTH = 256
_MAX_METADATA_BYTES = 4096


def sanitize_audit_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    """Drop sensitive keys, truncate long values and cap total payload size."""
    if not metadata:
        return {}

    def _clean(value: Any, depth: int = 0) -> Any:
        if depth > 4:
            return "[truncated]"
        if isinstance(value, dict):
            return {
                key: ("[redacted]" if _SENSITIVE_KEYS.search(str(key)) else _clean(item, depth + 1))
                for key, item in value.items()
            }
        if isinstance(value, (list, tuple)):
            return [_clean(item, depth + 1) for item in value[:50]]
        if isinstance(value, str) and len(value) > _MAX_STRING_LENGTH:
            return value[:_MAX_STRING_LENGTH] + "...[truncated]"
        if isinstance(value, (int, float, bool)) or value is None:
            return value
        return str(value)[:_MAX_STRING_LENGTH]

    cleaned = _clean(metadata)
    encoded = len(str(cleaned).encode("utf-8"))
    if encoded > _MAX_METADATA_BYTES:
        return {"truncated": True, "original_size_bytes": encoded}
    return cleaned


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    actor_username: Mapped[str | None] = mapped_column(String(39))
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    target_type: Mapped[str | None] = mapped_column(String(64))
    target_id: Mapped[str | None] = mapped_column(String(64))
    log_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=now_utc, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_audit_logs_action", "action"),
        Index("ix_audit_logs_actor_id", "actor_id"),
        Index("ix_audit_logs_target", "target_type", "target_id"),
        Index("ix_audit_logs_created_at", "created_at"),
    )
