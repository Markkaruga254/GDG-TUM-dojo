"""Seed the disposable end-to-end database used by the Playwright suite.

Creates deterministic data for ``e2e/`` (see ``e2e/README.md``):

- two staff accounts (admin + moderator) and two students;
- ``cloud-notes-platform`` — a published challenge whose checks all pass
  against the canned repository served by ``e2e/scripts/mock-github.mjs``;
- ``lab-telemetry-pipeline`` — a draft challenge that must stay invisible;
- one pre-evaluated submission (100/100) used by the moderation tests.

Session tokens for the Playwright suite are written to the file named by
``E2E_SESSIONS_FILE`` (default ``e2e/.sessions.json``) and never printed.

The database must already exist or be creatable; ``e2e/scripts/prepare.mjs``
creates it, applies migrations and then runs this script. The database name is
required to end with ``_e2e`` so the destructive seed can never touch the
development or test databases.

Usage:
    cd backend
    DATABASE_URL='postgresql+psycopg://buildarena:buildarena@127.0.0.1:5433/buildarena_e2e' \
        python -m scripts.seed_e2e
"""

from __future__ import annotations

import json
import os
import re
import sys
import uuid
from datetime import timedelta
from pathlib import Path

import psycopg
from psycopg import sql
from sqlalchemy import text
from sqlalchemy.engine import URL, make_url

from app.core.security import generate_token, hash_token, now_utc
from app.core.version import EVALUATOR_VERSION
from app.db.session import get_session_factory
from app.models import AuthSession, User
from app.models.enums import EvaluationStatus, SubmissionStatus, UserRole
from app.models.submission import Evaluation, Submission
from app.schemas.challenge import ChallengeCreate
from app.services.badges import BadgeService
from app.services.challenges import ChallengeService

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SESSIONS_PATH = REPO_ROOT / "e2e" / ".sessions.json"
DATABASE_NAME_PATTERN = re.compile(r"^[a-z0-9_]{1,60}$")

MOCK_REPO_URL = "https://github.com/e2e-labs/cloud-notes"

PASS_MESSAGES = {
    "repo_accessible": "Repository is accessible.",
    "repo_public": "Repository is public.",
    "readme_present": "README found.",
    "readme_sections": "All required sections documented.",
    "readme_min_length": "README is long enough.",
    "required_files": "All required paths exist.",
    "required_directories": "All required directories exist.",
    "min_commits": "At least the minimum number of commits found.",
    "license_present": "A license file is present.",
    "language_present": "Required languages detected.",
    "evidence_links": "Evidence link(s) provided.",
}


# --------------------------------------------------------------------------- #
# database preparation
# --------------------------------------------------------------------------- #


def database_url_from_env() -> str:
    """Return DATABASE_URL or fail loudly — there is no safe default."""
    value = os.environ.get("DATABASE_URL", "").strip()
    if not value:
        raise SystemExit(
            "DATABASE_URL is not set. Point it at a disposable database whose name ends "
            "with '_e2e', e.g. "
            "postgresql+psycopg://buildarena:buildarena@127.0.0.1:5433/buildarena_e2e"
        )
    return value


def ensure_database(url: URL) -> None:
    """Create the E2E database when it is missing; never touch other databases."""
    name = url.database or ""
    if not DATABASE_NAME_PATTERN.match(name) or not name.endswith("_e2e"):
        raise SystemExit(
            f"refusing to use database {name!r}: the E2E database name must be "
            "lowercase and end with '_e2e'"
        )

    conninfo = {
        "host": url.host or "127.0.0.1",
        "port": url.port or 5432,
        "user": url.username or "",
        "password": url.password or "",
        "dbname": "postgres",
        "connect_timeout": 5,
    }
    try:
        with psycopg.connect(**conninfo, autocommit=True) as connection:
            exists = connection.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s", (name,)
            ).fetchone()
            if exists:
                return
            connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    except psycopg.OperationalError as exc:
        raise SystemExit(
            f"could not prepare database {name!r}: {exc}\n"
            "Is PostgreSQL running? Can the configured role create databases?"
        ) from exc
    print(f"created database {name}")


# --------------------------------------------------------------------------- #
# seeding
# --------------------------------------------------------------------------- #


def seed_user(
    db,
    *,
    github_id: int,
    username: str,
    display_name: str,
    role: UserRole = UserRole.STUDENT,
) -> User:
    user = User(
        github_id=github_id,
        github_username=username,
        display_name=display_name,
        avatar_url=None,
        role=role,
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


def challenge_checks(challenge) -> list[dict]:
    """Mirror the runner's check payloads with everything passing."""
    configured = [
        item for item in challenge.evaluation_config.get("checks", []) if item.get("enabled", True)
    ]
    return [
        {
            "id": item["id"],
            "type": item["type"],
            "description": item["description"],
            "status": "passed",
            "max_points": int(item["points"]),
            "awarded_points": int(item["points"]),
            "message": PASS_MESSAGES.get(item["type"], "Check passed."),
            "required": bool(item.get("required", True)),
            "evidence": {},
        }
        for item in configured
    ]


def add_evaluated_submission(
    db,
    *,
    user: User,
    challenge,
    repo_url: str,
    evidence: list[str],
    notes: str,
    days_ago: float = 2.0,
) -> Submission:
    checks = challenge_checks(challenge)
    awarded = sum(check["awarded_points"] for check in checks)
    max_score = sum(check["max_points"] for check in checks)
    submitted_at = now_utc() - timedelta(days=days_ago)
    submission = Submission(
        id=uuid.uuid4(),
        user_id=user.id,
        challenge_id=challenge.id,
        repo_url=repo_url,
        repo_full_name=repo_url.removeprefix("https://github.com/"),
        notes=notes,
        evidence_urls=evidence,
        status=SubmissionStatus.PASSED,
        points_awarded=awarded,
        evaluation_summary=f"Passed — {awarded}/{max_score} points.",
        evaluation_attempts=1,
        submitted_at=submitted_at,
        evaluated_at=submitted_at + timedelta(minutes=2),
    )
    db.add(submission)
    db.flush()
    db.add(
        Evaluation(
            id=uuid.uuid4(),
            submission_id=submission.id,
            status=EvaluationStatus.COMPLETED,
            checks=checks,
            max_score=max_score,
            awarded_score=awarded,
            feedback="Automated evaluation finished.",
            evaluator_version=EVALUATOR_VERSION,
            started_at=submitted_at + timedelta(minutes=1),
            completed_at=submitted_at + timedelta(minutes=2),
            created_at=submitted_at + timedelta(minutes=1),
        )
    )
    return submission


def mint_session(db, user: User) -> dict[str, str]:
    raw = generate_token(32)
    csrf = generate_token(24)
    db.add(
        AuthSession(
            id=uuid.uuid4(),
            user_id=user.id,
            token_hash=hash_token(raw),
            user_agent="playwright-e2e",
            expires_at=now_utc() + timedelta(days=7),
        )
    )
    return {"username": user.github_username, "session": raw, "csrf": csrf}


def seed() -> int:
    session = get_session_factory()()
    try:
        # The E2E database is disposable by contract; wipe everything first.
        session.execute(
            text(
                "TRUNCATE TABLE user_badges, evaluations, submissions, challenges, "
                "audit_logs, auth_sessions, users, badges RESTART IDENTITY CASCADE"
            )
        )

        badges_created = BadgeService(session).seed_defaults()

        admin = seed_user(
            session,
            github_id=940001,
            username="e2e-admin",
            display_name="E2E Admin",
            role=UserRole.ADMIN,
        )
        moderator = seed_user(
            session,
            github_id=940002,
            username="e2e-mod",
            display_name="E2E Moderator",
            role=UserRole.MODERATOR,
        )
        aisha = seed_user(
            session,
            github_id=940003,
            username="e2e-aisha",
            display_name="Aisha Khan",
        )
        ben = seed_user(
            session,
            github_id=940004,
            username="e2e-ben",
            display_name="Ben Müller",
        )

        service = ChallengeService(session)
        published = service.create_challenge(
            admin,
            ChallengeCreate(
                title="Cloud Notes Platform",
                slug="cloud-notes-platform",
                description=(
                    "Ship a notes application that syncs across devices. The end-to-end "
                    "suite evaluates it against a deterministic mock repository."
                ),
                instructions=(
                    "Document installation and usage in the README.\n"
                    "Commit incrementally and attach one evidence link."
                ),
                track="web",
                difficulty="intermediate",
                tags=["notes", "sync"],
                max_points=100,
                evaluation_config={
                    "version": 1,
                    "require_public_repo": True,
                    "checks": [
                        {
                            "id": "repo-accessible",
                            "type": "repo_accessible",
                            "description": "Repository is reachable through the GitHub API.",
                            "points": 10,
                        },
                        {
                            "id": "readme-present",
                            "type": "readme_present",
                            "description": "Repository has a README.",
                            "points": 10,
                        },
                        {
                            "id": "readme-sections",
                            "type": "readme_sections",
                            "description": "README documents installation and usage.",
                            "points": 10,
                            "params": {"sections": ["installation", "usage"]},
                        },
                        {
                            "id": "required-files",
                            "type": "required_files",
                            "description": "README.md and package.json exist.",
                            "points": 10,
                            "params": {"paths": ["README.md", "package.json"], "match": "all"},
                        },
                        {
                            "id": "min-commits",
                            "type": "min_commits",
                            "description": "At least five commits.",
                            "points": 20,
                            "params": {"min_count": 5},
                        },
                        {
                            "id": "license-present",
                            "type": "license_present",
                            "description": "Repository declares a license.",
                            "points": 10,
                        },
                        {
                            "id": "language-present",
                            "type": "language_present",
                            "description": "Mostly TypeScript.",
                            "points": 20,
                            "params": {"languages": ["TypeScript"], "min_share": 0.5},
                        },
                        {
                            "id": "evidence-links",
                            "type": "evidence_links",
                            "description": "At least one evidence link.",
                            "points": 10,
                            "params": {"min_count": 1},
                        },
                    ],
                },
            ),
        )
        session.flush()

        draft = service.create_challenge(
            admin,
            ChallengeCreate(
                title="Lab Telemetry Pipeline",
                slug="lab-telemetry-pipeline",
                description=("Draft challenge used to prove drafts stay invisible to students."),
                instructions="Kept as a draft on purpose — the E2E suite asserts that.",
                track="cloud",
                difficulty="advanced",
                tags=["telemetry"],
                max_points=100,
                evaluation_config={
                    "version": 1,
                    "require_public_repo": True,
                    "checks": [
                        {
                            "id": "repo-accessible",
                            "type": "repo_accessible",
                            "description": "Repository is reachable through the GitHub API.",
                            "points": 50,
                        },
                        {
                            "id": "readme-present",
                            "type": "readme_present",
                            "description": "Repository has a README.",
                            "points": 50,
                        },
                    ],
                },
            ),
        )
        session.flush()

        service.publish_challenge(admin, published.id)

        add_evaluated_submission(
            session,
            user=ben,
            challenge=published,
            repo_url=MOCK_REPO_URL,
            evidence=["https://example.com/cloud-notes-demo"],
            notes="Seeded evaluation used by the moderation tests.",
        )

        badge_service = BadgeService(session)
        for user in (aisha, ben):
            badge_service.evaluate_awards(user)

        sessions = {
            "admin": mint_session(session, admin),
            "moderator": mint_session(session, moderator),
            "student": mint_session(session, aisha),
            "student2": mint_session(session, ben),
        }
        sessions_path = Path(os.environ.get("E2E_SESSIONS_FILE", str(DEFAULT_SESSIONS_PATH)))
        sessions_path.parent.mkdir(parents=True, exist_ok=True)
        sessions_path.write_text(json.dumps(sessions, indent=2) + "\n")

        session.commit()

        print(f"badges: {badges_created} catalogue entries seeded")
        print("users: e2e-admin, e2e-mod, e2e-aisha, e2e-ben")
        print(f"challenges: {published.slug} (published), {draft.slug} (draft)")
        print("submissions: 1 evaluated (e2e-ben, 100/100)")
        print(f"sessions written to {sessions_path} (tokens not printed)")
        return 0
    finally:
        session.close()


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    url = make_url(database_url_from_env())
    ensure_database(url)
    if "--ensure-database" in args:
        return 0
    return seed()


if __name__ == "__main__":
    raise SystemExit(main())
