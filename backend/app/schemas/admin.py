"""Administrative schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import UserRole


class RoleUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: UserRole
    reason: str | None = Field(default=None, max_length=300)


class UserStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_active: bool
    reason: str | None = Field(default=None, max_length=300)


class DisqualifyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=5, max_length=500)


class ScoreOverrideRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    points: int = Field(ge=0, le=10_000)
    reason: str = Field(min_length=5, max_length=500)


class AdminUserSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    github_username: str
    display_name: str | None = None
    avatar_url: str | None = None
    role: UserRole
    is_active: bool
    created_at: datetime


class AdminActionResponse(BaseModel):
    status: str = "ok"
    message: str
