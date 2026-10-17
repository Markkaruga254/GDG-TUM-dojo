"""Seed the default badge catalogue (idempotent).

Usage:
    python -m scripts.seed_badges
"""

from __future__ import annotations

from app.db.session import get_session_factory
from app.services.badges import BadgeService


def main() -> int:
    session = get_session_factory()()
    try:
        created = BadgeService(session).seed_defaults()
        session.commit()
        print(f"Badge seeding complete. New badges created: {created}")
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
