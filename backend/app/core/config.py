"""Central application configuration (Pydantic v2 settings)."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from app.core.version import APP_VERSION, EVALUATOR_VERSION

Environment = Literal["development", "test", "production"]


class Settings(BaseSettings):
    """Runtime configuration sourced from environment variables and `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Core -----------------------------------------------------------------
    app_name: str = "GDG TUM Build Arena API"
    app_version: str = APP_VERSION
    environment: Environment = "development"
    debug: bool = False
    docs_enabled: bool | None = None
    log_level: str = "INFO"
    log_json: bool = True
    api_v1_prefix: str = "/api/v1"

    # --- HTTP / CORS -----------------------------------------------------------
    backend_base_url: str = "http://localhost:8000"
    frontend_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173"]
    allowed_hosts: Annotated[list[str], NoDecode] = []
    trust_proxy_headers: bool = False

    # --- Database --------------------------------------------------------------
    database_url: str = "postgresql+psycopg://buildarena:buildarena@localhost:5432/buildarena"
    db_pool_size: int = Field(default=5, ge=1, le=50)
    db_max_overflow: int = Field(default=10, ge=0, le=100)
    db_pool_recycle_seconds: int = Field(default=1800, ge=-1)

    # --- GitHub OAuth / API ----------------------------------------------------
    github_client_id: str = ""
    github_client_secret: SecretStr = SecretStr("")
    github_oauth_scopes: str = "read:user"
    github_api_token: SecretStr = SecretStr("")
    github_api_base_url: str = "https://api.github.com"
    github_oauth_authorize_url: str = "https://github.com/login/oauth/authorize"
    github_oauth_token_url: str = "https://github.com/login/oauth/access_token"
    github_api_timeout_seconds: float = Field(default=10.0, gt=0, le=60)
    frontend_auth_redirect_url: str = "http://localhost:5173/auth/callback"
    admin_github_usernames: Annotated[list[str], NoDecode] = []

    # --- Sessions / cookies -----------------------------------------------------
    session_ttl_hours: int = Field(default=168, ge=1, le=24 * 90)
    session_cookie_name: str = "ba_session"
    csrf_cookie_name: str = "ba_csrf"
    oauth_state_cookie_name: str = "ba_oauth_state"
    oauth_verifier_cookie_name: str = "ba_oauth_verifier"
    session_cookie_secure: bool | None = None
    cookie_domain: str = ""
    oauth_state_ttl_seconds: int = Field(default=600, ge=60, le=3600)

    # --- Limits -----------------------------------------------------------------
    rate_limit_enabled: bool | None = None
    auth_rate_limit_per_minute: int = Field(default=30, ge=1)
    submission_rate_limit_per_hour: int = Field(default=30, ge=1)
    evaluation_rate_limit_per_hour: int = Field(default=60, ge=1)
    default_rate_limit_per_minute: int = Field(default=240, ge=1)
    submission_cooldown_seconds: int = Field(default=30, ge=0, le=3600)
    max_submissions_per_challenge_per_day: int = Field(default=10, ge=1, le=500)
    max_evidence_urls: int = Field(default=5, ge=0, le=20)
    max_notes_length: int = Field(default=4000, ge=0, le=20000)
    max_repo_url_length: int = Field(default=300, ge=64, le=1000)
    default_page_size: int = Field(default=20, ge=1, le=100)
    max_page_size: int = Field(default=100, ge=1, le=500)

    # --- Evaluation ---------------------------------------------------------------
    evaluator_version: str = EVALUATOR_VERSION

    # --- Validators ----------------------------------------------------------------
    @field_validator("frontend_origins", "allowed_hosts", "admin_github_usernames", mode="before")
    @classmethod
    def _split_comma_separated(cls, value: object) -> object:
        if value is None:
            return []
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("frontend_origins")
    @classmethod
    def _normalize_origins(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        for origin in value:
            candidate = origin.strip().rstrip("/")
            if not candidate:
                continue
            if candidate != "*" and not candidate.startswith(("http://", "https://")):
                raise ValueError(
                    f"invalid CORS origin {origin!r}: must start with http:// or https://"
                )
            normalized.append(candidate)
        return normalized

    @field_validator("backend_base_url", "frontend_auth_redirect_url", "github_api_base_url")
    @classmethod
    def _strip_trailing_slash(cls, value: str) -> str:
        return value.strip().rstrip("/")

    @model_validator(mode="after")
    def _apply_environment_defaults(self) -> Settings:
        if self.docs_enabled is None:
            self.docs_enabled = self.environment != "production"
        if self.rate_limit_enabled is None:
            self.rate_limit_enabled = self.environment != "test"
        if self.session_cookie_secure is None:
            self.session_cookie_secure = self.environment == "production"

        if self.environment == "production":
            problems: list[str] = []
            if not self.github_oauth_configured:
                problems.append(
                    "GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET must be set in production"
                )
            if "*" in self.frontend_origins:
                problems.append("wildcard CORS origins are not allowed in production")
            if "*" in self.allowed_hosts:
                problems.append("wildcard ALLOWED_HOSTS is not allowed in production")
            if not self.session_cookie_secure:
                problems.append("SESSION_COOKIE_SECURE must not be disabled in production")
            if self.debug:
                problems.append("DEBUG must be disabled in production")
            if problems:
                raise ValueError("invalid production configuration: " + "; ".join(problems))
        return self

    # --- Derived properties -----------------------------------------------------------
    @property
    def github_oauth_configured(self) -> bool:
        return bool(
            self.github_client_id.strip() and self.github_client_secret.get_secret_value().strip()
        )

    @property
    def github_api_token_value(self) -> str:
        return self.github_api_token.get_secret_value().strip()

    @property
    def github_redirect_uri(self) -> str:
        return f"{self.backend_base_url}{self.api_v1_prefix}/auth/github/callback"

    @property
    def cookie_secure(self) -> bool:
        return bool(self.session_cookie_secure)

    @property
    def cookie_domain_value(self) -> str | None:
        return self.cookie_domain.strip() or None

    @property
    def rate_limits_enabled(self) -> bool:
        return bool(self.rate_limit_enabled)

    @property
    def admin_usernames_normalized(self) -> set[str]:
        return {name.strip().lower() for name in self.admin_github_usernames if name.strip()}


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings singleton (cached)."""
    return Settings()
