"""Stats API routes for registry health metrics."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from loom.api.deps import get_stats_service
from loom.api.middleware import verify_api_key
from loom.services.stats_service import StatsService

router = APIRouter(prefix="/api/v1/stats", tags=["stats"])


@router.get("/overview")
async def get_overview(
    service: Annotated[StatsService, Depends(get_stats_service)],
    _: Annotated[str, Depends(verify_api_key)],
) -> dict[str, Any]:
    """Return high-level registry health overview."""
    return await service.get_overview()


@router.get("/eval-trends")
async def get_eval_trends(
    service: Annotated[StatsService, Depends(get_stats_service)],
    _: Annotated[str, Depends(verify_api_key)],
    category: Annotated[str | None, Query()] = None,
    weeks: Annotated[int, Query(ge=1, le=52)] = 12,
) -> dict[str, Any]:
    """Return eval score distribution over time."""
    return await service.get_eval_trends(category=category, weeks=weeks)


@router.get("/usage-heatmap")
async def get_usage_heatmap(
    service: Annotated[StatsService, Depends(get_stats_service)],
    _: Annotated[str, Depends(verify_api_key)],
    period_type: Annotated[str, Query(pattern="^(week|day)$")] = "week",
    periods: Annotated[int, Query(ge=1, le=52)] = 12,
) -> dict[str, Any]:
    """Return usage heatmap data: categories x time periods."""
    return await service.get_usage_heatmap(period_type=period_type, periods=periods)
