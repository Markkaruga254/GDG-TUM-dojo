"""Shared SQLAlchemy column helpers."""

from __future__ import annotations

from enum import Enum as PyEnum

from sqlalchemy import Enum


def enum_column(enum_cls: type[PyEnum], name: str) -> Enum:
    """Store Python enums as VARCHAR with Python-side validation.

    ``native_enum=False`` keeps migrations simple (no ``ALTER TYPE`` pain).
    ``create_constraint=False`` avoids Alembic emitting the enum CHECK twice;
    allowed values are enforced with an explicit :func:`enum_check` constraint.
    """
    return Enum(
        enum_cls,
        name=name,
        native_enum=False,
        length=32,
        validate_strings=True,
        create_constraint=False,
        values_callable=lambda cls: [member.value for member in cls],
    )


def enum_check(column: str, enum_cls: type[PyEnum]) -> str:
    """SQL snippet for an explicit CHECK constraint listing enum values."""
    values = ", ".join(f"'{member.value}'" for member in enum_cls)
    return f"{column} IN ({values})"
