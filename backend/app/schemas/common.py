"""Shared response schemas: pagination and error envelopes."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Page[T](BaseModel):
    """Standard pagination envelope used by every list endpoint."""

    items: list[T]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    pages: int = Field(ge=0)

    @classmethod
    def build(cls, items: list[T], total: int, page: int, page_size: int) -> Page[T]:
        pages = (total + page_size - 1) // page_size if page_size else 0
        return cls(items=items, total=total, page=page, page_size=page_size, pages=pages)


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: list[dict[str, Any]] | None = None


class ErrorResponse(BaseModel):
    """Machine-readable error envelope returned by all error responses."""

    error: ErrorDetail


class StatusResponse(BaseModel):
    status: str


class MessageResponse(BaseModel):
    message: str
