"""Tests for usage signal detection cron job logic."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from loom.models.usage import UsageAggregate
from loom.worker import detect_usage_signals


def _make_aggregate(
    skill_id: uuid.UUID | None = None,
    success_count: int = 8,
    partial_count: int = 0,
    failure_count: int = 2,
    success_rate: float | None = None,
    window_type: str = "7d",
) -> UsageAggregate:
    total = success_count + partial_count + failure_count
    if success_rate is None and total > 0:
        success_rate = success_count / total
    return UsageAggregate(
        id=uuid.uuid4(),
        skill_id=skill_id or uuid.uuid4(),
        skill_version="1.0.0",
        window_type=window_type,
        success_count=success_count,
        partial_count=partial_count,
        failure_count=failure_count,
        success_rate=success_rate,
        avg_runtime_ms=100.0,
        computed_at=datetime.now(UTC),
        window_start=datetime.now(UTC),
    )


def _make_ctx():
    """Build a mock arq context dict."""
    conn = AsyncMock()
    pool = MagicMock()

    @asynccontextmanager
    async def _acquire():
        yield conn

    pool.acquire = _acquire

    usage_repo = AsyncMock()
    settings = MagicMock()
    settings.pipeline.usage_failure_rate_trigger = 0.30
    settings.pipeline.usage_success_rate_drop_trigger = 0.20

    redis = AsyncMock()

    ctx = {
        "pool": pool,
        "settings": settings,
        "usage_repo_factory": lambda c: usage_repo,
        "redis": redis,
    }
    return ctx, usage_repo, redis


@pytest.mark.asyncio
async def test_no_aggregates_no_alerts():
    """No aggregates above threshold produces zero alerts."""
    ctx, usage_repo, _ = _make_ctx()
    usage_repo.get_aggregates_above_threshold.return_value = []

    result = await detect_usage_signals(ctx)
    assert result["alerts"] == 0
    assert result["re_evals_triggered"] == 0


@pytest.mark.asyncio
async def test_high_failure_rate_triggers_reeval():
    """Failure rate above threshold triggers re-assessment."""
    ctx, usage_repo, redis = _make_ctx()
    skill_id = uuid.uuid4()
    # 4 failures out of 10 = 40% > 30% threshold
    agg = _make_aggregate(skill_id=skill_id, success_count=5, partial_count=1, failure_count=4)
    usage_repo.get_aggregates_above_threshold.return_value = [agg]
    usage_repo.get_aggregate_for_skill.return_value = None  # no 30d data

    result = await detect_usage_signals(ctx)
    assert result["alerts"] == 1
    assert result["re_evals_triggered"] == 1
    redis.enqueue_job.assert_awaited_once_with("run_eval_job", str(skill_id), "usage_signal")


@pytest.mark.asyncio
async def test_success_rate_drop_triggers_reeval():
    """Success rate drop from 30d to 7d above threshold triggers re-assessment."""
    ctx, usage_repo, redis = _make_ctx()
    skill_id = uuid.uuid4()
    # 7d: 60% success rate
    agg_7d = _make_aggregate(skill_id=skill_id, success_count=6, partial_count=2, failure_count=2)
    # 30d: 90% success rate -> drop of 30% > 20% threshold
    agg_30d = _make_aggregate(
        skill_id=skill_id, success_count=9, failure_count=1, window_type="30d"
    )
    usage_repo.get_aggregates_above_threshold.return_value = [agg_7d]
    usage_repo.get_aggregate_for_skill.return_value = agg_30d

    result = await detect_usage_signals(ctx)
    assert result["alerts"] >= 1
    assert result["re_evals_triggered"] >= 1


@pytest.mark.asyncio
async def test_healthy_skill_no_alerts():
    """Skill with good rates does not trigger alerts."""
    ctx, usage_repo, redis = _make_ctx()
    # 90% success, 10% failure = not above 30% threshold
    agg = _make_aggregate(success_count=9, partial_count=0, failure_count=1)
    usage_repo.get_aggregates_above_threshold.return_value = [agg]
    # 30d also at 90%, no drop
    agg_30d = _make_aggregate(success_count=90, failure_count=10, window_type="30d")
    usage_repo.get_aggregate_for_skill.return_value = agg_30d

    result = await detect_usage_signals(ctx)
    assert result["alerts"] == 0
    assert result["re_evals_triggered"] == 0
    redis.enqueue_job.assert_not_awaited()
