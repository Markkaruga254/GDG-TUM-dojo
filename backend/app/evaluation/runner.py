"""Deterministic evaluation runner.

Scoring policy (documented in README, "Evaluation and scoring policy"):

- ``passed``     → full check points
- ``partial``    → proportional points (floor), never more than the check's points
- ``failed``     → 0 points
- ``skipped``    → 0 points (check could not apply; optional checks do not fail the run)
- ``error``      → 0 points, and the whole evaluation is marked ``error`` so it can
                   be retried and never contributes to the leaderboard

A submission ``passes`` only when every enabled ``required`` check passed and no
check errored. Partial credit is still awarded for partial checks, but the
submission itself is ``failed``.

Only repository metadata is inspected. No student code is fetched, executed or
imported at any point.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.evaluation.probe import RepoProbe
from app.evaluation.rules import CheckConfig, EvaluationConfig, check_result
from app.integrations.github import GitHubError, RepoMetadata
from app.models.enums import CheckStatus, EvaluationStatus, SubmissionStatus

REQUIRED_FILES_KINDS = {"file", "symlink"}
MAX_HEADING_SCAN_LINES = 2000


@dataclass
class CheckContext:
    probe: RepoProbe
    repo: RepoMetadata | None
    evidence_urls: list[str] = field(default_factory=list)


@dataclass
class EvaluationOutcome:
    status: EvaluationStatus
    submission_status: SubmissionStatus
    checks: list[dict]
    awarded_score: int
    max_score: int
    feedback: str
    summary: str


def evaluate_repository(
    config: EvaluationConfig,
    probe: RepoProbe,
    *,
    evidence_urls: list[str] | None = None,
) -> EvaluationOutcome:
    """Run all enabled checks; never raises for expected GitHub failures."""
    max_score = config.total_points()
    evidence = list(evidence_urls or [])

    try:
        repo = probe.repository()
    except GitHubError as exc:
        return _fatal_outcome(
            config,
            max_score,
            f"Repository metadata could not be retrieved ({exc.code}); "
            "the evaluation can be retried.",
        )

    if repo is None:
        checks = [
            check_result(
                check_id=check.id,
                check_type=check.type,
                description=check.description,
                status=CheckStatus.SKIPPED if index > 0 else CheckStatus.FAILED,
                max_points=check.points,
                awarded_points=0,
                message=(
                    "Repository was not found or is not accessible through the GitHub API."
                    if index == 0
                    else "Skipped because the repository is not accessible."
                ),
            )
            for index, check in enumerate(config.enabled_checks())
        ]
        return EvaluationOutcome(
            status=EvaluationStatus.COMPLETED,
            submission_status=SubmissionStatus.FAILED,
            checks=checks,
            awarded_score=0,
            max_score=max_score,
            feedback="Repository not found or not accessible.",
            summary=_summary(checks, 0, max_score),
        )

    if config.require_public_repo and repo.private:
        checks = [
            check_result(
                check_id="repository_visibility",
                check_type="repo_public",
                description="Repository is publicly visible.",
                status=CheckStatus.FAILED,
                max_points=0,
                awarded_points=0,
                message="The repository is private. This challenge requires a public repository.",
            ),
            *[
                check_result(
                    check_id=check.id,
                    check_type=check.type,
                    description=check.description,
                    status=CheckStatus.SKIPPED,
                    max_points=check.points,
                    awarded_points=0,
                    message="Skipped because the repository is private.",
                )
                for check in config.enabled_checks()
            ],
        ]
        return EvaluationOutcome(
            status=EvaluationStatus.COMPLETED,
            submission_status=SubmissionStatus.FAILED,
            checks=checks,
            awarded_score=0,
            max_score=max_score,
            feedback="The repository is private; this challenge requires a public repository.",
            summary=_summary(checks, 0, max_score),
        )

    context = CheckContext(probe=probe, repo=repo, evidence_urls=evidence)
    checks: list[dict] = []
    for check in config.enabled_checks():
        try:
            checks.append(_run_check(check, context))
        except GitHubError as exc:
            checks.append(
                check_result(
                    check_id=check.id,
                    check_type=check.type,
                    description=check.description,
                    status=CheckStatus.ERROR,
                    max_points=check.points,
                    awarded_points=0,
                    message=(
                        f"Check could not complete ({exc.code}); the evaluation can be retried."
                    ),
                )
            )

    errored = any(check["status"] == CheckStatus.ERROR.value for check in checks)
    if errored:
        return EvaluationOutcome(
            status=EvaluationStatus.ERROR,
            submission_status=SubmissionStatus.ERROR,
            checks=checks,
            awarded_score=0,
            max_score=max_score,
            feedback="Evaluation was incomplete because one or more checks errored. Retry later.",
            summary=_summary(checks, 0, max_score),
        )

    awarded = min(sum(check["awarded_points"] for check in checks), max_score)
    passed = not _required_failures(config, checks)
    submission_status = SubmissionStatus.PASSED if passed else SubmissionStatus.FAILED
    failed_ids = [check["id"] for check in checks if check["status"] != CheckStatus.PASSED.value]
    feedback = (
        "All required checks passed."
        if passed
        else ("Required checks not satisfied: " + ", ".join(failed_ids))
    )
    return EvaluationOutcome(
        status=EvaluationStatus.COMPLETED,
        submission_status=submission_status,
        checks=checks,
        awarded_score=awarded,
        max_score=max_score,
        feedback=feedback,
        summary=_summary(checks, awarded, max_score),
    )


def _required_failures(config: EvaluationConfig, checks: list[dict]) -> list[dict]:
    required_ids = {check.id for check in config.enabled_checks() if check.required}
    return [
        check
        for check in checks
        if check["id"] in required_ids and check["status"] != CheckStatus.PASSED.value
    ]


def _fatal_outcome(config: EvaluationConfig, max_score: int, message: str) -> EvaluationOutcome:
    checks = [
        check_result(
            check_id=check.id,
            check_type=check.type,
            description=check.description,
            status=CheckStatus.ERROR,
            max_points=check.points,
            awarded_points=0,
            message=message,
        )
        for check in config.enabled_checks()
    ]
    return EvaluationOutcome(
        status=EvaluationStatus.ERROR,
        submission_status=SubmissionStatus.ERROR,
        checks=checks,
        awarded_score=0,
        max_score=max_score,
        feedback=message,
        summary=message,
    )


def _summary(checks: list[dict], awarded: int, max_score: int) -> str:
    passed = sum(1 for check in checks if check["status"] == CheckStatus.PASSED.value)
    return f"{passed}/{len(checks)} checks passed — {awarded}/{max_score} points"


# --- individual checks ---------------------------------------------------------


def _run_check(check: CheckConfig, context: CheckContext) -> dict:
    handler = _CHECK_HANDLERS[check.type]
    status, awarded, message, evidence = handler(check, context)
    payload = check_result(
        check_id=check.id,
        check_type=check.type,
        description=check.description,
        status=status,
        max_points=check.points,
        awarded_points=awarded,
        message=message,
        evidence=evidence,
    )
    payload["required"] = check.required
    return payload


def _repo_accessible(check: CheckConfig, context: CheckContext) -> tuple:
    repo = context.repo
    if repo is None:
        return CheckStatus.FAILED, 0, "Repository not found or not accessible.", {}
    evidence = {
        "full_name": repo.full_name,
        "default_branch": repo.default_branch,
        "private": repo.private,
        "archived": repo.archived,
        "stars": repo.stars,
        "size_kb": repo.size_kb,
        "pushed_at": repo.pushed_at.isoformat() if repo.pushed_at else None,
    }
    return CheckStatus.PASSED, check.points, "Repository is accessible.", evidence


def _repo_public(check: CheckConfig, context: CheckContext) -> tuple:
    repo = context.repo
    if repo is None or repo.private:
        return CheckStatus.FAILED, 0, "Repository is not publicly visible.", {}
    return CheckStatus.PASSED, check.points, "Repository is public.", {"private": False}


def _required_paths(check: CheckConfig, context: CheckContext, expected_kind: str) -> tuple:
    paths = list(check.params.get("paths", []))
    match = str(check.params.get("match", "all"))
    if not paths:
        return CheckStatus.SKIPPED, 0, "No paths configured.", {}

    found: list[str] = []
    missing: list[str] = []
    for path in paths:
        entry = context.probe.file_entry(path)
        ok = entry is not None and (
            entry.kind == expected_kind
            or (expected_kind == "file" and entry.kind in REQUIRED_FILES_KINDS)
        )
        (found if ok else missing).append(path)

    evidence = {"found": found, "missing": missing, "expected": expected_kind}
    if match == "any":
        if found:
            return (
                CheckStatus.PASSED,
                check.points,
                f"Found {len(found)} of {len(paths)} accepted paths.",
                evidence,
            )
        return CheckStatus.FAILED, 0, "None of the accepted paths exist.", evidence

    if not missing:
        return CheckStatus.PASSED, check.points, f"All {len(paths)} required paths exist.", evidence
    if found:
        awarded = int(check.points * len(found) / len(paths))
        return (
            CheckStatus.PARTIAL,
            awarded,
            f"Missing paths: {', '.join(missing)}.",
            evidence,
        )
    return CheckStatus.FAILED, 0, f"Missing paths: {', '.join(missing)}.", evidence


def _required_files(check: CheckConfig, context: CheckContext) -> tuple:
    return _required_paths(check, context, "file")


def _required_directories(check: CheckConfig, context: CheckContext) -> tuple:
    return _required_paths(check, context, "dir")


def _readme_present(check: CheckConfig, context: CheckContext) -> tuple:
    readme = context.probe.readme()
    if readme is None:
        return CheckStatus.FAILED, 0, "No README found on the default branch.", {"readme": False}
    return (
        CheckStatus.PASSED,
        check.points,
        "README found.",
        {"readme": True, "characters": len(readme)},
    )


def _readme_sections(check: CheckConfig, context: CheckContext) -> tuple:
    sections = [str(section).lower() for section in check.params.get("sections", [])]
    readme = context.probe.readme()
    if readme is None:
        return (
            CheckStatus.FAILED,
            0,
            "No README found to check sections against.",
            {"missing": sections},
        )
    headings = _extract_headings(readme)
    missing = [
        section for section in sections if not any(section in heading for heading in headings)
    ]
    found = [section for section in sections if section not in missing]
    evidence = {"found": found, "missing": missing, "headings_scanned": len(headings)}
    if not missing:
        return (
            CheckStatus.PASSED,
            check.points,
            f"All {len(sections)} sections documented.",
            evidence,
        )
    awarded = int(check.points * len(found) / len(sections)) if sections else 0
    if found:
        return CheckStatus.PARTIAL, awarded, f"Missing sections: {', '.join(missing)}.", evidence
    return CheckStatus.FAILED, 0, f"Missing sections: {', '.join(missing)}.", evidence


def _readme_min_length(check: CheckConfig, context: CheckContext) -> tuple:
    minimum = int(check.params.get("min_characters", 300))
    readme = context.probe.readme()
    actual = len(readme) if readme is not None else 0
    evidence = {"characters": actual, "min_characters": minimum}
    if actual >= minimum:
        return CheckStatus.PASSED, check.points, f"README has {actual} characters.", evidence
    if actual > 0:
        return (
            CheckStatus.PARTIAL,
            int(check.points * actual / minimum),
            f"README is shorter than {minimum} characters.",
            evidence,
        )
    return CheckStatus.FAILED, 0, "README is missing or empty.", evidence


def _evidence_links(check: CheckConfig, context: CheckContext) -> tuple:
    minimum = int(check.params.get("min_count", 1))
    count = len([url for url in context.evidence_urls if url])
    evidence = {"provided": count, "min_count": minimum}
    if count >= minimum:
        return CheckStatus.PASSED, check.points, f"{count} evidence link(s) provided.", evidence
    return (
        CheckStatus.FAILED,
        0,
        f"At least {minimum} evidence link(s) required, {count} provided.",
        evidence,
    )


def _min_commits(check: CheckConfig, context: CheckContext) -> tuple:
    minimum = int(check.params.get("min_count", 1))
    count = context.probe.commit_count(minimum)
    evidence = {"commits_found": count, "min_count": minimum, "capped": True}
    if count >= minimum:
        return CheckStatus.PASSED, check.points, f"At least {minimum} commits found.", evidence
    return CheckStatus.FAILED, 0, f"Fewer than {minimum} commits found.", evidence


def _license_present(check: CheckConfig, context: CheckContext) -> tuple:
    if context.probe.license_present():
        return CheckStatus.PASSED, check.points, "A license file is present.", {"license": True}
    return CheckStatus.FAILED, 0, "No license file was detected.", {"license": False}


def _language_present(check: CheckConfig, context: CheckContext) -> tuple:
    required = [str(language) for language in check.params.get("languages", [])]
    min_share = float(check.params.get("min_share", 0.0))
    languages = context.probe.languages()
    total = sum(languages.values())
    shares: dict[str, float] = {}
    met: list[str] = []
    for language in required:
        matched = next(
            (size for name, size in languages.items() if name.lower() == language.lower()), 0
        )
        share = (matched / total) if total else 0.0
        shares[language] = round(share, 4)
        if share >= min_share and matched > 0:
            met.append(language)
    evidence = {"shares": shares, "min_share": min_share}
    if len(met) == len(required):
        return CheckStatus.PASSED, check.points, "Required languages detected.", evidence
    awarded = int(check.points * len(met) / len(required)) if required else 0
    missing = [language for language in required if language not in met]
    if met:
        return CheckStatus.PARTIAL, awarded, f"Missing languages: {', '.join(missing)}.", evidence
    return CheckStatus.FAILED, 0, f"Missing languages: {', '.join(missing)}.", evidence


def _extract_headings(readme: str) -> list[str]:
    headings: list[str] = []
    for line in readme.splitlines()[:MAX_HEADING_SCAN_LINES]:
        stripped = line.strip()
        if stripped.startswith("#"):
            heading = stripped.lstrip("#").strip().lower()
            if heading:
                headings.append(heading)
    return headings


_CHECK_HANDLERS = {
    "repo_accessible": _repo_accessible,
    "repo_public": _repo_public,
    "required_files": _required_files,
    "required_directories": _required_directories,
    "readme_present": _readme_present,
    "readme_sections": _readme_sections,
    "readme_min_length": _readme_min_length,
    "evidence_links": _evidence_links,
    "min_commits": _min_commits,
    "license_present": _license_present,
    "language_present": _language_present,
}
