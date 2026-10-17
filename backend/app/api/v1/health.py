"""Health and readiness endpoints.

These endpoints are deliberately information-free: no version strings of
dependencies, no connection strings, no error details.
"""

from __future__ import annotations

from fastapi import APIRouter, Response
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.dependencies import DbDep, SettingsDep
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    application: str


class ReadinessResponse(BaseModel):
    status: str
    checks: dict[str, str]


@router.get("/health", response_model=HealthResponse, summary="Liveness probe")
def health(settings: SettingsDep) -> HealthResponse:
    return HealthResponse(status="ok", application=settings.app_name)


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    responses={503: {"model": ReadinessResponse, "description": "A dependency is not ready"}},
    summary="Readiness probe",
)
def ready(response: Response, db: DbDep) -> ReadinessResponse:
    checks: dict[str, str] = {}
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except SQLAlchemyError:
        logger.warning("readiness probe: database unavailable")
        checks["database"] = "error"
    if any(value != "ok" for value in checks.values()):
        response.status_code = 503
        return ReadinessResponse(status="not_ready", checks=checks)
    return ReadinessResponse(status="ready", checks=checks)
