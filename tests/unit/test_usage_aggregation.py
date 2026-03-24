"""Tests for usage aggregation cron job logic."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest

from loom.worker import aggregate_usage


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

    ctx = {
        "pool": pool,
        "settings": settings,
        "usage_repo_factory": lambda c: usage_repo,
    }
    return ctx, usage_repo


@pytest.mark.asyncio
async def test_aggregate_usage_empty():
    """No reports in any window produces zero skill updates."""
    ctx, usage_repo = _make_ctx()
    usage_repo.get_distinct_skill_versions_in_window.return_value = []

    result = await aggregate_usage(ctx)
    assert result["windows_processed"] == 3
    assert result["skills_updated"] == 0


@pytest.mark.asyncio
async def test_aggregate_usage_computes_correct_rates():
    """Aggregation computes correct success_rate from outcome counts."""
    ctx, usage_repo = _make_ctx()

    skill_id = uuid.uuid4()
    pairs = [(skill_id, "1.0.0")]
    usage_repo.get_distinct_skill_versions_in_window.return_value = pairs
    usage_repo.aggregate_reports_in_window.return_value = {
        "success": 7,
        "partial": 2,
        "failure": 1,
        "avg_runtime_ms": 150.0,
    }

    upsert_mock = usage_repo.upsert_aggregate
    upsert_mock.return_value = MagicMock()

    result = await aggregate_usage(ctx)
    assert result["skills_updated"] == 3  # same skill across 3 windows

    # Check success_rate calculation in calls
    calls = upsert_mock.call_args_list
    assert len(calls) == 3
    first_call = calls[0]
    assert first_call.kwargs["success_rate"] == 0.7  # 7/10
    assert first_call.kwargs["avg_runtime_ms"] == 150.0


@pytest.mark.asyncio
async def test_aggregate_usage_handles_zero_total():
    """Zero total reports produces None success_rate."""
    ctx, usage_repo = _make_ctx()

    skill_id = uuid.uuid4()
    usage_repo.get_distinct_skill_versions_in_window.return_value = [(skill_id, "1.0.0")]
    usage_repo.aggregate_reports_in_window.return_value = {
        "success": 0,
        "partial": 0,
        "failure": 0,
        "avg_runtime_ms": None,
    }
    usage_repo.upsert_aggregate.return_value = MagicMock()

    result = await aggregate_usage(ctx)
    assert result["skills_updated"] == 3

    first_call = usage_repo.upsert_aggregate.call_args_list[0]
    assert first_call.kwargs["success_rate"] is None
