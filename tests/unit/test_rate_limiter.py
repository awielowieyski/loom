"""Tests for the InMemoryRateLimiter."""

from __future__ import annotations

import time

import pytest

from loom.services.rate_limiter import InMemoryRateLimiter, RateLimitExceeded


@pytest.mark.asyncio
async def test_first_request_allowed():
    """First request within limit is allowed."""
    limiter = InMemoryRateLimiter(unverified_limit=5, window_seconds=60)
    # Should not raise
    await limiter.check_rate_limit("user-1", is_verified=False)


@pytest.mark.asyncio
async def test_requests_up_to_limit_allowed():
    """All requests up to the limit are allowed."""
    limiter = InMemoryRateLimiter(unverified_limit=3, window_seconds=60)
    await limiter.check_rate_limit("user-1")
    await limiter.check_rate_limit("user-1")
    await limiter.check_rate_limit("user-1")
    # 4th should fail
    with pytest.raises(RateLimitExceeded):
        await limiter.check_rate_limit("user-1")


@pytest.mark.asyncio
async def test_exceeding_limit_raises():
    """Request exceeding limit raises RateLimitExceeded with retry_after."""
    limiter = InMemoryRateLimiter(unverified_limit=2, window_seconds=60)
    await limiter.check_rate_limit("user-1")
    await limiter.check_rate_limit("user-1")

    with pytest.raises(RateLimitExceeded) as exc_info:
        await limiter.check_rate_limit("user-1")

    assert exc_info.value.retry_after_seconds >= 1


@pytest.mark.asyncio
async def test_window_slides_old_entries_expire():
    """Old entries outside the window are pruned, allowing new submissions."""
    limiter = InMemoryRateLimiter(unverified_limit=2, window_seconds=10)

    # Simulate two submissions 15 seconds ago
    old_time = time.time() - 15
    limiter._entries["user-1"] = [old_time, old_time + 1]

    # Should be allowed since old entries are outside the 10s window
    await limiter.check_rate_limit("user-1")


@pytest.mark.asyncio
async def test_different_keys_independent():
    """Different user IDs have independent rate limits."""
    limiter = InMemoryRateLimiter(unverified_limit=1, window_seconds=60)
    await limiter.check_rate_limit("user-1")
    # user-2 should still be allowed
    await limiter.check_rate_limit("user-2")
    # user-1 should fail
    with pytest.raises(RateLimitExceeded):
        await limiter.check_rate_limit("user-1")


@pytest.mark.asyncio
async def test_verified_gets_higher_limit():
    """Verified accounts use the higher limit."""
    limiter = InMemoryRateLimiter(unverified_limit=2, verified_limit=5, window_seconds=60)

    # Use 3 submissions — exceeds unverified but within verified
    for _ in range(3):
        await limiter.check_rate_limit("user-1", is_verified=True)

    # As unverified, 3rd submission would have failed
    limiter2 = InMemoryRateLimiter(unverified_limit=2, verified_limit=5, window_seconds=60)
    await limiter2.check_rate_limit("user-2", is_verified=False)
    await limiter2.check_rate_limit("user-2", is_verified=False)
    with pytest.raises(RateLimitExceeded):
        await limiter2.check_rate_limit("user-2", is_verified=False)
