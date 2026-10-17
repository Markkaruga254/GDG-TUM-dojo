"""Authentication schemas."""

from __future__ import annotations

from pydantic import BaseModel


class LoginResponse(BaseModel):
    """Returned when ``/auth/github/login`` is called with ``Accept: application/json``."""

    authorization_url: str
    expires_in: int


class LogoutResponse(BaseModel):
    status: str = "ok"
