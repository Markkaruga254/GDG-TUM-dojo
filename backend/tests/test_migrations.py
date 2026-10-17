"""Migration tests: run Alembic against a disposable database.

These tests need a *second* disposable PostgreSQL database so they never touch
the schema managed by ``Base.metadata.create_all`` for the rest of the suite:

    createdb buildarena_mig
    export TEST_MIGRATION_DATABASE_URL=postgresql+psycopg://user:pass@host:port/buildarena_mig

When ``TEST_MIGRATION_DATABASE_URL`` is not set, the entire module is skipped.
"""

from __future__ import annotations

import argparse
import contextlib
import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect

from app.db.base import Base

BACKEND_DIR = Path(__file__).resolve().parents[1]

EXPECTED_TABLES = {
    "users",
    "auth_sessions",
    "challenges",
    "submissions",
    "evaluations",
    "badges",
    "user_badges",
    "audit_logs",
}

pytestmark = pytest.mark.postgres


def _alembic_config(database_url: str) -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    # ``x`` mirrors ``alembic -x db_url=...``; migrations/env.py prefers it over DATABASE_URL.
    config.cmd_opts = argparse.Namespace(x=[f"db_url={database_url}"])
    return config


def _downgrade_best_effort(config: Config) -> None:
    # The disposable database may be in any state (e.g. after a previous failed run).
    with contextlib.suppress(Exception):
        command.downgrade(config, "base")


@pytest.fixture
def migrated_database() -> Iterator[tuple[Config, str]]:
    database_url = os.environ.get("TEST_MIGRATION_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_MIGRATION_DATABASE_URL is not set")

    config = _alembic_config(database_url)
    _downgrade_best_effort(config)
    command.upgrade(config, "head")
    try:
        yield config, database_url
    finally:
        _downgrade_best_effort(config)


def _table_names(database_url: str) -> set[str]:
    engine = create_engine(database_url)
    try:
        return set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def test_upgrade_head_creates_all_application_tables(migrated_database) -> None:
    _, database_url = migrated_database
    tables = _table_names(database_url)

    assert tables >= EXPECTED_TABLES
    assert "alembic_version" in tables


def test_migrated_schema_matches_models(migrated_database) -> None:
    """The migrated schema and ``Base.metadata`` must be identical.

    This is the automated equivalent of ``alembic check``: any model change that
    is missing from a migration (or any drift in the migration) fails the suite.
    """
    _config, database_url = migrated_database
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            context = MigrationContext.configure(
                connection,
                opts={"compare_type": True, "compare_server_default": True},
            )
            diff = compare_metadata(context, Base.metadata)
    finally:
        engine.dispose()

    assert diff == [], f"schema drift detected between migrations and models: {diff}"


def test_downgrade_base_removes_application_tables(migrated_database) -> None:
    config, database_url = migrated_database
    command.downgrade(config, "base")

    remaining = _table_names(database_url)
    assert remaining & EXPECTED_TABLES == set()
    assert remaining <= {"alembic_version"}
