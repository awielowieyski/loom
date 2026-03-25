"""Tests for StatsService."""

from unittest.mock import AsyncMock

import pytest

from loom.services.stats_service import StatsService


def _make_conn() -> AsyncMock:
    return AsyncMock()


@pytest.mark.asyncio
async def test_get_overview_empty_registry() -> None:
    conn = _make_conn()
    # No skills by tier
    conn.fetch.return_value = []
    # capability count, behavioral count, stale count, deprecated count, res_7d, res_30d
    conn.fetchval.side_effect = [0, 0, 0, 0, 0, 0]

    service = StatsService(conn)
    result = await service.get_overview()

    assert result["skill_counts"] == {"experimental": 0, "community": 0, "verified": 0}
    assert result["capability_count"] == 0
    assert result["behavioral_eval_coverage"] == 0.0
    assert result["stale_count"] == 0
    assert result["deprecated_count"] == 0
    assert result["total_resolutions_7d"] == 0
    assert result["total_resolutions_30d"] == 0


@pytest.mark.asyncio
async def test_get_overview_with_skills() -> None:
    conn = _make_conn()
    conn.fetch.return_value = [
        {"trust_tier": "experimental", "cnt": 5},
        {"trust_tier": "community", "cnt": 3},
        {"trust_tier": "verified", "cnt": 2},
    ]
    # cap_count=4, behavioral=7, stale=1, deprecated=2, res_7d=100, res_30d=500
    conn.fetchval.side_effect = [4, 7, 1, 2, 100, 500]

    service = StatsService(conn)
    result = await service.get_overview()

    assert result["skill_counts"]["experimental"] == 5
    assert result["skill_counts"]["community"] == 3
    assert result["skill_counts"]["verified"] == 2
    assert result["capability_count"] == 4
    assert result["behavioral_eval_coverage"] == 0.7  # 7/10
    assert result["stale_count"] == 1
    assert result["deprecated_count"] == 2
    assert result["total_resolutions_7d"] == 100
    assert result["total_resolutions_30d"] == 500


@pytest.mark.asyncio
async def test_get_eval_trends_empty() -> None:
    conn = _make_conn()
    conn.fetch.return_value = []

    service = StatsService(conn)
    result = await service.get_eval_trends(weeks=4)

    assert result["weeks_requested"] == 4
    assert result["category"] is None
    assert result["windows"] == []


@pytest.mark.asyncio
async def test_get_usage_heatmap_empty() -> None:
    conn = _make_conn()
    conn.fetch.return_value = []

    service = StatsService(conn)
    result = await service.get_usage_heatmap(period_type="week", periods=4)

    assert result["period_type"] == "week"
    assert result["categories"] == []
    assert result["periods"] == []
    assert result["data"] == []
