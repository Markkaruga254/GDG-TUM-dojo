"""Evaluation engine tests: check behaviour, scoring boundaries and isolation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.evaluation.rules import EvaluationConfig, validate_config_points
from app.evaluation.runner import evaluate_repository
from app.integrations.github import FileEntry, GitHubRateLimited, RepoMetadata
from app.models.enums import CheckStatus, EvaluationStatus, SubmissionStatus


class FakeProbe:
    """In-memory repository probe. No network, no code execution."""

    def __init__(
        self,
        *,
        files: dict[str, str] | None = None,
        readme: str | None = None,
        commits: int = 3,
        license_present: bool = True,
        languages: dict[str, int] | None = None,
        private: bool = False,
        exists: bool = True,
        raises: Exception | None = None,
    ) -> None:
        self.files = files or {}
        self._readme = readme
        self.commits = commits
        self._license = license_present
        self._languages = languages or {}
        self.private = private
        self.exists = exists
        self.raises = raises
        self.calls: list[str] = []

    def repository(self) -> RepoMetadata | None:
        self.calls.append("repository")
        if self.raises:
            raise self.raises
        if not self.exists:
            return None
        return RepoMetadata(
            full_name="owner/repo",
            private=self.private,
            default_branch="main",
            html_url="https://github.com/owner/repo",
            stars=3,
        )

    def file_entry(self, path: str) -> FileEntry | None:
        self.calls.append(f"file:{path}")
        kind = self.files.get(path)
        return FileEntry(path=path, kind=kind) if kind else None

    def readme(self) -> str | None:
        self.calls.append("readme")
        return self._readme

    def commit_count(self, limit: int) -> int:
        self.calls.append("commits")
        return min(self.commits, limit)

    def license_present(self) -> bool:
        self.calls.append("license")
        return self._license

    def languages(self) -> dict[str, int]:
        self.calls.append("languages")
        return self._languages


def config(*checks: dict, require_public_repo: bool = True) -> EvaluationConfig:
    return EvaluationConfig.model_validate(
        {"require_public_repo": require_public_repo, "checks": list(checks)}
    )


def check(check_id: str, check_type: str, points: int, **extra) -> dict:
    return {
        "id": check_id,
        "type": check_type,
        "description": f"{check_type} check",
        "points": points,
        **extra,
    }


# --- configuration validation ----------------------------------------------------


def test_config_rejects_duplicate_check_ids():
    with pytest.raises(ValidationError):
        config(check("dup", "readme_present", 10), check("dup", "license_present", 10))


def test_config_rejects_unknown_check_type():
    with pytest.raises(ValidationError):
        config(check("bad", "run_student_tests", 10))


def test_config_rejects_path_traversal_parameters():
    with pytest.raises(ValidationError):
        config(check("files", "required_files", 10, params={"paths": ["../etc/passwd"]}))


def test_config_rejects_all_disabled_checks():
    with pytest.raises(ValidationError):
        config(check("readme", "readme_present", 10, enabled=False))


def test_points_cannot_exceed_challenge_maximum():
    cfg = config(check("readme", "readme_present", 80), check("license", "license_present", 40))
    problems = validate_config_points(cfg, 100)
    assert problems and "120" in problems[0]
    assert validate_config_points(cfg, 120) == []


# --- individual checks ----------------------------------------------------------------


def test_full_pass_awards_every_point():
    cfg = config(
        check("access", "repo_accessible", 10),
        check("files", "required_files", 40, params={"paths": ["README.md", "app.py"]}),
        check("readme", "readme_sections", 30, params={"sections": ["installation"]}),
        check("license", "license_present", 20),
    )
    probe = FakeProbe(
        files={"README.md": "file", "app.py": "file"},
        readme="# Project\n## Installation\nsteps",
    )
    outcome = evaluate_repository(cfg, probe)
    assert outcome.status is EvaluationStatus.COMPLETED
    assert outcome.submission_status is SubmissionStatus.PASSED
    assert outcome.awarded_score == 100
    assert outcome.max_score == 100


def test_partial_credit_never_exceeds_check_points():
    cfg = config(
        check("files", "required_files", 40, params={"paths": ["a.py", "b.py", "c.py", "d.py"]}),
    )
    probe = FakeProbe(files={"a.py": "file", "b.py": "file", "c.py": "file"})
    outcome = evaluate_repository(cfg, probe)
    files_result = outcome.checks[0]
    assert files_result["status"] == CheckStatus.PARTIAL.value
    assert files_result["awarded_points"] == 30
    assert files_result["awarded_points"] <= files_result["max_points"]
    assert outcome.submission_status is SubmissionStatus.FAILED


def test_required_failure_fails_submission_even_with_optional_points():
    cfg = config(
        check("license", "license_present", 50),
        check("evidence", "evidence_links", 50, required=False, params={"min_count": 2}),
    )
    probe = FakeProbe(license_present=False)
    outcome = evaluate_repository(cfg, probe, evidence_urls=["https://a.example/demo"])
    assert outcome.submission_status is SubmissionStatus.FAILED
    assert outcome.awarded_score == 0


def test_optional_check_does_not_block_passing():
    cfg = config(
        check("readme", "readme_present", 50),
        check("evidence", "evidence_links", 50, required=False, params={"min_count": 1}),
    )
    outcome = evaluate_repository(cfg, FakeProbe(readme="# hi"), evidence_urls=[])
    assert outcome.submission_status is SubmissionStatus.PASSED
    assert outcome.awarded_score == 50


def test_directory_check_requires_directory_kind():
    cfg = config(check("dirs", "required_directories", 10, params={"paths": ["src"]}))
    assert evaluate_repository(cfg, FakeProbe(files={"src": "file"})).awarded_score == 0
    assert evaluate_repository(cfg, FakeProbe(files={"src": "dir"})).awarded_score == 10


def test_match_any_semantics():
    cfg = config(
        check(
            "files",
            "required_files",
            10,
            params={"paths": ["main.py", "app.py"], "match": "any"},
        )
    )
    assert evaluate_repository(cfg, FakeProbe(files={"app.py": "file"})).awarded_score == 10
    assert evaluate_repository(cfg, FakeProbe(files={})).awarded_score == 0


def test_readme_min_length_scales_partially():
    cfg = config(check("len", "readme_min_length", 20, params={"min_characters": 1000}))
    outcome = evaluate_repository(cfg, FakeProbe(readme="x" * 500))
    assert outcome.checks[0]["status"] == CheckStatus.PARTIAL.value
    assert outcome.checks[0]["awarded_points"] == 10


def test_min_commits_and_language_checks():
    cfg = config(
        check("commits", "min_commits", 10, params={"min_count": 5}),
        check("lang", "language_present", 10, params={"languages": ["Python"], "min_share": 0.5}),
    )
    probe = FakeProbe(commits=5, languages={"Python": 800, "HTML": 200})
    assert evaluate_repository(cfg, probe).awarded_score == 20

    weak = FakeProbe(commits=2, languages={"HTML": 1000})
    outcome = evaluate_repository(cfg, weak)
    assert outcome.awarded_score == 0


def test_missing_repository_fails_without_erroring():
    cfg = config(check("access", "repo_accessible", 50), check("readme", "readme_present", 50))
    outcome = evaluate_repository(cfg, FakeProbe(exists=False))
    assert outcome.status is EvaluationStatus.COMPLETED
    assert outcome.submission_status is SubmissionStatus.FAILED
    assert outcome.checks[0]["status"] == CheckStatus.FAILED.value
    assert outcome.checks[1]["status"] == CheckStatus.SKIPPED.value
    assert outcome.awarded_score == 0


def test_private_repository_fails_public_requirement():
    cfg = config(check("readme", "readme_present", 50))
    outcome = evaluate_repository(cfg, FakeProbe(private=True, readme="# hi"))
    assert outcome.submission_status is SubmissionStatus.FAILED
    assert outcome.awarded_score == 0
    assert "private" in outcome.checks[0]["message"].lower()
    # No repository contents were even requested for a private repo.
    assert "readme" not in outcome.checks[0]["evidence"]


def test_private_repository_allowed_when_config_permits_it():
    cfg = config(check("readme", "readme_present", 50), require_public_repo=False)
    outcome = evaluate_repository(cfg, FakeProbe(private=True, readme="# hi"))
    assert outcome.submission_status is SubmissionStatus.PASSED


def test_rate_limited_probe_marks_evaluation_as_error_and_awards_nothing():
    cfg = config(check("access", "repo_accessible", 50))
    outcome = evaluate_repository(cfg, FakeProbe(raises=GitHubRateLimited("slow down")))
    assert outcome.status is EvaluationStatus.ERROR
    assert outcome.submission_status is SubmissionStatus.ERROR
    assert outcome.awarded_score == 0
    assert all(check["status"] == CheckStatus.ERROR.value for check in outcome.checks)


def test_checks_are_deterministic():
    cfg = config(check("readme", "readme_present", 30), check("license", "license_present", 70))
    probe = FakeProbe(readme="# hi", license_present=True)
    first = evaluate_repository(cfg, probe)
    second = evaluate_repository(cfg, probe)
    assert first.checks == second.checks
    assert first.awarded_score == second.awarded_score == 100


def test_evidence_urls_required_count():
    cfg = config(check("evidence", "evidence_links", 10, params={"min_count": 3}))
    probe = FakeProbe()
    assert evaluate_repository(cfg, probe, evidence_urls=["a", "b", "c"]).awarded_score == 10
    assert evaluate_repository(cfg, probe, evidence_urls=["a"]).awarded_score == 0


def test_engine_never_executes_repository_code():
    """The runner must talk only to the probe, never to subprocesses or the network."""
    calls: list[str] = []

    class Recorder(FakeProbe):
        def file_entry(self, path: str) -> FileEntry | None:
            calls.append(path)
            return None

    cfg = config(check("files", "required_files", 10, params={"paths": ["setup.py"]}))
    evaluate_repository(cfg, Recorder())
    assert calls == ["setup.py"]  # only metadata lookups, no execution
