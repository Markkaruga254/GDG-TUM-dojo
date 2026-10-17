"""Promote a GitHub user to admin (explicit, audited, no authentication bypass).

Usage:
    python -m scripts.promote_admin <github_username>

The user must have signed in at least once so their account exists.
"""

from __future__ import annotations

import argparse
import sys

from app.db.session import get_session_factory
from app.models import UserRole
from app.repositories.audit import AuditRepository
from app.repositories.users import UserRepository
from app.services.audit import AuditAction


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Promote a user to admin.")
    parser.add_argument("username", help="GitHub username of the account to promote")
    args = parser.parse_args(argv)

    session = get_session_factory()()
    try:
        repository = UserRepository(session)
        user = repository.get_by_username(args.username)
        if user is None:
            print(
                f"No account found for GitHub username {args.username!r}. "
                "The user must sign in with GitHub first.",
                file=sys.stderr,
            )
            return 1
        previous = user.role
        user.role = UserRole.ADMIN
        AuditRepository(session).record(
            action=AuditAction.USER_ROLE_CHANGE,
            actor_id=None,
            actor_username="cli:promote_admin",
            target_type="user",
            target_id=str(user.id),
            metadata={
                "previous_role": previous.value,
                "new_role": UserRole.ADMIN.value,
                "username": user.github_username,
                "source": "cli",
            },
        )
        session.commit()
        print(f"Promoted {user.github_username} from {previous.value} to admin.")
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
