"""Badge schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import BadgeRuleType

BADGE_SLUG_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"


class BadgeRule(BaseModel):
    """Machine-readable award rule. Evaluated server-side only."""

    model_config = ConfigDict(extra="forbid")

    type: BadgeRuleType
    count: int = Field(default=1, ge=1, le=100)
    track: str | None = Field(default=None, min_length=2, max_length=64)


class BadgeCriteria(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str = Field(min_length=3, max_length=300)
    rule: BadgeRule


class BadgePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    name: str
    description: str
    icon: str
    criteria: dict[str, Any]


class UserBadgeEntry(BaseModel):
    badge: BadgePublic
    awarded_at: datetime


class BadgeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slug: str = Field(min_length=3, max_length=64, pattern=BADGE_SLUG_PATTERN)
    name: str = Field(min_length=3, max_length=120)
    description: str = Field(min_length=3, max_length=1000)
    icon: str = Field(min_length=2, max_length=64)
    criteria: BadgeCriteria
    is_active: bool = True


class BadgeUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=3, max_length=120)
    description: str | None = Field(default=None, min_length=3, max_length=1000)
    icon: str | None = Field(default=None, min_length=2, max_length=64)
    criteria: BadgeCriteria | None = None
    is_active: bool | None = None


class BadgeGrant(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str | None = Field(default=None, max_length=300)

    @field_validator("reason")
    @classmethod
    def _clean(cls, value: str | None) -> str | None:
        return value.strip() if value else None

    @model_validator(mode="after")
    def _noop(self) -> BadgeGrant:
        return self
