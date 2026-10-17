"""Validated, structured evaluation configuration.

Check definitions are declarative data stored on the challenge. Only these
predefined, metadata-only check types can run — student-supplied code is never
executed (see README "Evaluation engine").
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import CheckStatus

MAX_CHECKS_PER_CONFIG = 25
CHECK_ID_PATTERN = r"^[a-z0-9][a-z0-9_-]{2,63}$"


class CheckParams(BaseModel):
    model_config = ConfigDict(extra="forbid")


class NoParams(CheckParams):
    pass


class RequiredPathsParams(CheckParams):
    paths: list[str] = Field(min_length=1, max_length=25)
    match: Literal["all", "any"] = "all"

    @field_validator("paths")
    @classmethod
    def _validate_paths(cls, paths: list[str]) -> list[str]:
        cleaned: list[str] = []
        for path in paths:
            candidate = path.strip()
            if not candidate or len(candidate) > 200:
                raise ValueError("paths must be non-empty and at most 200 characters")
            if candidate.startswith(("/", "\\")) or ".." in candidate.split("/"):
                raise ValueError(f"path must be repository-relative without '..': {path!r}")
            if "\\" in candidate or "\x00" in candidate or " " in candidate:
                raise ValueError(f"path contains unsupported characters: {path!r}")
            cleaned.append(candidate.strip("/"))
        return cleaned


class ReadmeSectionsParams(CheckParams):
    sections: list[str] = Field(min_length=1, max_length=10)

    @field_validator("sections")
    @classmethod
    def _validate_sections(cls, sections: list[str]) -> list[str]:
        cleaned = [section.strip().lower() for section in sections if section.strip()]
        if not cleaned:
            raise ValueError("at least one non-empty section keyword is required")
        if any(len(section) > 60 for section in cleaned):
            raise ValueError("section keywords must be at most 60 characters")
        return cleaned


class ReadmeMinLengthParams(CheckParams):
    min_characters: int = Field(default=300, ge=50, le=20_000)


class EvidenceLinksParams(CheckParams):
    min_count: int = Field(default=1, ge=1, le=20)


class MinCommitsParams(CheckParams):
    min_count: int = Field(default=1, ge=1, le=100)


class LanguagePresentParams(CheckParams):
    languages: list[str] = Field(min_length=1, max_length=5)
    min_share: float = Field(default=0.0, ge=0.0, le=1.0)

    @field_validator("languages")
    @classmethod
    def _validate_languages(cls, languages: list[str]) -> list[str]:
        cleaned = [language.strip() for language in languages if language.strip()]
        if not cleaned:
            raise ValueError("at least one language name is required")
        return cleaned


PARAMS_MODELS: dict[str, type[CheckParams]] = {
    "repo_accessible": NoParams,
    "repo_public": NoParams,
    "required_files": RequiredPathsParams,
    "required_directories": RequiredPathsParams,
    "readme_present": NoParams,
    "readme_sections": ReadmeSectionsParams,
    "readme_min_length": ReadmeMinLengthParams,
    "evidence_links": EvidenceLinksParams,
    "min_commits": MinCommitsParams,
    "license_present": NoParams,
    "language_present": LanguagePresentParams,
}

CheckType = Literal[
    "repo_accessible",
    "repo_public",
    "required_files",
    "required_directories",
    "readme_present",
    "readme_sections",
    "readme_min_length",
    "evidence_links",
    "min_commits",
    "license_present",
    "language_present",
]

CHECK_TYPE_DESCRIPTIONS: dict[str, str] = {
    "repo_accessible": "Repository exists and is reachable through the GitHub API.",
    "repo_public": "Repository is publicly visible.",
    "required_files": "Required files exist in the repository.",
    "required_directories": "Required directories exist in the repository.",
    "readme_present": "Repository has a README.",
    "readme_sections": "README documents the required sections.",
    "readme_min_length": "README has a minimum length.",
    "evidence_links": "Submission includes the required evidence links.",
    "min_commits": "Repository has a minimum number of commits.",
    "license_present": "Repository declares a license.",
    "language_present": "Repository uses the required language(s).",
}


class CheckConfig(BaseModel):
    """One configurable evaluation check."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=CHECK_ID_PATTERN)
    type: CheckType
    description: str = Field(min_length=3, max_length=300)
    points: int = Field(ge=0, le=10_000)
    required: bool = True
    enabled: bool = True
    params: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_params(self) -> CheckConfig:
        params_model = PARAMS_MODELS[self.type]
        validated = params_model.model_validate(self.params)
        self.params = validated.model_dump()
        if not self.description.strip():
            # Reuse PARAMS_MODELS default description guidance for consistency.
            self.description = CHECK_TYPE_DESCRIPTIONS[self.type]
        return self


class EvaluationConfig(BaseModel):
    """Validated evaluation configuration attached to a challenge."""

    model_config = ConfigDict(extra="forbid")

    version: int = Field(default=1, ge=1, le=100)
    require_public_repo: bool = True
    checks: list[CheckConfig] = Field(min_length=1, max_length=MAX_CHECKS_PER_CONFIG)

    @model_validator(mode="after")
    def _validate_checks(self) -> EvaluationConfig:
        ids = [check.id for check in self.checks]
        if len(set(ids)) != len(ids):
            duplicates = sorted({check_id for check_id in ids if ids.count(check_id) > 1})
            raise ValueError(f"duplicate check ids: {', '.join(duplicates)}")
        if not any(check.enabled for check in self.checks):
            raise ValueError("at least one check must be enabled")
        return self

    def enabled_checks(self) -> list[CheckConfig]:
        return [check for check in self.checks if check.enabled]

    def total_points(self) -> int:
        return sum(check.points for check in self.enabled_checks())

    def public_summary(self) -> list[dict[str, Any]]:
        """Student-facing view: reveal weights, withhold internal parameters."""
        return [
            {
                "id": check.id,
                "type": check.type,
                "description": check.description,
                "points": check.points,
                "required": check.required,
                "enabled": check.enabled,
            }
            for check in self.checks
        ]


def validate_config_points(config: EvaluationConfig, max_points: int) -> list[str]:
    """Return human-readable problems; empty list means the config is acceptable."""
    problems: list[str] = []
    allocated = config.total_points()
    if allocated > max_points:
        problems.append(
            f"evaluation checks allocate {allocated} points but the "
            f"challenge maximum is {max_points}"
        )
    if allocated == 0:
        problems.append("evaluation checks allocate zero points; at least one check must score")
    return problems


def check_result(
    *,
    check_id: str,
    check_type: str,
    description: str,
    status: CheckStatus,
    max_points: int,
    awarded_points: int,
    message: str,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a validated check-result payload dict."""
    payload = {
        "id": check_id,
        "type": check_type,
        "description": description,
        "status": status.value,
        "max_points": max_points,
        "awarded_points": max(0, min(awarded_points, max_points)),
        "message": message,
        "evidence": evidence or {},
    }
    return payload
