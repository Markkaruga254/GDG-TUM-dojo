"""Repository probes used by the evaluation engine.

A probe is a read-only view over repository metadata. The production
implementation talks to the GitHub API; tests substitute a fake probe. Probes
never execute repository code.
"""

from __future__ import annotations

from typing import Protocol

from app.integrations.github import FileEntry, GitHubClient, RepoMetadata, RepoRef


class RepoProbe(Protocol):
    """Read-only repository metadata access used by evaluation checks."""

    def repository(self) -> RepoMetadata | None: ...

    def file_entry(self, path: str) -> FileEntry | None: ...

    def readme(self) -> str | None: ...

    def commit_count(self, limit: int) -> int: ...

    def license_present(self) -> bool: ...

    def languages(self) -> dict[str, int]: ...


class GitHubRepoProbe:
    """``RepoProbe`` backed by :class:`GitHubClient` (caching is handled there)."""

    def __init__(self, client: GitHubClient, ref: RepoRef) -> None:
        self._client = client
        self._ref = ref

    @property
    def ref(self) -> RepoRef:
        return self._ref

    def repository(self) -> RepoMetadata | None:
        return self._client.get_repository(self._ref)

    def file_entry(self, path: str) -> FileEntry | None:
        return self._client.get_contents(self._ref, path)

    def readme(self) -> str | None:
        return self._client.get_readme(self._ref)

    def commit_count(self, limit: int) -> int:
        return self._client.count_commits(self._ref, limit)

    def license_present(self) -> bool:
        return self._client.has_license(self._ref)

    def languages(self) -> dict[str, int]:
        return self._client.get_languages(self._ref)
