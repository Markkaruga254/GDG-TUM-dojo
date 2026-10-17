"""Audit-log schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AuditLogPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    action: str
    actor_id: uuid.UUID | None = None
    actor_username: str | None = None
    target_type: str | None = None
    target_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict, validation_alias="log_metadata")
    created_at: datetime
