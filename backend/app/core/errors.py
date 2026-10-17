"""Application error types and machine-readable error envelope helpers."""

from __future__ import annotations

from typing import Any


class ApiError(Exception):
    """Base class for controlled, client-safe API errors.

    Errors are rendered as ``{"error": {"code", "message", "details"}}`` so API
    consumers can branch on a stable machine-readable ``code``.
    """

    status_code: int = 400
    code: str = "bad_request"

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        status_code: int | None = None,
        details: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code
        self.details = details


class ValidationFailed(ApiError):
    status_code = 422
    code = "validation_error"


class NotAuthenticated(ApiError):
    status_code = 401
    code = "not_authenticated"


class Forbidden(ApiError):
    status_code = 403
    code = "forbidden"


class NotFound(ApiError):
    status_code = 404
    code = "not_found"


class Conflict(ApiError):
    status_code = 409
    code = "conflict"


class RateLimited(ApiError):
    status_code = 429
    code = "rate_limited"


class NotReady(ApiError):
    status_code = 503
    code = "not_ready"


class ExternalServiceError(ApiError):
    status_code = 502
    code = "external_service_error"


def error_payload(
    code: str,
    message: str,
    details: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"error": {"code": code, "message": message}}
    if details:
        payload["error"]["details"] = details
    return payload
