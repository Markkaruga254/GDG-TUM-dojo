"""Authentication endpoints: GitHub OAuth login, callback, session info, logout."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse

from app.core.dependencies import (
    CurrentContextDep,
    DbDep,
    GitHubClientDep,
    SettingsDep,
    rate_limit_dependency,
)
from app.core.errors import ApiError, NotAuthenticated, ValidationFailed
from app.core.logging import get_logger
from app.core.security import constant_time_equals
from app.schemas.auth import LoginResponse, LogoutResponse
from app.schemas.common import ErrorResponse
from app.schemas.user import UserSelf
from app.services.auth import AuthService, require_oauth_configured, revoke_session

logger = get_logger(__name__)

router = APIRouter()

auth_rate_limit = rate_limit_dependency(
    "auth",
    lambda settings: (settings.auth_rate_limit_per_minute, 60),
)

JSON_ACCEPT = "application/json"


def _wants_json(request: Request) -> bool:
    return JSON_ACCEPT in request.headers.get("accept", "").lower()


def _set_state_cookies(
    response: Response,
    *,
    settings,  # type: ignore[no-untyped-def]
    state: str,
    code_verifier: str,
) -> None:
    common = {
        "httponly": True,
        "secure": settings.cookie_secure,
        "samesite": "lax",
        "max_age": settings.oauth_state_ttl_seconds,
        "path": "/",
        "domain": settings.cookie_domain_value,
    }
    response.set_cookie(settings.oauth_state_cookie_name, state, **common)
    response.set_cookie(settings.oauth_verifier_cookie_name, code_verifier, **common)


def _clear_flow_cookies(response: Response, settings) -> None:  # type: ignore[no-untyped-def]
    for name in (settings.oauth_state_cookie_name, settings.oauth_verifier_cookie_name):
        response.delete_cookie(name, path="/", domain=settings.cookie_domain_value)


def _auth_error_redirect(settings, code: str) -> RedirectResponse:  # type: ignore[no-untyped-def]
    separator = "&" if "?" in settings.frontend_auth_redirect_url else "?"
    response = RedirectResponse(
        f"{settings.frontend_auth_redirect_url}{separator}status=error&code={code}",
        status_code=302,
    )
    _clear_flow_cookies(response, settings)
    return response


@router.get(
    "/github/login",
    response_model=LoginResponse,
    responses={
        302: {"description": "Redirect to GitHub"},
        503: {"model": ErrorResponse, "description": "OAuth not configured"},
    },
    dependencies=[Depends(auth_rate_limit)],
    summary="Start the GitHub OAuth flow",
)
def github_login(request: Request, db: DbDep, settings: SettingsDep, client: GitHubClientDep):  # type: ignore[no-untyped-def]
    service = AuthService(db, settings, client)
    start = service.start_login()

    if _wants_json(request):
        response: Response = JSONResponse(
            LoginResponse(
                authorization_url=start.authorization_url, expires_in=start.expires_in
            ).model_dump()
        )
    else:
        response = RedirectResponse(start.authorization_url, status_code=302)
    _set_state_cookies(
        response, settings=settings, state=start.state, code_verifier=start.code_verifier
    )
    return response


@router.get(
    "/github/callback",
    response_model=UserSelf,
    responses={
        302: {"description": "Redirect back to the frontend"},
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        503: {"model": ErrorResponse, "description": "OAuth not configured"},
    },
    dependencies=[Depends(auth_rate_limit)],
    summary="Complete the GitHub OAuth flow",
)
def github_callback(  # type: ignore[no-untyped-def]
    request: Request,
    db: DbDep,
    settings: SettingsDep,
    client: GitHubClientDep,
    code: str | None = Query(default=None, max_length=200),
    state: str | None = Query(default=None, max_length=200),
    error: str | None = Query(default=None, max_length=100),
):
    wants_json = _wants_json(request)

    def failure(exc: ApiError):  # type: ignore[no-untyped-def]
        if wants_json:
            raise exc
        return _auth_error_redirect(settings, exc.code)

    try:
        require_oauth_configured(settings)
    except ApiError as exc:
        return failure(exc)

    if error:
        return failure(
            ValidationFailed("GitHub sign-in was cancelled.", code="oauth_denied", status_code=400)
        )
    if not code:
        return failure(
            ValidationFailed(
                "Missing authorization code.", code="oauth_missing_code", status_code=400
            )
        )

    expected_state = request.cookies.get(settings.oauth_state_cookie_name)
    if not expected_state or not constant_time_equals(expected_state, state):
        return failure(
            NotAuthenticated("Invalid or expired OAuth state. Please start the sign-in again.")
        )
    code_verifier = request.cookies.get(settings.oauth_verifier_cookie_name)
    if not code_verifier:
        return failure(NotAuthenticated("Missing OAuth verifier. Please start the sign-in again."))

    service = AuthService(db, settings, client)
    result = service.complete_login(
        code=code, code_verifier=code_verifier, user_agent=request.headers.get("user-agent")
    )
    db.commit()

    if wants_json:
        response: Response = JSONResponse(
            UserSelf.model_validate(result.user).model_dump(mode="json")
        )
    else:
        separator = "&" if "?" in settings.frontend_auth_redirect_url else "?"
        response = RedirectResponse(
            f"{settings.frontend_auth_redirect_url}{separator}status=ok", status_code=302
        )

    _clear_flow_cookies(response, settings)
    _set_session_cookies(
        response,
        settings=settings,
        session_token=result.session_token,
        csrf_token=result.csrf_token,
    )
    return response


@router.get("/me", response_model=UserSelf, summary="Current authenticated user")
def me(context: CurrentContextDep) -> UserSelf:
    return UserSelf.model_validate(context.user)


@router.post(
    "/logout",
    response_model=LogoutResponse,
    responses={401: {"model": ErrorResponse}},
    summary="Revoke the current session",
)
def logout(
    request: Request,
    response: Response,
    context: CurrentContextDep,
    db: DbDep,
    settings: SettingsDep,
) -> LogoutResponse:
    if context.session_token:
        revoke_session(db, context.session_token)
    db.commit()
    response.delete_cookie(
        settings.session_cookie_name, path="/", domain=settings.cookie_domain_value
    )
    response.delete_cookie(settings.csrf_cookie_name, path="/", domain=settings.cookie_domain_value)
    return LogoutResponse()


def _set_session_cookies(
    response: Response,
    *,
    settings,  # type: ignore[no-untyped-def]
    session_token: str,
    csrf_token: str,
) -> None:
    max_age = settings.session_ttl_hours * 3600
    response.set_cookie(
        settings.session_cookie_name,
        session_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=max_age,
        path="/",
        domain=settings.cookie_domain_value,
    )
    # CSRF cookie is intentionally readable by the frontend (double-submit pattern).
    response.set_cookie(
        settings.csrf_cookie_name,
        csrf_token,
        httponly=False,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=max_age,
        path="/",
        domain=settings.cookie_domain_value,
    )
