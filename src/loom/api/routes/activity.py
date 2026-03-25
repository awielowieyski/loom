"""Activity feed API routes."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from loom.api.deps import get_activity_feed_service
from loom.api.middleware import verify_api_key
from loom.models.activity import ActivityEvent
from loom.services.activity_feed import ActivityFeedService

router = APIRouter(prefix="/api/v1/activity", tags=["activity"])


@router.get("/feed", response_model=list[ActivityEvent])
async def get_activity_feed(
    _: Annotated[str | None, Depends(verify_api_key)],
    service: Annotated[ActivityFeedService, Depends(get_activity_feed_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    since: Annotated[datetime | None, Query()] = None,
) -> list[ActivityEvent]:
    """Return a unified activity feed of recent events."""
    return await service.get_feed(limit=limit, since=since)
