"""FastAPI application factory, middleware, and centralized error handling."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.router import api_router
from app.api.v1 import health as health_module
from app.core.config import Settings, get_settings
from app.core.errors import ApiError, error_payload
from app.core.logging import configure_logging, get_logger
from app.core.middleware import register_middlewares
from app.db.session import database_is_ready
from app.evaluation.rules import CHECK_TYPE_DESCRIPTIONS

logger = get_logger(__name__)

DESCRIPTION = """
Backend API for **GDG TUM Build Arena** — a competitive developer learning and
portfolio platform run by Google Developer Groups on Campus at the Technical
University of Mombasa.

* Authentication: GitHub OAuth with HttpOnly cookie sessions (CSRF-protected).
* Scores are always computed server-side; nobody can submit points.
* Automated evaluation inspects repository metadata only — submitted code is
  never executed in the API process.
"""


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level, settings.log_json)

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        if not settings.github_oauth_configured and settings.environment != "test":
            logger.warning(
                "GitHub OAuth is not configured; authentication endpoints will fail "
                "with an actionable configuration error until GITHUB_CLIENT_ID and "
                "GITHUB_CLIENT_SECRET are set."
            )
        if not database_is_ready():
            logger.warning("database is not reachable at startup; readiness will report not_ready")
        logger.info(
            "application started",
            extra={
                "context": {
                    "environment": settings.environment,
                    "version": settings.app_version,
                    "evaluator": settings.evaluator_version,
                }
            },
        )
        yield
        logger.info("application stopped")

    app = FastAPI(
        title=settings.app_name,
        description=DESCRIPTION,
        version=settings.app_version,
        lifespan=lifespan,
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url="/redoc" if settings.docs_enabled else None,
        openapi_url="/openapi.json" if settings.docs_enabled else None,
        openapi_tags=[
            {"name": "health", "description": "Liveness and readiness probes."},
            {"name": "auth", "description": "GitHub OAuth sign-in and session management."},
            {"name": "users", "description": "Profiles and portfolios."},
            {"name": "challenges", "description": "Challenge catalogue and authoring."},
            {"name": "submissions", "description": "Submissions, evaluation and results."},
            {"name": "leaderboard", "description": "Rankings derived from finalized scores."},
            {"name": "badges", "description": "Badge catalogue and user awards."},
            {"name": "admin", "description": "Administrative operations (audited)."},
        ],
    )
    app.state.settings = settings
    app.state.evaluator_check_types = sorted(CHECK_TYPE_DESCRIPTIONS)

    register_middlewares(app, settings)
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    # Root-level probes for platforms (e.g. Render) that expect /health and /ready.
    app.include_router(health_module.router, include_in_schema=False)

    _register_error_handlers(app, settings)
    return app


def _register_error_handlers(app: FastAPI, settings: Settings) -> None:
    @app.exception_handler(ApiError)
    async def handle_api_error(request: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error_payload(exc.code, exc.message, exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # Only field names and messages are exposed — never the submitted values.
        details = [
            {
                "field": ".".join(str(part) for part in error.get("loc", ())),
                "reason": str(error.get("msg", "invalid value")),
            }
            for error in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content=error_payload("validation_error", "Request validation failed.", details),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        codes = {
            400: "bad_request",
            401: "not_authenticated",
            403: "forbidden",
            404: "not_found",
            405: "method_not_allowed",
            409: "conflict",
            413: "payload_too_large",
            415: "unsupported_media_type",
            422: "validation_error",
            429: "rate_limited",
        }
        code = codes.get(exc.status_code, "http_error")
        message = exc.detail if isinstance(exc.detail, str) and exc.detail else "Request failed."
        if exc.status_code >= 500:
            message = "Internal server error."
        return JSONResponse(status_code=exc.status_code, content=error_payload(code, message))

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        logger.exception(
            "unhandled exception",
            extra={"context": {"path": request.url.path, "request_id": request_id}},
        )
        return JSONResponse(
            status_code=500,
            content=error_payload(
                "internal_error", "Internal server error. Please retry or contact the organizers."
            ),
        )


app = create_app()
