"""GitHub integration tests: URL validation and API error handling (no live calls)."""

from __future__ import annotations

import httpx
import pytest

from app.integrations.github import (
    GitHubAuthError,
    GitHubClient,
    GitHubRateLimited,
    GitHubUnavailable,
    InvalidRepoUrlError,
    RepoRef,
    parse_repo_url,
)

VALID_URLS = [
    ("https://github.com/GDG-TUM/build-arena", "gdg-tum/build-arena", "GDG-TUM"),
    ("https://github.com/owner/repo.git", "owner/repo", "owner"),
    ("https://github.com/owner/repo/", "owner/repo", "owner"),
    ("  https://github.com/owner/repo  ", "owner/repo", "owner"),
    ("https://GitHub.com/Owner/Repo", "owner/repo", "Owner"),
]

INVALID_URLS = [
    "http://github.com/owner/repo",
    "git://github.com/owner/repo",
    "ssh://git@github.com/owner/repo",
    "git@github.com:owner/repo.git",
    "https://gitlab.com/owner/repo",
    "https://github.com.evil.example/owner/repo",
    "https://evil.example/github.com/owner/repo",
    "https://user:token@github.com/owner/repo",
    "https://github.com:8443/owner/repo",
    "https://github.com/owner",
    "https://github.com/owner/repo/extra/path",
    "https://github.com/owner/repo?ref=main",
    "https://github.com/owner/repo#readme",
    "https://github.com/-invalid/repo",
    "https://github.com/owner/..",
    "https://github.com/../repo",
    "https://github.com/owner/re po",
    "https://github.com/owner/%2e%2e",
    "file:///etc/passwd",
    "javascript:alert(1)",
    "",
    "   ",
    "not-a-url",
]


@pytest.mark.parametrize(("url", "expected_full_name", "expected_owner"), VALID_URLS)
def test_valid_repo_urls_are_parsed(url, expected_full_name, expected_owner):
    ref = parse_repo_url(url)
    assert ref.full_name == expected_full_name
    assert ref.owner == expected_owner
    assert ref.canonical_url.startswith("https://github.com/")


@pytest.mark.parametrize("url", INVALID_URLS)
def test_unsafe_repo_urls_are_rejected(url):
    with pytest.raises(InvalidRepoUrlError):
        parse_repo_url(url)


def test_repo_ref_api_path_is_built_from_validated_parts():
    ref = parse_repo_url("https://github.com/Owner/Repo.git")
    assert ref.api_path == "/repos/Owner/Repo"
    assert RepoRef(owner="a", name="b").full_name == "a/b"


def _client(handler) -> GitHubClient:  # type: ignore[no-untyped-def]
    return GitHubClient(
        base_url="https://api.github.test",
        timeout_seconds=1.0,
        transport=httpx.MockTransport(handler),
    )


def test_missing_repository_returns_none():
    client = _client(lambda request: httpx.Response(404, json={"message": "Not Found"}))
    assert client.get_repository(RepoRef(owner="o", name="r")) is None
    assert client.get_readme(RepoRef(owner="o", name="r")) is None
    assert client.has_license(RepoRef(owner="o", name="r")) is False


def test_repository_metadata_is_parsed():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "full_name": "owner/repo",
                "private": False,
                "default_branch": "trunk",
                "html_url": "https://github.com/owner/repo",
                "archived": False,
                "fork": True,
                "size": 42,
                "stargazers_count": 7,
                "pushed_at": "2026-01-02T03:04:05Z",
            },
        )

    repo = _client(handler).get_repository(RepoRef(owner="owner", name="repo"))
    assert repo is not None
    assert repo.default_branch == "trunk"
    assert repo.stars == 7
    assert repo.pushed_at is not None and repo.pushed_at.year == 2026
    assert repo.private is False


def test_rate_limit_is_detected_and_reported():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            403,
            json={"message": "API rate limit exceeded"},
            headers={"x-ratelimit-remaining": "0", "x-ratelimit-reset": "9999999999"},
        )

    with pytest.raises(GitHubRateLimited) as exc:
        _client(handler).get_repository(RepoRef(owner="o", name="r"))
    assert exc.value.retry_after_seconds is not None


def test_unauthorized_api_token_raises_auth_error():
    client = _client(lambda request: httpx.Response(401, json={"message": "Bad credentials"}))
    with pytest.raises(GitHubAuthError):
        client.get_authenticated_user("bad-token")


def test_network_timeouts_become_unavailable():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timed out")

    with pytest.raises(GitHubUnavailable):
        _client(handler).get_repository(RepoRef(owner="o", name="r"))


def test_server_errors_are_retried_then_reported():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(503, json={"message": "unavailable"})

    with pytest.raises(GitHubUnavailable):
        _client(handler).get_repository(RepoRef(owner="o", name="r"))
    assert calls["n"] == 2  # one retry


def test_readme_content_is_decoded_and_truncated():
    import base64

    content = base64.b64encode(b"# Hello\nworld").decode()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"content": content, "encoding": "base64"})

    readme = _client(handler).get_readme(RepoRef(owner="o", name="r"))
    assert readme is not None
    assert "Hello" in readme


def test_oauth_code_exchange_rejects_github_error_payload():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"error": "bad_verification_code", "error_description": "expired"}
        )

    client = _client(handler)
    with pytest.raises(GitHubAuthError):
        client.exchange_oauth_code(
            token_url="https://github.test/login/oauth/access_token",
            client_id="id",
            client_secret="secret",
            code="code",
            redirect_uri="https://api.test/callback",
            code_verifier="verifier",
        )


def test_oauth_code_exchange_returns_access_token():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["accept"] == "application/json"
        return httpx.Response(200, json={"access_token": "gho_example", "token_type": "bearer"})

    client = _client(handler)
    token = client.exchange_oauth_code(
        token_url="https://github.test/login/oauth/access_token",
        client_id="id",
        client_secret="secret",
        code="code",
        redirect_uri="https://api.test/callback",
        code_verifier="verifier",
    )
    assert token == "gho_example"


def test_commit_count_is_capped():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["per_page"] == "5"
        return httpx.Response(200, json=[{"sha": str(n)} for n in range(5)])

    count = _client(handler).count_commits(RepoRef(owner="o", name="r"), 5)
    assert count == 5
