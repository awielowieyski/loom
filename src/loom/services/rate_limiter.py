"""Rate limiting for skill submissions using Redis sorted sets or in-memory fallback."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import MutableMapping
    from typing import Any

logger = logging.getLogger(__name__)


class RateLimitExceeded(Exception):
    """Raised when submission rate limit is exceeded."""

    def __init__(self, retry_after_seconds: int) -> None:
        self.retry_after_seconds = retry_after_seconds
        super().__init__(f"Rate limit exceeded. Retry after {retry_after_seconds}s")


class RateLimiter:
    """Redis-based sliding window rate limiter for skill submissions.

    Uses sorted sets keyed by author ID, where each member is a unique
    submission timestamp. Old entries are pruned on each check, and the
    key auto-expires after the window elapses.
    """

    def __init__(
        self,
        redis_url: str,
        unverified_limit: int = 5,
        verified_limit: int = 20,
        window_seconds: int = 86400,
    ) -> None:
        self._redis_url = redis_url
        self._unverified_limit = unverified_limit
        self._verified_limit = verified_limit
        self._window_seconds = window_seconds
        self._redis = None

    async def _get_redis(self) -> Any:
        """Lazy-initialise the Redis client."""
        if self._redis is None:
            import redis.asyncio as aioredis

            self._redis = aioredis.from_url(self._redis_url)  # type: ignore[no-untyped-call]
        return self._redis

    async def check_rate_limit(self, author_id: str, is_verified: bool = False) -> None:
        """Check if author can submit. Raises RateLimitExceeded if over limit."""
        limit = self._verified_limit if is_verified else self._unverified_limit
        key = f"rate:submission:{author_id}"
        now = time.time()
        window_start = now - self._window_seconds

        r = await self._get_redis()
        # Remove entries outside the window
        await r.zremrangebyscore(key, "-inf", window_start)
        # Count remaining entries
        count = await r.zcard(key)

        if count >= limit:
            # Find the oldest entry to compute retry-after
            oldest = await r.zrange(key, 0, 0, withscores=True)
            retry_after = (
                int(oldest[0][1] + self._window_seconds - now) if oldest else self._window_seconds
            )
            raise RateLimitExceeded(retry_after_seconds=max(1, retry_after))

        # Record this submission
        await r.zadd(key, {f"{now}": now})
        await r.expire(key, self._window_seconds)


class InMemoryRateLimiter:
    """In-memory fallback rate limiter for environments without Redis.

    Uses a dict mapping author IDs to lists of submission timestamps.
    Expired entries are cleaned up on each check.
    """

    def __init__(
        self,
        unverified_limit: int = 5,
        verified_limit: int = 20,
        window_seconds: int = 86400,
    ) -> None:
        self._unverified_limit = unverified_limit
        self._verified_limit = verified_limit
        self._window_seconds = window_seconds
        self._entries: MutableMapping[str, list[float]] = {}

    async def check_rate_limit(self, author_id: str, is_verified: bool = False) -> None:
        """Check if author can submit. Raises RateLimitExceeded if over limit."""
        limit = self._verified_limit if is_verified else self._unverified_limit
        now = time.time()
        window_start = now - self._window_seconds

        # Get and prune entries
        timestamps = self._entries.get(author_id, [])
        timestamps = [ts for ts in timestamps if ts > window_start]
        self._entries[author_id] = timestamps

        if len(timestamps) >= limit:
            oldest = min(timestamps) if timestamps else now
            retry_after = int(oldest + self._window_seconds - now)
            raise RateLimitExceeded(retry_after_seconds=max(1, retry_after))

        # Record this submission
        timestamps.append(now)
