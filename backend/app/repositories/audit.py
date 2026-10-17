"""Audit-log and session data access."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.security import now_utc
from app.models import AuditLog, AuthSession


class AuditRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def record(
        self,
        *,
        action: str,
        actor_id: uuid.UUID | None,
        actor_username: str | None,
        target_type: str | None = None,
        target_id: str | None = None,
        metadata: dict | None = None,
    ) -> AuditLog:
        from app.models import sanitize_audit_metadata

        entry = AuditLog(
            action=action,
            actor_id=actor_id,
            actor_username=actor_username,
            target_type=target_type,
            target_id=target_id,
            log_metadata=sanitize_audit_metadata(metadata),
        )
        self.session.add(entry)
        return entry

    def list_logs(
        self,
        *,
        action: str | None = None,
        actor_id: uuid.UUID | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[AuditLog], int]:
        query = select(AuditLog)
        if action:
            query = query.where(AuditLog.action == action)
        if actor_id:
            query = query.where(AuditLog.actor_id == actor_id)
        total = int(
            self.session.execute(select(func.count()).select_from(query.subquery())).scalar_one()
        )
        rows = (
            self.session.execute(
                query.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
                .limit(limit)
                .offset(offset)
            )
            .scalars()
            .all()
        )
        return list(rows), total


class SessionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        *,
        user_id: uuid.UUID,
        token_hash: str,
        expires_at: datetime,
        user_agent: str | None = None,
    ) -> AuthSession:
        auth_session = AuthSession(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            user_agent=(user_agent or "")[:256] or None,
        )
        self.session.add(auth_session)
        return auth_session

    def get_valid_by_token_hash(self, token_hash: str) -> AuthSession | None:
        return self.session.execute(
            select(AuthSession).where(
                AuthSession.token_hash == token_hash,
                AuthSession.revoked_at.is_(None),
                AuthSession.expires_at > now_utc(),
            )
        ).scalar_one_or_none()

    def revoke(self, auth_session: AuthSession) -> None:
        auth_session.revoked_at = now_utc()

    def revoke_all_for_user(self, user_id: uuid.UUID) -> int:
        result = self.session.execute(
            update(AuthSession)
            .where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
            .values(revoked_at=now_utc())
        )
        return int(result.rowcount or 0)
