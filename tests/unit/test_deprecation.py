"""Tests for deprecation/staleness workflow in SkillRepo and signal detection."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest

from loom.worker import detect_usage_signals


def _make_ctx():
    """Build a mock arq context with both usage_repo and skill_repo factories."""
    conn = AsyncMock()
    pool = MagicMock()

    @asynccontextmanager
    async def _acquire():
        yield conn

    pool.acquire = _acquire

    usage_repo = AsyncMock()
    skill_repo = AsyncMock()
    settings = MagicMock()
    settings.pipeline.usage_failure_rate_trigger = 0.30
    settings.pipeline.usage_success_rate_drop_trigger = 0.20
    settings.pipeline.staleness_window_days = 90

    redis = AsyncMock()

    ctx = {
        "pool": pool,
        "settings": settings,
        "usage_repo_factory": lambda c: usage_repo,
        "skill_repo_factory": lambda c: skill_repo,
        "redis": redis,
    }
    return ctx, usage_repo, skill_repo, redis


@pytest.mark.asyncio
async def test_staleness_detection_marks_stale_skills():
    """Signal detection cron marks skills with zero usage as stale."""
    ctx, usage_repo, skill_repo, _ = _make_ctx()
    usage_repo.get_aggregates_above_threshold.return_value = []

    stale_ids = [uuid.uuid4(), uuid.uuid4()]
    skill_repo.get_stale_candidates.return_value = stale_ids

    result = await detect_usage_signals(ctx)
    assert result["stale_marked"] == 2
    assert skill_repo.mark_stale.await_count == 2
    skill_repo.get_stale_candidates.assert_awaited_once_with(90)


@pytest.mark.asyncio
async def test_staleness_with_no_candidates():
    """No stale candidates results in zero stale_marked."""
    ctx, usage_repo, skill_repo, _ = _make_ctx()
    usage_repo.get_aggregates_above_threshold.return_value = []
    skill_repo.get_stale_candidates.return_value = []

    result = await detect_usage_signals(ctx)
    assert result["stale_marked"] == 0


@pytest.mark.asyncio
async def test_combined_signals_and_staleness():
    """Both signal alerts and staleness detection work in same run."""
    ctx, usage_repo, skill_repo, redis = _make_ctx()

    from datetime import UTC, datetime

    from loom.models.usage import UsageAggregate

    # One skill with high failure rate
    agg = UsageAggregate(
        id=uuid.uuid4(),
        skill_id=uuid.uuid4(),
        skill_version="1.0.0",
        window_type="7d",
        success_count=3,
        partial_count=0,
        failure_count=7,
        success_rate=0.3,
        avg_runtime_ms=100.0,
        computed_at=datetime.now(UTC),
        window_start=datetime.now(UTC),
    )
    usage_repo.get_aggregates_above_threshold.return_value = [agg]
    usage_repo.get_aggregate_for_skill.return_value = None

    # Plus some stale skills
    skill_repo.get_stale_candidates.return_value = [uuid.uuid4()]

    result = await detect_usage_signals(ctx)
    assert result["alerts"] >= 1
    assert result["stale_marked"] == 1
