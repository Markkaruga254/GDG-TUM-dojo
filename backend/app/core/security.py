"""Password-free security helpers: tokens, hashing, PKCE, slugs, UTC time."""

from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets
from datetime import UTC, datetime

_SLUG_STRIP = re.compile(r"[^a-z0-9]+")


def now_utc() -> datetime:
    return datetime.now(UTC)


def generate_token(nbytes: int = 32) -> str:
    """URL-safe, high-entropy token for sessions, CSRF and OAuth state."""
    return secrets.token_urlsafe(nbytes)


def hash_token(token: str) -> str:
    """SHA-256 digest used to store session tokens at rest."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def constant_time_equals(left: str | None, right: str | None) -> bool:
    if not left or not right:
        return False
    return hmac.compare_digest(left.encode("utf-8"), right.encode("utf-8"))


def create_pkce_pair() -> tuple[str, str]:
    """Return ``(code_verifier, code_challenge)`` for OAuth PKCE (S256)."""
    verifier = secrets.token_urlsafe(48)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


def slugify(value: str, *, max_length: int = 120) -> str:
    slug = _SLUG_STRIP.sub("-", value.strip().lower()).strip("-")
    if len(slug) > max_length:
        slug = slug[:max_length].rstrip("-")
    return slug or "challenge"


def unique_slug(base: str, is_taken, max_attempts: int = 50) -> str:
    """Return ``base`` or ``base-2``, ``base-3``... until ``is_taken(candidate)`` is false."""
    candidate = slugify(base)
    if not is_taken(candidate):
        return candidate
    for suffix in range(2, max_attempts + 2):
        suffixed = f"{candidate[:110]}-{suffix}"
        if not is_taken(suffixed):
            return suffixed
    return f"{candidate[:100]}-{secrets.token_hex(4)}"
