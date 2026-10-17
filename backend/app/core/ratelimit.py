"""In-process sliding-window rate limiting.

This intentionally avoids extra infrastructure for the MVP. It is per-process,
which is sufficient for a single-instance deployment; multi-instance deployments
must additionally apply provider-level (Render / reverse-proxy / WAF) limits.
See README section "Rate limiting strategy".

The FastAPI dependency factory built on top of this limiter lives in
``app.core.dependencies`` (``rate_limit_dependency``).
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from fastapi import Request

from app.core.config import Settings


class SlidingWindowRateLimiter:
    def __init__(self, max_keys: int = 20_000) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()
        self._max_keys = max_keys

    def check(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
        """Return ``(allowed, retry_after_seconds)``."""
        now = time.monotonic()
        with self._lock:
            self._prune(now)
            bucket = self._hits[key]
            cutoff = now - window_seconds
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= limit:
                retry_after = int(bucket[0] + window_seconds - now) + 1
                return False, max(retry_after, 1)
            bucket.append(now)
            return True, 0

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()

    def _prune(self, now: float) -> None:
        if len(self._hits) < self._max_keys:
            return
        stale = [key for key, bucket in self._hits.items() if not bucket or bucket[-1] < now - 3600]
        for key in stale:
            self._hits.pop(key, None)


rate_limiter = SlidingWindowRateLimiter()


def client_ip(request: Request, settings: Settings) -> str:
    """Resolve the client IP, honouring X-Forwarded-For only when explicitly trusted."""
    if settings.trust_proxy_headers:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            first = forwarded.split(",")[0].strip()
            if first:
                return first
    return request.client.host if request.client else "unknown"
