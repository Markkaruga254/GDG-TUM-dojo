"""Request middleware: request IDs, security headers, CORS and CSRF checks."""

from __future__ import annotations

import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.core.config import Settings
from app.core.errors import error_payload
from app.core.logging import get_logger
from app.core.security import constant_time_equals

logger = get_logger(__name__)

MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
CSRF_HEADER = "x-csrf-token"
UNSAFE_DEFAULT_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
}


def register_middlewares(app: FastAPI, settings: Settings) -> None:
    """Register middleware in the correct execution order."""

    if settings.allowed_hosts:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.frontend_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-CSRF-Token", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
        max_age=600,
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next):  # type: ignore[no-untyped-def]
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        request.state.request_id = request_id
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            logger.exception(
                "unhandled request error",
                extra={
                    "context": {
                        "request_id": request_id,
                        "method": request.method,
                        "path": request.url.path,
                        "duration_ms": duration_ms,
                    }
                },
            )
            raise
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        for header, value in UNSAFE_DEFAULT_HEADERS.items():
            response.headers.setdefault(header, value)
        if request.url.path.startswith(f"{settings.api_v1_prefix}/auth"):
            response.headers.setdefault("Cache-Control", "no-store")
        logger.info(
            "request handled",
            extra={
                "context": {
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": duration_ms,
                }
            },
        )
        return response

    @app.middleware("http")
    async def enforce_csrf(request: Request, call_next):  # type: ignore[no-untyped-def]
        """Double-submit CSRF token + origin validation for cookie-authenticated writes."""
        if request.method not in MUTATING_METHODS:
            return await call_next(request)
        if not request.url.path.startswith(settings.api_v1_prefix):
            return await call_next(request)
        if request.headers.get("authorization"):
            # Bearer-token clients are not cookie-authenticated: no CSRF surface.
            return await call_next(request)

        session_cookie = request.cookies.get(settings.session_cookie_name)
        if not session_cookie:
            return await call_next(request)

        origin = request.headers.get("origin")
        if origin and origin.rstrip("/") not in settings.frontend_origins:
            return _csrf_failure("origin_not_allowed", "Request origin is not allowed.")

        cookie_token = request.cookies.get(settings.csrf_cookie_name)
        header_token = request.headers.get(CSRF_HEADER)
        if not constant_time_equals(cookie_token, header_token):
            return _csrf_failure("csrf_failed", "Missing or invalid CSRF token.")

        return await call_next(request)


def _csrf_failure(code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=403,
        content=error_payload(code, message),
    )
