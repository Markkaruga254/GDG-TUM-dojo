"""API v1 router assembly."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import (
    admin,
    auth,
    badges,
    challenges,
    health,
    leaderboard,
    submissions,
    users,
)

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(challenges.router, prefix="/challenges", tags=["challenges"])
api_router.include_router(submissions.router, tags=["submissions"])
api_router.include_router(leaderboard.router, prefix="/leaderboard", tags=["leaderboard"])
api_router.include_router(badges.router, tags=["badges"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])

__all__ = ["api_router"]
